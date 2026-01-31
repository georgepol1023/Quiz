from flask import Flask, request, render_template, session, redirect, url_for, send_file
import csv
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')


@app.route("/download")
def download():
    return send_file(
        CSV_FILE,
        mimetype="text/csv",
        as_attachment=True,
        download_name="responses.csv"
    )

quiz = [
    {
        "question": "What did God create on the very first day?",
        "options": ["Animals", "Light", "Trees", "The Moon"],
        "answer": "Light"
    },
    {
        "question": "How many commandments did God give to Moses?",
        "options": ["5", "10", "300", "none of the above"],
        "answer": "none of the above"
    },
    {
        "question": "What animal tempted Eve in the Garden of Eden?",
        "options": ["A lion", "A snake", "A bear", "A wolf"],
        "answer": "A snake"
    },
    {
        "question": "What did Jesus use to feed 5,000 people?",
        "options": ["Loaves and fishes", "Milk and honey", "Apples and nuts", "Steak and potatoes"],
        "answer": "Loaves and fishes"
    },
    {
        "question": "Who was the very first man created by God?",
        "options": ["Noah", "Abraham", "Adam", "Moses"],
        "answer": "Adam"
    },
    {
        "question": "What did Noah build to save the animals?",
        "options": ["A castle", "An ark", "A tower", "A bridge"],
        "answer": "An ark"
    },
    {
        "question": "Which bird brought back an olive branch to Noah?",
        "options": ["An eagle", "A raven", "A dove", "A sparrow"],
        "answer": "A dove"
    },
    {
        "question": "What was the name of Jesus' mother?",
        "options": ["Mary", "Martha", "Ruth", "Esther"],
        "answer": "Mary"
    },
    {
        "question": "What did the three wise men follow to find baby Jesus?",
        "options": ["A map", "A star", "A river", "A cloud"],
        "answer": "A star"
    },
    {
        "question": "What did Moses use to part the Red Sea?",
        "options": ["A sword", "A staff", "A shield", "A stone"],
        "answer": "A staff"
    },
    {
        "question": "Which day of the week did God rest after creating the world?",
        "options": ["The first day", "The third day", "The seventh day", "The tenth day"],
        "answer": "The seventh day"
    },
    {
        "question": "Who was thrown into a den of lions but wasn't hurt?",
        "options": ["Daniel", "David", "Peter", "Paul"],
        "answer": "Daniel"
    },
    {
        "question": "What did God put in the sky as a promise to never flood the Earth again?",
        "options": ["A rainbow", "The sun", "A comet", "A lightning bolt"],
        "answer": "A rainbow"
    },
    {
        "question": "What was Jesus' job before He started His ministry?",
        "options": ["A fisherman", "A carpenter", "A tax collector", "A soldier"],
        "answer": "A carpenter"
    },
    {
        "question": "Who killed his brother Abel?",
        "options": ["Cain", "Seth", "Enos", "Jared"],
        "answer": "Cain"
    }
]

CSV_FILE = "responses.csv"

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name"] + [f"Q{i}" for i in range(len(quiz))] + ["Score (%)"])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['name'] = request.form.get('name')
        session['theme'] = request.form.get('theme', 'light')
        session['answers'] = []
        session['current_question'] = 0
        return redirect(url_for('quiz_question'))
    return render_template("welcome.html")

@app.route("/quiz", methods=["GET", "POST"])
def quiz_question():
    if 'name' not in session:
        return redirect(url_for('index'))
    
    current_q = session.get('current_question', 0)
    
    if request.method == "POST":
        answer = request.form.get('answer')
        session['answers'].append(answer)
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
                         theme=session.get('theme', 'light'))

@app.route("/complete")
def complete():
    FUN_FACT = "Did you know? The Bible is the most translated book in the world, available in over 3,000 languages!"

    # Make sure the user actually has answers
    if 'name' not in session or 'answers' not in session:
        return redirect(url_for('index'))

    name = session['name']
    answers = session['answers']

    # Calculate score
    score = 0
    for user_answer, q in zip(answers, quiz):
        if user_answer == q["answer"]:
            score += 1
    score = score / len(quiz) * 100  # percentage
    score = round(score, 2)
    # Save name, answers, and score to CSV
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name] + answers + [score])

    theme = session.get('theme', 'light')

    # Clear session after saving
    session.clear()

    # Render completion page and pass score
    return render_template("complete.html",
                           name=name,
                           theme=theme,
                           score=score,
                           fun_fact=FUN_FACT,
                           total_questions=len(quiz))

@app.route("/leaderboard")
def leaderboard():
    # Read all scores from CSV
    leaderboard_data = []
    
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) > 0:
                    name = row[0]
                    score = float(row[-1])  # Last column is the score
                    leaderboard_data.append({"name": name, "score": score})
    
    # Sort by score (highest first)
    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
    
    return render_template("leaderboard.html", 
                         leaderboard=leaderboard_data,
                         total_questions=len(quiz))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)