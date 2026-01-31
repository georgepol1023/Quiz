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
        "question": "Who was thrown into the lions' den?",
        "options": ["Daniel", "Joseph", "Moses", "Elijah"],
        "answer": "Daniel"
    },
    {
        "question": "Who was the strongest man in the Bible?",
        "options": ["David", "Samson", "Saul", "Esau"],
        "answer": "Samson"
    },
    {
        "question": "Who crossed the Jordan River by striking the water with his cloak?",
        "options": ["Elijah", "Elisha", "Moses", "Joshua"],
        "answer": "Elijah"
    },
    {
        "question": "What food did God provide the Israelites in the wilderness?",
        "options": ["Bread and fish", "Manna", "Grapes", "Quail eggs"],
        "answer": "Manna"
    },
    {
        "question": "Who was the first king of Israel?",
        "options": ["David", "Saul", "Solomon", "Samuel"],
        "answer": "Saul"
    },
    {
        "question": "Who anointed David to be king?",
        "options": ["Nathan", "Samuel", "Elijah", "Aaron"],
        "answer": "Samuel"
    },
    {
        "question": "Which sea did Moses part?",
        "options": ["Red Sea", "Dead Sea", "Galilee Sea", "Mediterranean Sea"],
        "answer": "Red Sea"
    },
    {
        "question": "Who climbed a sycamore tree to see Jesus?",
        "options": ["Zacchaeus", "Peter", "Bartimaeus", "Thomas"],
        "answer": "Zacchaeus"
    },
    {
        "question": "What did Jesus turn water into at the wedding?",
        "options": ["Milk", "Wine", "Oil", "Honey"],
        "answer": "Wine"
    },
    {
        "question": "Who was the shepherd boy that became a king?",
        "options": ["Solomon", "David", "Joshua", "Isaac"],
        "answer": "David"
    },
    {
        "question": "Which apostle denied Jesus three times?",
        "options": ["Peter", "Thomas", "John", "Andrew"],
        "answer": "Peter"
    },
    {
        "question": "Where did Jesus grow up?",
        "options": ["Bethlehem", "Nazareth", "Jerusalem", "Capernaum"],
        "answer": "Nazareth"
    },
    {
        "question": "Who interpreted Pharaoh's dreams about the cows and grain?",
        "options": ["Joseph", "Moses", "Daniel", "Aaron"],
        "answer": "Joseph"
    },
    {
        "question": "What weapon did Samson use to defeat a thousand Philistines?",
        "options": ["Spear", "Jawbone of a donkey", "Sword", "Rock"],
        "answer": "Jawbone of a donkey"
    },
    {
        "question": "Which disciple walked on water toward Jesus?",
        "options": ["Peter", "John", "James", "Philip"],
        "answer": "Peter"
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