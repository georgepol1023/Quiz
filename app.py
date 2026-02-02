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
        "question": "Who built the ark during the great flood?",
        "options": ["Moses", "Noah", "Abraham", "David"],
        "answer": "Noah"
    },
    {
        "question": "What city were Adam and Eve placed near in the beginning?",
        "options": ["Jerusalem", "Bethlehem", "The Garden of Eden", "Nazareth"],
        "answer": "The Garden of Eden"
    },
    {
        "question": "What did God create on the second day?",
        "options": ["Animals", "The sky", "Land", "People"],
        "answer": "The sky"
    },
    {
        "question": "Who led the Israelites out of Egypt?",
        "options": ["Joseph", "Aaron", "Moses", "Joshua"],
        "answer": "Moses"
    },
    {
        "question": "What was David before he became king?",
        "options": ["A shepherd", "A priest", "A soldier", "A farmer"],
        "answer": "A shepherd"
    },
    {
        "question": "What giant did David defeat?",
        "options": ["Goliath", "Samson", "Nebuchadnezzar", "Pharaoh"],
        "answer": "Goliath"
    },
    {
        "question": "How many days and nights did it rain during the flood?",
        "options": ["7", "12", "40", "100"],
        "answer": "40"
    },
    {
        "question": "Who swallowed Jonah in the Bible story?",
        "options": ["A shark", "A whale", "A giant fish", "A sea serpent"],
        "answer": "A giant fish"
    },
    {
        "question": "What food fell from heaven to feed the Israelites in the desert?",
        "options": ["Bread", "Manna", "Rice", "Fish"],
        "answer": "Manna"
    },
    {
        "question": "Who betrayed Jesus?",
        "options": ["Peter", "John", "Judas", "Matthew"],
        "answer": "Judas"
    },
    {
        "question": "What did Jesus walk on to reach His disciples?",
        "options": ["Sand", "Stones", "Water", "A bridge"],
        "answer": "Water"
    },
    {
        "question": "Where was Jesus born?",
        "options": ["Nazareth", "Jerusalem", "Bethlehem", "Capernaum"],
        "answer": "Bethlehem"
    },
    {
        "question": "What was the name of the strong man in the Bible?",
        "options": ["Samuel", "Solomon", "Samson", "Saul"],
        "answer": "Samson"
    },
    {
        "question": "How many disciples did Jesus have?",
        "options": ["7", "10", "12", "20"],
        "answer": "12"
    },
    {
        "question": "What did Jesus calm during the storm?",
        "options": ["The fire", "The crowd", "The sea", "The rain"],
        "answer": "The sea"
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