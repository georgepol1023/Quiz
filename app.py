from flask import Flask, request, render_template, session, redirect, url_for, send_file
import csv
import os

app = Flask(__name__)
app.secret_key = os.environ['SESSION_SECRET']


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
        "question": "Who built the ark?",
        "options": ["Moses", "Noah", "Abraham", "David"],
        "answer": "Noah"
    },
    {
        "question": "What did God create on the first day?",
        "options": ["Sun and moon", "Light", "Animals", "Plants"],
        "answer": "Light"
    },
    {
        "question": "Who was swallowed by a big fish?",
        "options": ["Jonah", "Daniel", "Joseph", "Elijah"],
        "answer": "Jonah"
    },
    {
        "question": "How many commandments did God give Moses?",
        "options": ["5", "10", "7", "12"],
        "answer": "10"
    },
    {
        "question": "Who was the mother of Jesus?",
        "options": ["Mary", "Sarah", "Ruth", "Elizabeth"],
        "answer": "Mary"
    },
    {
        "question": "What did David use to defeat Goliath?",
        "options": ["Sword", "Spear", "Sling and stone", "Bow and arrow"],
        "answer": "Sling and stone"
    },
    {
        "question": "Where was Jesus born?",
        "options": ["Nazareth", "Bethlehem", "Jerusalem", "Jericho"],
        "answer": "Bethlehem"
    },
    {
        "question": "Who betrayed Jesus?",
        "options": ["Peter", "Judas", "John", "Thomas"],
        "answer": "Judas"
    },
    {
        "question": "What river did John the Baptist baptize people in?",
        "options": ["Nile", "Jordan", "Euphrates", "Tigris"],
        "answer": "Jordan"
    },
    {
        "question": "Who led the Israelites out of Egypt?",
        "options": ["Abraham", "Moses", "Joshua", "Samuel"],
        "answer": "Moses"
    },
]

CSV_FILE = "responses.csv"

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name"] + [f"Q{i}" for i in range(len(quiz))] + ["Score"])

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

    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
