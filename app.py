from flask import Flask, render_template, request, redirect, url_for, session, abort, Response
import csv
import io
import json
import os
import time
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "praisejesus")

# Fixed admin token - set ADMIN_TOKEN env var in production!
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'praisejesus')

# ---------------------------------------------------------------------------
# Google Sheets configuration (set these env vars on Render):
#   GOOGLE_CREDENTIALS_JSON : the FULL service-account JSON, pasted as one value
#   GOOGLE_SHEET_ID         : the ID from the sheet URL
#                             https://docs.google.com/spreadsheets/d/<THIS PART>/edit
# When either is missing, the app falls back to a local responses.csv
# (fine for local testing; NOT persistent on Render's free tier).
# ---------------------------------------------------------------------------
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
WORKSHEET_NAME = os.environ.get("GOOGLE_WORKSHEET_NAME", "Responses")
USE_SHEETS = bool(GOOGLE_CREDENTIALS_JSON and GOOGLE_SHEET_ID)

CSV_FILE = "responses.csv"  # local fallback only
MAX_POINTS_PER_QUESTION = 50
TIME_LIMIT_SECONDS = 20  # Time until points reach minimum
TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"

print(f"Admin download URL: http://localhost:5000/download?token={ADMIN_TOKEN}")
print(f"Storage backend: {'Google Sheets' if USE_SHEETS else 'local CSV (responses.csv)'}")
print("Leaderboard: showing all-time entries from storage")

quiz = [
  {
    "question": "Who built the ark?",
    "options": ["Moses", "Noah", "David", "Abraham"],
    "answer": "Noah",
    "difficulty": "easy"
  },
  {
    "question": "Who was the first man created by God?",
    "options": ["Noah", "Adam", "Moses", "Joseph"],
    "answer": "Adam",
    "difficulty": "easy"
  },
  {
    "question": "Who was the first woman created by God?",
    "options": ["Sarah", "Mary", "Eve", "Ruth"],
    "answer": "Eve",
    "difficulty": "easy"
  },
  {
    "question": "How many days did God take to create the world?",
    "options": ["5", "6", "7", "8"],
    "answer": "6",
    "difficulty": "easy"
  },
  {
    "question": "What did God create on the first day?",
    "options": ["Animals", "Light", "People", "Stars"],
    "answer": "Light",
    "difficulty": "easy"
  },
  {
    "question": "Who led the Israelites out of Egypt?",
    "options": ["David", "Abraham", "Moses", "Joshua"],
    "answer": "Moses",
    "difficulty": "easy"
  },
  {
    "question": "What did David use to defeat Goliath?",
    "options": ["A sword", "A spear", "A sling and a stone", "A bow and arrow"],
    "answer": "A sling and a stone",
    "difficulty": "easy"
  },
  {
    "question": "Where was Jesus born?",
    "options": ["Nazareth", "Jerusalem", "Bethlehem", "Capernaum"],
    "answer": "Bethlehem",
    "difficulty": "easy"
  },
  {
    "question": "Who was Jesus' mother?",
    "options": ["Martha", "Elizabeth", "Mary", "Ruth"],
    "answer": "Mary",
    "difficulty": "easy"
  },
  {
    "question": "Who baptized Jesus?",
    "options": ["Peter", "John the Baptist", "Andrew", "Paul"],
    "answer": "John the Baptist",
    "difficulty": "easy"
  },
  {
    "question": "How many disciples did Jesus choose?",
    "options": ["10", "11", "12", "13"],
    "answer": "12",
    "difficulty": "easy"
  },
  {
    "question": "What did Jesus turn water into?",
    "options": ["Juice", "Milk", "Wine", "Oil"],
    "answer": "Wine",
    "difficulty": "easy"
  },
  {
    "question": "What did Jesus feed the five thousand with?",
    "options": ["Bread and fish", "Rice and lamb", "Fruit and honey", "Bread and water"],
    "answer": "Bread and fish",
    "difficulty": "easy"
  },
  {
    "question": "Who denied Jesus three times?",
    "options": ["John", "Judas", "Peter", "Thomas"],
    "answer": "Peter",
    "difficulty": "easy"
  },
  {
    "question": "On what day did Jesus rise from the dead?",
    "options": ["The first day", "The second day", "The third day", "The seventh day"],
    "answer": "The third day",
    "difficulty": "easy"
  }
]

# Columns: PlayerID, Name, Timestamp, Q0..Qn, Score (%), Total Points, Violations
HEADER = (
    ["PlayerID", "Name", "Timestamp"]
    + [f"Q{i}" for i in range(len(quiz))]
    + ["Score (%)", "Total Points", "Violations"]
)
ROW_WIDTH = len(HEADER)


# ---------------------------------------------------------------------------
# Storage layer: Google Sheets (primary) or local CSV (fallback)
# ---------------------------------------------------------------------------
_worksheet = None  # cached gspread worksheet handle


def _get_worksheet():
    """Connect to the Google Sheet (cached). Creates the worksheet/header if missing."""
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    try:
        ws = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=WORKSHEET_NAME, rows=1000, cols=ROW_WIDTH
        )

    first_row = ws.row_values(1)
    if first_row != HEADER:
        if not first_row:
            ws.append_row(HEADER, value_input_option="RAW")
        else:
            ws.update("A1", [HEADER], value_input_option="RAW")

    _worksheet = ws
    return _worksheet


def _ensure_local_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADER)


def storage_append_row(row):
    """Append one response row to the active backend."""
    if USE_SHEETS:
        ws = _get_worksheet()
        ws.append_row([str(c) for c in row], value_input_option="RAW")
    else:
        _ensure_local_csv()
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)


def storage_get_rows():
    """Return all response rows (header excluded), padded to full width."""
    if USE_SHEETS:
        ws = _get_worksheet()
        all_values = ws.get_all_values()
        rows = all_values[1:] if all_values else []
    else:
        _ensure_local_csv()
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            try:
                next(reader)  # skip header
            except StopIteration:
                return []
            rows = list(reader)
    # Sheets drops trailing empty cells; pad so column indexing is safe
    return [r + [""] * (ROW_WIDTH - len(r)) for r in rows]


def storage_csv_bytes():
    """Render the full all-time dataset (header + rows) as CSV bytes."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(HEADER)
    for row in storage_get_rows():
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_player_id(name):
    """Generate a unique ID for each player based on name and timestamp"""
    unique_string = f"{name}_{time.time()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get('name')
        player_id = generate_player_id(name)

        session['player_id'] = player_id
        session['name'] = name
        session['theme'] = request.form.get('theme', 'light')
        session['answers'] = []
        session['current_question'] = 0
        session['total_points'] = 0
        session['question_start_time'] = None
        session['timestamp'] = time.strftime(TIMESTAMP_FMT)
        session['violations'] = 0
        return redirect(url_for('quiz_question'))
    return render_template("welcome.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz_question():
    if 'name' not in session:
        return redirect(url_for('index'))

    current_q = session.get('current_question', 0)

    if request.method == "POST":
        answer = request.form.get('answer')
        time_taken = float(request.form.get('time_taken', TIME_LIMIT_SECONDS))
        terminated = request.form.get('terminated', 'false') == 'true'

        violations_from_form = request.form.get('violations_count', '0')
        try:
            session['violations'] = int(violations_from_form)
        except ValueError:
            pass

        if terminated:
            while len(session['answers']) < len(quiz):
                session['answers'].append('')
            session['quiz_terminated'] = True
            return redirect(url_for('complete'))

        if answer == quiz[current_q]["answer"]:
            points = max(10, MAX_POINTS_PER_QUESTION - (time_taken / TIME_LIMIT_SECONDS * (MAX_POINTS_PER_QUESTION - 10)))
            points = round(points)
        else:
            points = 0

        session['answers'].append(answer)
        session['total_points'] = session.get('total_points', 0) + points
        session['current_question'] = current_q + 1

        if session['current_question'] >= len(quiz):
            return redirect(url_for('complete'))

        return redirect(url_for('quiz_question'))

    if current_q >= len(quiz):
        return redirect(url_for('complete'))

    if 'violations' not in session:
        session['violations'] = 0

    question = quiz[current_q]
    progress = ((current_q) / len(quiz)) * 100

    return render_template("quiz.html",
                         question=question,
                         question_num=current_q + 1,
                         total=len(quiz),
                         progress=progress,
                         theme=session.get('theme', 'light'),
                         max_points=MAX_POINTS_PER_QUESTION,
                         time_limit=TIME_LIMIT_SECONDS,
                         current_violations=session.get('violations', 0))


@app.route("/complete")
def complete():
    FUN_FACT = "Did you know? The Bible is the most translated book in the world, available in over 3,000 languages!"

    if 'name' not in session or 'answers' not in session:
        return redirect(url_for('index'))

    player_id = session['player_id']
    name = session['name']
    answers = session['answers']
    total_points = session.get('total_points', 0)
    was_terminated = session.get('quiz_terminated', False)
    timestamp = session.get('timestamp', time.strftime(TIMESTAMP_FMT))
    violations = session.get('violations', 0)

    correct = 0
    for user_answer, q in zip(answers, quiz):
        if user_answer == q["answer"]:
            correct += 1
    percentage_score = round((correct / len(quiz)) * 100, 2)

    storage_append_row(
        [player_id, name, timestamp] + answers + [percentage_score, total_points, violations]
    )

    # Prevent a refresh of /complete from writing a duplicate row
    session.pop('answers', None)

    theme = session.get('theme', 'light')
    max_possible_points = MAX_POINTS_PER_QUESTION * len(quiz)

    return render_template("complete.html",
                           name=name,
                           theme=theme,
                           score=percentage_score,
                           total_points=total_points,
                           max_possible_points=max_possible_points,
                           fun_fact=FUN_FACT,
                           total_questions=len(quiz),
                           was_terminated=was_terminated,
                           player_id=player_id)


@app.route("/results/<player_id>")
def view_results(player_id):
    """Private results page for each player (all-time lookup, not reset-filtered)."""
    player_data = None

    for row in storage_get_rows():
        if row and row[0] == player_id:
            player_data = {
                "player_id": row[0],
                "name": row[1],
                "timestamp": row[2],
                "answers": row[3:3 + len(quiz)],
                "percentage": float(row[3 + len(quiz)] or 0),
                "points": int(row[3 + len(quiz) + 1] or 0),
                "violations": int(row[3 + len(quiz) + 2] or 0),
            }
            break

    if not player_data:
        abort(404, description="Results not found")

    detailed_results = []
    for i, (user_answer, question) in enumerate(zip(player_data["answers"], quiz)):
        is_correct = user_answer == question["answer"]
        detailed_results.append({
            "question_num": i + 1,
            "question": question["question"],
            "user_answer": user_answer,
            "correct_answer": question["answer"],
            "is_correct": is_correct,
            "difficulty": question["difficulty"]
        })

    return render_template("results.html",
                         player_data=player_data,
                         detailed_results=detailed_results,
                         total_questions=len(quiz),
                         max_possible_points=MAX_POINTS_PER_QUESTION * len(quiz))


@app.route("/leaderboard")
def leaderboard():
    """Leaderboard showing only entries since the last deployment."""
    leaderboard_data = []

    score_idx = 3 + len(quiz)
    points_idx = score_idx + 1
    violations_idx = score_idx + 2

    for row in storage_get_rows():
        if len(row) < ROW_WIDTH:
            continue
        if not row[0]:
            continue
        try:
            leaderboard_data.append({
                "player_id": row[0],
                "name": row[1],
                "percentage": float(row[score_idx] or 0),
                "points": int(row[points_idx] or 0),
                "violations": int(row[violations_idx] or 0),
            })
        except ValueError:
            continue  # skip malformed rows rather than 500

    leaderboard_data.sort(key=lambda x: (x["percentage"], x["points"]), reverse=True)

    return render_template("leaderboard.html",
                         leaderboard=leaderboard_data,
                         total_questions=len(quiz),
                         max_possible_points=MAX_POINTS_PER_QUESTION * len(quiz))


@app.route("/download")
def download_csv():
    """Hidden admin endpoint: downloads the FULL all-time CSV (not reset-filtered)."""
    token = request.args.get('token', '')
    if token != ADMIN_TOKEN:
        abort(403, description="Unauthorized access")

    data = storage_csv_bytes()
    filename = f"quiz_responses_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)