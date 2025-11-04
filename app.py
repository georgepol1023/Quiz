from flask import Flask, request, render_template, session, redirect, url_for, send_file

import csv
import os

app = Flask(__name__)
app.secret_key = os.environ['SESSION_SECRET']


@app.route("/download")
def download():
    return send_file(CSV_FILE, mimetype="text/csv", as_attachment=True)

quiz = [
    {
        "question": "Who parted the Red Sea?",
        "options": ["Moses", "David", "Jesus", "Paul"]
    },
    {
        "question": "What is the first book of the Bible?",
        "options": ["Genesis", "Exodus", "Leviticus", "Numbers"]
    },
    {
        "question": "Who was thrown into the lions' den?",
        "options": ["Daniel", "Joseph", "Elijah", "Jonah"]
    },
]

CSV_FILE = "responses.csv"

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name"] + [f"Q{i}" for i in range(len(quiz))])

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
    if 'name' not in session or 'answers' not in session:
        return redirect(url_for('index'))
    
    name = session['name']
    answers = session['answers']
    
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([name] + answers)
    
    theme = session.get('theme', 'light')
    session.clear()
    
    return render_template("complete.html", name=name, theme=theme)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)