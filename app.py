from flask import Flask, request, render_template
import csv
import os

app = Flask(__name__)

# Dynamic quiz questions
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
        "question": "Who was thrown into the lions’ den?",
        "options": ["Daniel", "Joseph", "Elijah", "Jonah"]
    },
]

CSV_FILE = "responses.csv"

# Ensure CSV exists with headers
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([f"Q{i}" for i in range(len(quiz))])

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        answers = [request.form.get(f"q{i}") for i in range(len(quiz))]
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(answers)
        return "<h3>Thanks! Your answers have been submitted. Results will be shared later.</h3>"
    return render_template("quiz.html", quiz=quiz)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
