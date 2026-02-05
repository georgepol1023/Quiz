from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort
import csv
import os
import time
import secrets
import hashlib

app = Flask(__name__)
app.secret_key = "praisejesus"

# Fixed admin token - CHANGE THIS TO YOUR OWN SECRET VALUE!
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'my_bible_quiz_secret_2024')

print(f"Admin download URL: http://localhost:5000/download?token={ADMIN_TOKEN}")


quiz = [
    {
    "question": "On which day did God create humans?",
    "options": ["Fourth day", "Fifth day", "Sixth day", "Seventh day"],
    "answer": "Sixth day",
    "difficulty": "easy"
},
{
    "question": "What did God create on the first day?",
    "options": ["Land and seas", "Light", "Sun and moon", "Animals"],
    "answer": "Light",
    "difficulty": "easy"
},
{
    "question": "Who lived the longest according to Genesis?",
    "options": ["Adam", "Noah", "Methuselah", "Enoch"],
    "answer": "Methuselah",
    "difficulty": "easy"
},
{
    "question": "What material did God use to create Eve?",
    "options": ["Dust", "Clay", "Adam’s rib", "Breath"],
    "answer": "Adam’s rib",
    "difficulty": "easy"
},

{
    "question": "How many people were on the ark including Noah?",
    "options": ["6", "7", "8", "10"],
    "answer": "8",
    "difficulty": "medium"
},
{
    "question": "What tower did people build to reach the heavens?",
    "options": ["Tower of Jerusalem", "Tower of Eden", "Tower of Babel", "Tower of Sodom"],
    "answer": "Tower of Babel",
    "difficulty": "medium"
},
{
    "question": "Who was Abraham’s wife?",
    "options": ["Rebekah", "Leah", "Rachel", "Sarah"],
    "answer": "Sarah",
    "difficulty": "medium"
},
{
    "question": "What was the name of Abraham’s son with Hagar?",
    "options": ["Isaac", "Ishmael", "Esau", "Lot"],
    "answer": "Ishmael",
    "difficulty": "medium"
},

{
    "question": "What was the name of Isaac’s wife?",
    "options": ["Sarah", "Leah", "Rachel", "Rebekah"],
    "answer": "Rebekah",
    "difficulty": "hard"
},
{
    "question": "Which twin did Isaac favor?",
    "options": ["Jacob", "Esau", "Joseph", "Benjamin"],
    "answer": "Esau",
    "difficulty": "hard"
},
{
    "question": "What was Joseph’s special garment called?",
    "options": [
        "A royal robe",
        "A linen cloak",
        "A coat of many colors",
        "A priestly tunic"
    ],
    "answer": "A coat of many colors",
    "difficulty": "hard"
},
{
    "question": "What animals did God instruct Noah to take seven pairs of?",
    "options": ["Wild animals", "Birds", "Clean animals", "Creeping things"],
    "answer": "Clean animals",
    "difficulty": "hard"
}
]

CSV_FILE = "responses.csv"
MAX_POINTS_PER_QUESTION = 50
TIME_LIMIT_SECONDS = 15  # Time until points reach minimum

def generate_player_id(name):
    """Generate a unique ID for each player based on name and timestamp"""
    unique_string = f"{name}_{time.time()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["PlayerID", "Name", "Timestamp"] + [f"Q{i}" for i in range(len(quiz))] + ["Score (%)", "Total Points"])

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
        session['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
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
        
        # Update violations count from form if provided
        violations_from_form = request.form.get('violations_count', '0')
        try:
            session['violations'] = int(violations_from_form)
        except:
            pass
        
        # If quiz was terminated due to violations, mark all remaining as wrong
        if terminated:
            # Fill remaining answers with empty strings (wrong answers)
            while len(session['answers']) < len(quiz):
                session['answers'].append('')
            session['quiz_terminated'] = True
            return redirect(url_for('complete'))
        
        # Calculate points based on time taken
        if answer == quiz[current_q]["answer"]:
            # Points decrease linearly from MAX_POINTS to 10 over TIME_LIMIT_SECONDS
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
    
    # Initialize violations count if not set
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
    timestamp = session.get('timestamp', time.strftime("%Y-%m-%d %H:%M:%S"))

    # Calculate percentage score
    correct = 0
    for user_answer, q in zip(answers, quiz):
        if user_answer == q["answer"]:
            correct += 1
    percentage_score = round((correct / len(quiz)) * 100, 2)
    
    # Save player_id, name, timestamp, answers, percentage score, and total points to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([player_id, name, timestamp] + answers + [percentage_score, total_points])

    theme = session.get('theme', 'light')
    max_possible_points = MAX_POINTS_PER_QUESTION * len(quiz)

    # Don't clear session yet - we need player_id for results page
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
    """Private results page for each player"""
    player_data = None
    
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header row
            
            for row in reader:
                if row[0] == player_id:  # Match player_id
                    player_data = {
                        "player_id": row[0],
                        "name": row[1],
                        "timestamp": row[2],
                        "answers": row[3:3+len(quiz)],
                        "percentage": float(row[-2]),
                        "points": int(row[-1])
                    }
                    break
    
    if not player_data:
        abort(404, description="Results not found")
    
    # Build detailed results with correct/incorrect for each question
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
    leaderboard_data = []
    
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) > len(quiz) + 3:  # Make sure row has all data
                    player_id = row[0]
                    name = row[1]
                    percentage = float(row[-2])
                    points = int(row[-1])
                    leaderboard_data.append({
                        "player_id": player_id,
                        "name": name, 
                        "percentage": percentage,
                        "points": points
                    })
    
    # Sort by percentage (highest first), then by points as tiebreaker
    leaderboard_data.sort(key=lambda x: (x["percentage"], x["points"]), reverse=True)
    
    return render_template("leaderboard.html", 
                         leaderboard=leaderboard_data,
                         total_questions=len(quiz),
                         max_possible_points=MAX_POINTS_PER_QUESTION * len(quiz))

@app.route("/download")
def download_csv():
    """Hidden admin endpoint to download all responses CSV"""
    token = request.args.get('token', '')
    
    # Check if token matches
    if token != ADMIN_TOKEN:
        abort(403, description="Unauthorized access")
    
    if not os.path.exists(CSV_FILE):
        abort(404, description="No data available")
    
    return send_file(CSV_FILE, 
                    as_attachment=True, 
                    download_name=f"quiz_responses_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mimetype='text/csv')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)