import os
import random
import psycopg2
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(database_url)

def init_db():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS passages (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cur.close()
    finally:
        conn.close()

def get_passages(limit=10):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, text, created_at
            FROM passages
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        passages = cur.fetchall()
        cur.close()
        return passages
    finally:
        conn.close()

def make_sentences(text):
    text = text.replace("?", ".")
    text = text.replace("!", ".")
    raw = text.split(".")
    sentences = []
    for sentence in raw:
        sentence = sentence.strip()
        if sentence:
            sentences.append(sentence)
    return sentences

def start_round(sentences):
    session["sentences"] = sentences
    session["current"] = 0
    session["correct"] = 0
    session["total"] = len(sentences)
    session["wrong"] = []

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        sentences = make_sentences(text)
        if not sentences:
            return render_template(
                "index.html",
                error="문장을 입력해주세요.",
                passages=get_passages()
            )
        start_round(sentences)
        return redirect(url_for("quiz"))

    passages = get_passages()
    return render_template("index.html", passages=passages)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    sentences = session.get("sentences")
    if not sentences:
        return redirect(url_for("index"))

    current = session.get("current", 0)
    total = session.get("total", len(sentences))

    if current >= total:
        return redirect(url_for("result"))

    feedback = None
    correct_answer = None
    is_correct = None
    user_input = None

    if request.method == "POST":
        user_input = request.form.get("answer", "").strip()
        answer_sentence = sentences[current]

        user_words = user_input.split()
        answer_words = answer_sentence.split()

        is_correct = (user_words == answer_words)

        if is_correct:
            session["correct"] = session.get("correct", 0) + 1
            feedback = "정답!"
        else:
            feedback = "오답!"
            correct_answer = answer_sentence
            wrong = session.get("wrong", [])
            wrong.append(answer_sentence)
            session["wrong"] = wrong

        session["current"] = current + 1
        current = session["current"]

        if current >= total:
            return render_template(
                "result.html",
                correct=session.get("correct", 0),
                total=total,
                wrong_count=len(session.get("wrong", [])),
                feedback=feedback,
                is_correct=is_correct,
                correct_answer=correct_answer,
                user_answer=user_input if not is_correct else None  # ✨ 오답 데이터 전달
            )

    sentence = sentences[current]
    words = sentence.split()
    shuffled = words.copy()
    random.shuffle(shuffled)
    progress = current + 1

    return render_template(
        "quiz.html",
        shuffled=shuffled,
        progress=progress,
        total=total,
        feedback=feedback,
        is_correct=is_correct,
        correct_answer=correct_answer,
        user_answer=user_input if (request.method == "POST" and not is_correct) else None  # ✨ 오답 데이터 전달
    )

@app.route("/result")
def result():
    correct = session.get("correct", 0)
    total = session.get("total", 0)
    wrong_count = len(session.get("wrong", []))
    return render_template("result.html", correct=correct, total=total, wrong_count=wrong_count)

@app.route("/retry")
def retry():
    wrong = session.get("wrong", [])
    if not wrong:
        return redirect(url_for("index"))
    start_round(wrong)
    return redirect(url_for("quiz"))

@app.route("/fill")
def fill():
    return render_template("fill.html")

@app.route("/passage/<int:passage_id>")
def passage_game(passage_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT text FROM passages WHERE id = %s", (passage_id,))
        result = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if result is None:
        return redirect(url_for("passages"))

    text = result[0]
    sentences = make_sentences(text)
    if not sentences:
        return redirect(url_for("passages"))

    start_round(sentences)
    return redirect(url_for("quiz"))

@app.route("/passages", methods=["GET", "POST"])
def passages():
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO passages (text) VALUES (%s)", (text,))
                conn.commit()
                cur.close()
            finally:
                conn.close()
        return redirect(url_for("passages"))

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, text, created_at FROM passages ORDER BY id DESC")
        saved_passages = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    return render_template("passages.html", passages=saved_passages)

@app.route("/passages/delete/<int:passage_id>", methods=["POST"])
def delete_passage(passage_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM passages WHERE id = %s", (passage_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return redirect(url_for("passages"))

try:
    init_db()
except Exception as e:
    print("DB 초기화 실패:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
