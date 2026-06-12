from flask import Flask, render_template, request, redirect, url_for, session, abort, Response
import csv
import io
import json
import os
import time
import hashlib
from datetime import datetime

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

# ---------------------------------------------------------------------------
# Per-deploy leaderboard reset.
#
# The leaderboard shows only responses submitted at or after DEPLOY_TIME;
# the sheet and /download always contain the full all-time history.
#
# DEPLOY_TIME is resolved in priority order:
#   1. RENDER_GIT_COMMIT  -> a real redeploy gives a new commit, so the reset
#      marker advances on deploy but NOT on an idle spin-up/spin-down (the
#      commit is unchanged). We map the commit to the process start time.
#   2. The current time at process start (fallback). Note: on Render's free
#      tier this also advances on spin-up after idle, so the board would clear
#      after an idle period too. Set RENDER_GIT_COMMIT (auto on Render) or a
#      manual DEPLOY_ID to avoid that.
#
# You can also force a manual reset any time by bumping the DEPLOY_ID env var.
# ---------------------------------------------------------------------------
# Floor to whole seconds: stored timestamps are second-resolution strings, so
# keeping microseconds here would wrongly exclude a response submitted in the
# same second the app started.
DEPLOY_TIME = datetime.now().replace(microsecond=0)
_deploy_marker = (
    os.environ.get("DEPLOY_ID")
    or os.environ.get("RENDER_GIT_COMMIT")
    or "local"
)

CSV_FILE = "responses.csv"  # local fallback only
MAX_POINTS_PER_QUESTION = 50
TIME_LIMIT_SECONDS = 20  # Time until points reach minimum
TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"

print(f"Admin download URL: http://localhost:5000/download?token={ADMIN_TOKEN}")
print(f"Storage backend: {'Google Sheets' if USE_SHEETS else 'local CSV (responses.csv)'}")
print(f"Leaderboard reset marker: {_deploy_marker} (showing entries since {DEPLOY_TIME:{TIMESTAMP_FMT}})")

quiz = [
  {
    "question": "What did Jesus say to the fishermen Simon and Andrew when He called them?",
    "options": ["Build a boat", "Follow Me, and I will make you fishers of men", "Go to Jerusalem", "Cast your nets at noon"],
    "answer": "Follow Me, and I will make you fishers of men",
    "difficulty": "easy"
  },
  {
    "question": "What illness did the friends bring to Jesus by lowering a man through the roof?",
    "options": ["Blindness", "Leprosy", "Paralysis", "Fever"],
    "answer": "Paralysis",
    "difficulty": "easy"
  },
  {
    "question": "What did Jesus calm with a command, saying, 'Peace! Be still!'?",
    "options": ["A crowd", "A storm", "A fire", "An army"],
    "answer": "A storm",
    "difficulty": "easy"
  },
  {
    "question": "What was the name of the ruler of the synagogue whose daughter Jesus raised to life?",
    "options": ["Nicodemus", "Jairus", "Zacchaeus", "Bartimaeus"],
    "answer": "Jairus",
    "difficulty": "easy"
  },
  {
    "question": "How many loaves did Jesus use to feed the five thousand?",
    "options": ["2", "5", "7", "12"],
    "answer": "5",
    "difficulty": "easy"
  },
  {
    "question": "How many fish were used along with the loaves to feed the five thousand?",
    "options": ["1", "2", "5", "12"],
    "answer": "2",
    "difficulty": "easy"
  },
  {
    "question": "What did Jesus walk on to reach His disciples during the night?",
    "options": ["A bridge", "The shore", "The water", "A boat"],
    "answer": "The water",
    "difficulty": "easy"
  },
  {
    "question": "What did blind Bartimaeus call out to Jesus?",
    "options": ["Teacher from Nazareth", "Son of David, have mercy on me!", "Lord of heaven", "King of Israel"],
    "answer": "Son of David, have mercy on me!",
    "difficulty": "easy"
  },
  {
    "question": "What kind of animal did Jesus ride when He entered Jerusalem?",
    "options": ["A horse", "A camel", "A donkey colt", "A mule"],
    "answer": "A donkey colt",
    "difficulty": "easy"
  },
  {
    "question": "What happened to the fig tree that Jesus cursed?",
    "options": ["It grew fruit", "It was cut down", "It withered", "It caught fire"],
    "answer": "It withered",
    "difficulty": "easy"
  },
  {
    "question": "During the Last Supper, what did Jesus say the bread was?",
    "options": ["The law", "His body", "The temple", "The kingdom"],
    "answer": "His body",
    "difficulty": "easy"
  },
  {
    "question": "Which disciple cut off the ear of the high priest's servant during Jesus' arrest?",
    "options": ["Peter", "John", "Thomas", "Philip"],
    "answer": "Peter",
    "difficulty": "easy"
  },
  {
    "question": "Who carried Jesus' cross on the way to Golgotha?",
    "options": ["Joseph of Arimathea", "Simon of Cyrene", "Barabbas", "Andrew"],
    "answer": "Simon of Cyrene",
    "difficulty": "easy"
  },
  {
    "question": "Who asked Pilate for permission to bury Jesus' body?",
    "options": ["Stephen", "Joseph of Arimathea", "Jairus", "Matthew"],
    "answer": "Joseph of Arimathea",
    "difficulty": "medium"
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


def _parse_ts(value):
    """Parse a stored timestamp string; return None if unparseable."""
    try:
        return datetime.strptime(value, TIMESTAMP_FMT)
    except (ValueError, TypeError):
        return None


def _row_is_current(row):
    """True if a row was submitted at/after this deployment's reset marker."""
    ts = _parse_ts(row[2]) if len(row) > 2 else None
    if ts is None:
        return False  # undated rows are treated as historical (hidden from board)
    return ts >= DEPLOY_TIME


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
        if not _row_is_current(row):
            continue  # submitted before this deploy -> hidden from board
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