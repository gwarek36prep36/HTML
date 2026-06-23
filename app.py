import random
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'change-this-secret-key'


def make_sentences(text):
    text = text.replace('?', '.').replace('!', '.')
    raw = text.split('.')
    sentences = []
    for s in raw:
        s = s.strip()
        if s != '':
            sentences.append(s)
    return sentences


def start_round(sentences):
    """현재 라운드(sentences 목록)에 대한 세션 상태를 초기화"""
    session['sentences'] = sentences
    session['current'] = 0
    session['correct'] = 0
    session['total'] = len(sentences)
    session['wrong'] = []  # 이번 라운드에서 틀린 문장들


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form.get('text', '')
        sentences = make_sentences(text)

        if not sentences:
            return render_template('index.html', error='문장을 입력해주세요.')

        start_round(sentences)
        return redirect(url_for('quiz'))

    return render_template('index.html')


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    sentences = session.get('sentences')
    current = session.get('current', 0)

    if sentences is None:
        return redirect(url_for('index'))

    feedback = None
    correct_answer = None
    is_correct = None

    if request.method == 'POST':
        user_input = request.form.get('answer', '')
        user_words = user_input.split()

        answer_sentence = sentences[current]
        answer_words = answer_sentence.split()

        is_correct = (user_words == answer_words)

        if is_correct:
            session['correct'] = session.get('correct', 0) + 1
            feedback = '정답!'
        else:
            feedback = '오답!'
            correct_answer = answer_sentence

            wrong = session.get('wrong', [])
            wrong.append(answer_sentence)
            session['wrong'] = wrong

        session['current'] = current + 1
        current = session['current']

        if current >= session.get('total', 0):
            return render_template(
                'result.html',
                correct=session.get('correct', 0),
                total=session.get('total', 0),
                wrong_count=len(session.get('wrong', [])),
                feedback=feedback,
                is_correct=is_correct,
                correct_answer=correct_answer
            )

    if current >= session.get('total', 0):
        return redirect(url_for('result'))

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


@app.route('/result')
def result():
    correct = session.get('correct', 0)
    total = session.get('total', 0)
    wrong_count = len(session.get('wrong', []))

    return render_template('result.html', correct=correct, total=total, wrong_count=wrong_count)


@app.route('/retry')
def retry():
    """틀린 문장만 모아서 새 라운드 시작"""
    wrong = session.get('wrong', [])

    if not wrong:
        return redirect(url_for('index'))

    start_round(wrong)
    return redirect(url_for('quiz'))

# 맨 아래 기존 코드 위에 붙이기
@app.route('/fill')
def fill():
    return render_template('fill.html')


if __name__ == '__main__':
    app.run(debug=True)
