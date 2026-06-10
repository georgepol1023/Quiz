from flask import Flask, render_template, request, redirect, url_for, session, send_file, abort
import csv
import os
import time
import secrets
import hashlib

app = Flask(__name__)
app.secret_key = "praisejesus"

#download excel file : https://quiz-ehus.onrender.com/download?token=praisejesus


# Fixed admin token - CHANGE THIS TO YOUR OWN SECRET VALUE!
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'praisejesus')

print(f"Admin download URL: http://localhost:5000/download?token={ADMIN_TOKEN}")


quiz = [
  {
    "question": "What is the name of the mother of Jesus?",
    "options": ["Mary", "Martha", "Elizabeth", "Ruth"],
    "answer": "Mary",
    "difficulty": "easy"
  },
  {
    "question": "In what city was Jesus born?",
    "options": ["Jerusalem", "Nazareth", "Bethlehem", "Rome"],
    "answer": "Bethlehem",
    "difficulty": "easy"
  },
  {
    "question": "What was Jesus laid in after He was born because there was no room in the inn?",
    "options": ["A basket", "A manger", "A chariot", "A cradle"],
    "answer": "A manger",
    "difficulty": "easy"
  },
  {
    "question": "In the famous parable, who helped the beaten traveler after a priest and a Levite passed him by?",
    "options": ["A Pharisee", "A Roman soldier", "A Good Samaritan", "A fisherman"],
    "answer": "A Good Samaritan",
    "difficulty": "easy"
  },
  {
    "question": "What was the occupation of the men who were watching their flocks by night when the angels appeared?",
    "options": ["Carpenters", "Shepherds", "Farmers", "Tax collectors"],
    "answer": "Shepherds",
    "difficulty": "easy"
  },
  {
    "question": "Who was the cousin of Jesus who preached in the wilderness and baptized people?",
    "options": ["John the Baptist", "Peter", "Andrew", "James"],
    "answer": "John the Baptist",
    "difficulty": "easy"
  },
  {
    "question": "What was the occupation of Zacchaeus, the short man who climbed a tree to see Jesus?",
    "options": ["Fisherman", "Tax collector", "Carpenter", "Soldier"],
    "answer": "Tax collector",
    "difficulty": "easy"
  },
  {
    "question": "In the parable of the Prodigal Son, what does the father do when his lost son returns home?",
    "options": ["Rejects him", "Welcomes him with a feast", "Makes him a slave", "Sends him away"],
    "answer": "Welcomes him with a feast",
    "difficulty": "easy"
  },
  {
    "question": "How many disciples did Jesus choose to be His closest followers?",
    "options": ["3", "7", "12", "70"],
    "answer": "12",
    "difficulty": "easy"
  },
  {
    "question": "Which disciple denied knowing Jesus three times before the rooster crowed?",
    "options": ["Peter", "John", "Judas", "Thomas"],
    "answer": "Peter",
    "difficulty": "easy"
  },
  {
    "question": "What did Judas use to signal to the crowd which man was Jesus during His arrest?",
    "options": ["A handshake", "A kiss", "A pointed finger", "A torch"],
    "answer": "A kiss",
    "difficulty": "easy"
  },
  {
    "question": "Who was the Roman governor who handed Jesus over to be crucified?",
    "options": ["Herod", "Pontius Pilate", "Caesar", "Felix"],
    "answer": "Pontius Pilate",
    "difficulty": "easy"
  },
  {
    "question": "What happened to Jesus three days after He was crucified?",
    "options": ["He was moved to a new tomb", "He rose from the dead", "He went to Egypt", "Nothing"],
    "answer": "He rose from the dead",
    "difficulty": "easy"
  },
  {
    "question": "When Jesus visited Martha and Mary, which sister sat at Jesus' feet listening to Him?",
    "options": ["Mary", "Martha", "Elizabeth", "Sarah"],
    "answer": "Mary",
    "difficulty": "easy"
  },
  {
    "question": "After His resurrection, Jesus walked and talked with two disciples on the road to which town?",
    "options": ["Nazareth", "Emmaus", "Jericho", "Damascus"],
    "answer": "Emmaus",
    "difficulty": "medium"
  }
]

CSV_FILE = "responses.csv"
MAX_POINTS_PER_QUESTION = 50
TIME_LIMIT_SECONDS = 20  # Time until points reach minimum

def generate_player_id(name):
    """Generate a unique ID for each player based on name and timestamp"""
    unique_string = f"{name}_{time.time()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()[:16]

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["PlayerID", "Name", "Timestamp"] + [f"Q{i}" for i in range(len(quiz))] + ["Score (%)", "Total Points", "Violations"])

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
        session['violations'] = 0  # Initialize violations
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
    violations = session.get('violations', 0)

    # Calculate percentage score
    correct = 0
    for user_answer, q in zip(answers, quiz):
        if user_answer == q["answer"]:
            correct += 1
    percentage_score = round((correct / len(quiz)) * 100, 2)
    
    # Save player_id, name, timestamp, answers, percentage score, total points, and violations to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([player_id, name, timestamp] + answers + [percentage_score, total_points, violations])

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
                        "percentage": float(row[-3]),
                        "points": int(row[-2]),
                        "violations": int(row[-1])
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
                if len(row) > len(quiz) + 4:  # Make sure row has all data including violations
                    player_id = row[0]
                    name = row[1]
                    percentage = float(row[-3])
                    points = int(row[-2])
                    violations = int(row[-1])
                    leaderboard_data.append({
                        "player_id": player_id,
                        "name": name, 
                        "percentage": percentage,
                        "points": points,
                        "violations": violations
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