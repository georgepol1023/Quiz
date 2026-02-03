from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os
import time

app = Flask(__name__)
app.secret_key = "your_secret_key_here_12345"

quiz = [
     {
        "question": "Who was Jesus' mother?",
        "options": ["Elizabeth", "Mary", "Martha", "Anna"],
        "answer": "Mary",
        "difficulty": "easy"
    },
    {
        "question": "Where was Jesus born?",
        "options": ["Nazareth", "Jerusalem", "Bethlehem", "Capernaum"],
        "answer": "Bethlehem",
        "difficulty": "easy"
    },
    {
        "question": "How many disciples did Jesus have?",
        "options": ["7", "10", "12", "20"],
        "answer": "12",
        "difficulty": "easy"
    },
    {
        "question": "Who baptized Jesus?",
        "options": ["Peter", "John the Baptist", "Matthew", "Paul"],
        "answer": "John the Baptist",
        "difficulty": "easy"
    },

    {
        "question": "What was Jesus’ first miracle?",
        "options": ["Healing a blind man", "Walking on water", "Turning water into wine", "Feeding the 5,000"],
        "answer": "Turning water into wine",
        "difficulty": "medium"
    },
    {
        "question": "Who denied Jesus three times?",
        "options": ["John", "Peter", "James", "Andrew"],
        "answer": "Peter",
        "difficulty": "medium"
    },
    {
        "question": "How many baskets of leftovers were collected after feeding the 5,000?",
        "options": ["5", "7", "10", "12"],
        "answer": "12",
        "difficulty": "medium"
    },
    {
        "question": "Which Gospel tells the story of the Good Samaritan?",
        "options": ["Matthew", "Mark", "Luke", "John"],
        "answer": "Luke",
        "difficulty": "medium"
    },

    {
        "question": "Who helped carry Jesus’ cross?",
        "options": ["Joseph of Arimathea", "Nicodemus", "Simon of Cyrene", "Barabbas"],
        "answer": "Simon of Cyrene",
        "difficulty": "hard"
    },
    {
        "question": "Who was released instead of Jesus?",
        "options": ["Barnabas", "Barabbas", "Silas", "Stephen"],
        "answer": "Barabbas",
        "difficulty": "hard"
    },
    {
        "question": "Which disciple was known for doubting Jesus’ resurrection?",
        "options": ["Philip", "Matthew", "Thomas", "Simon"],
        "answer": "Thomas",
        "difficulty": "hard"
    },
    {
        "question": "What happened at Pentecost?",
        "options": [
            "Jesus ascended to heaven",
            "The Holy Spirit came upon the disciples",
            "The temple was destroyed",
            "Jesus fed the crowd"
        ],
        "answer": "The Holy Spirit came upon the disciples",
        "difficulty": "hard"
    }
]

CSV_FILE = "responses.csv"
MAX_POINTS_PER_QUESTION = 100
TIME_LIMIT_SECONDS = 30  # Time until points reach minimum

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name"] + [f"Q{i}" for i in range(len(quiz))] + ["Score (%)", "Total Points"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['name'] = request.form.get('name')
        session['theme'] = request.form.get('theme', 'light')
        session['answers'] = []
        session['current_question'] = 0
        session['total_points'] = 0
        session['question_start_time'] = None
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
    
    question = quiz[current_q]
    progress = ((current_q) / len(quiz)) * 100
    
    return render_template("quiz.html", 
                         question=question, 
                         question_num=current_q + 1,
                         total=len(quiz),
                         progress=progress,
                         theme=session.get('theme', 'light'),
                         max_points=MAX_POINTS_PER_QUESTION,
                         time_limit=TIME_LIMIT_SECONDS)

@app.route("/complete")
def complete():
    FUN_FACT = "Did you know? The Bible is the most translated book in the world, available in over 3,000 languages!"

    if 'name' not in session or 'answers' not in session:
        return redirect(url_for('index'))

    name = session['name']
    answers = session['answers']
    total_points = session.get('total_points', 0)

    # Calculate percentage score
    correct = 0
    for user_answer, q in zip(answers, quiz):
        if user_answer == q["answer"]:
            correct += 1
    percentage_score = round((correct / len(quiz)) * 100, 2)
    
    # Save name, answers, percentage score, and total points to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name] + answers + [percentage_score, total_points])

    theme = session.get('theme', 'light')
    max_possible_points = MAX_POINTS_PER_QUESTION * len(quiz)

    # Clear session after saving
    session.clear()

    return render_template("complete.html",
                           name=name,
                           theme=theme,
                           score=percentage_score,
                           total_points=total_points,
                           max_possible_points=max_possible_points,
                           fun_fact=FUN_FACT,
                           total_questions=len(quiz))

@app.route("/leaderboard")
def leaderboard():
    leaderboard_data = []
    
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) > len(quiz) + 1:  # Make sure row has points data
                    name = row[0]
                    percentage = float(row[-2])
                    points = int(row[-1])
                    leaderboard_data.append({
                        "name": name, 
                        "percentage": percentage,
                        "points": points
                    })
    
    # Sort by points (highest first), then by percentage
    leaderboard_data.sort(key=lambda x: (x["points"], x["percentage"]), reverse=True)
    
    return render_template("leaderboard.html", 
                         leaderboard=leaderboard_data,
                         total_questions=len(quiz),
                         max_possible_points=MAX_POINTS_PER_QUESTION * len(quiz))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)