import os
import random
import psycopg2

from flask import Flask, render_template, request, session, redirect, url_for


app = Flask(__name__)

# Render 환경변수에서 SECRET_KEY 가져오기
app.secret_key = os.environ.get(
    'SECRET_KEY',
    'change-this-secret-key'
)


# =========================================================
# 데이터베이스
# =========================================================

def get_db():
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        raise Exception(
            'DATABASE_URL 환경변수가 설정되지 않았습니다.'
        )

    return psycopg2.connect(database_url)


def init_db():

    conn = get_db()
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
    conn.close()


def get_passages():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, text, created_at
        FROM passages
        ORDER BY id DESC
        LIMIT 10
    """)

    passages = cur.fetchall()

    cur.close()
    conn.close()

    return passages


# =========================================================
# 문장 처리
# =========================================================

def make_sentences(text):

    text = text.replace('?', '.').replace('!', '.')

    raw = text.split('.')

    sentences = []

    for s in raw:

        s = s.strip()

        if s != '':
            sentences.append(s)

    return sentences


# =========================================================
# 게임 라운드 시작
# =========================================================

def start_round(sentences):

    session['sentences'] = sentences
    session['current'] = 0
    session['correct'] = 0
    session['total'] = len(sentences)
    session['wrong'] = []


# =========================================================
# 메인 페이지
# =========================================================

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':

        text = request.form.get('text', '').strip()

        sentences = make_sentences(text)

        if not sentences:

            return render_template(
                'index.html',
                error='문장을 입력해주세요.',
                passages=get_passages()
            )

        start_round(sentences)

        return redirect(url_for('quiz'))

    passages = get_passages()

    return render_template(
        'index.html',
        passages=passages
    )


# =========================================================
# 문장 순서 퀴즈
# =========================================================

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():

    sentences = session.get('sentences')
    current = session.get('current', 0)

    if sentences is None:
        return redirect(url_for('index'))

    feedback = None
    correct_answer = None
    is_correct = None

    # -----------------------------------------
    # 정답 제출
    # -----------------------------------------

    if request.method == 'POST':

        user_input = request.form.get('answer', '')

        user_words = user_input.split()

        answer_sentence = sentences[current]

        answer_words = answer_sentence.split()

        is_correct = (user_words == answer_words)

        if is_correct:

            session['correct'] = session.get(
                'correct',
                0
            ) + 1

            feedback = '정답!'

        else:

            feedback = '오답!'

            correct_answer = answer_sentence

            wrong = session.get('wrong', [])

            wrong.append(answer_sentence)

            session['wrong'] = wrong

        session['current'] = current + 1

        current = session['current']

        # -----------------------------------------
        # 모든 문제 종료
        # -----------------------------------------

        if current >= session.get('total', 0):

            return render_template(
                'result.html',
                correct=session.get('correct', 0),
                total=session.get('total', 0),
                wrong_count=len(
                    session.get('wrong', [])
                ),
                feedback=feedback,
                is_correct=is_correct,
                correct_answer=correct_answer
            )

    # -----------------------------------------
    # 혹시 이미 끝났다면
    # -----------------------------------------

    if current >= session.get('total', 0):

        return redirect(url_for('result'))

    # -----------------------------------------
    # 현재 문장
    # -----------------------------------------

    sentence = sentences[current]

    words = sentence.split()

    shuffled = words.copy()

    random.shuffle(shuffled)

    progress = current + 1

    total = session.get('total', 0)

    return render_template(
        'quiz.html',
        shuffled=shuffled,
        progress=progress,
        total=total,
        feedback=feedback,
        is_correct=is_correct,
        correct_answer=correct_answer
    )


# =========================================================
# 결과
# =========================================================

@app.route('/result')
def result():

    correct = session.get('correct', 0)

    total = session.get('total', 0)

    wrong_count = len(
        session.get('wrong', [])
    )

    return render_template(
        'result.html',
        correct=correct,
        total=total,
        wrong_count=wrong_count
    )


# =========================================================
# 틀린 문장 다시 풀기
# =========================================================

@app.route('/retry')
def retry():

    wrong = session.get('wrong', [])

    if not wrong:
        return redirect(url_for('index'))

    start_round(wrong)

    return redirect(url_for('quiz'))


# =========================================================
# 빈칸 퀴즈
# =========================================================

@app.route('/fill')
def fill():

    return render_template('fill.html')


# =========================================================
# 저장된 지문으로 게임 시작
# =========================================================

@app.route('/passage/<int:passage_id>')
def passage_game(passage_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT text
        FROM passages
        WHERE id = %s
        """,
        (passage_id,)
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    if result is None:

        return redirect(
            url_for('passages')
        )

    text = result[0]

    sentences = make_sentences(text)

    if not sentences:

        return redirect(
            url_for('passages')
        )

    start_round(sentences)

    return redirect(
        url_for('quiz')
    )


# =========================================================
# 지문 추가 / 관리
# =========================================================

@app.route('/passages', methods=['GET', 'POST'])
def passages():

    # -----------------------------------------
    # 지문 저장
    # -----------------------------------------

    if request.method == 'POST':

        text = request.form.get(
            'text',
            ''
        ).strip()

        if text:

            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO passages (text)
                VALUES (%s)
                """,
                (text,)
            )

            conn.commit()

            cur.close()
            conn.close()

        return redirect(
            url_for('passages')
        )

    # -----------------------------------------
    # 저장된 지문 불러오기
    # -----------------------------------------

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, text, created_at
        FROM passages
        ORDER BY id DESC
        """
    )

    saved_passages = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'passages.html',
        passages=saved_passages
    )


# =========================================================
# 지문 삭제
# =========================================================

@app.route(
    '/passages/delete/<int:passage_id>',
    methods=['POST']
)
def delete_passage(passage_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM passages
        WHERE id = %s
        """,
        (passage_id,)
    )

    conn.commit()

    cur.close()
    conn.close()

    return redirect(
        url_for('passages')
    )


# =========================================================
# DB 초기화
# =========================================================

try:

    init_db()

except Exception as e:

    print(
        'DB 초기화 실패:',
        e
    )


# =========================================================
# 로컬 실행
# =========================================================

if __name__ == '__main__':

    app.run(
        debug=True
    )
