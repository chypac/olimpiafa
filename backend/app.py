from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

QUESTIONS_FILE = "questions.txt"

def load_questions_from_txt(filename):
    """Загружает вопросы из текстового файла"""
    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return []

    blocks = [block.strip() for block in content.split('---') if block.strip()]
    questions = []

    for i, block in enumerate(blocks):
        lines = [line.rstrip() for line in block.splitlines()]

        q = {}
        current_key = None
        current_value_lines = []

        for line in lines:
            if not line.strip():
                continue

            key_match = None
            for key in ['title', 'text', 'answer', 'score', 'time_limit', 'hint']:
                if line.strip().lower().startswith(key + ':'):
                    key_match = key
                    break

            if key_match:
                if current_key:
                    value = '\n'.join(current_value_lines).strip()
                    q[current_key] = value
                    current_value_lines = []

                parts = line.split(':', 1)
                current_key = key_match.lower()
                value_part = parts[1].strip() if len(parts) > 1 else ""
                current_value_lines = [value_part]

            else:
                if current_key:
                    current_value_lines.append(line)

        if current_key:
            value = '\n'.join(current_value_lines).strip()
            q[current_key] = value

        q.setdefault('title', f"Вопрос {i+1}")
        q.setdefault('hint', "Подсказка недоступна.")
        q.setdefault('score', 1)
        q.setdefault('time_limit', 60)

        if 'text' not in q or not q['text'].strip():
            continue
        if 'answer' not in q or not q['answer'].strip():
            continue

        try:
            q['score'] = int(q['score'])
            q['time_limit'] = int(q['time_limit'])
        except ValueError:
            continue

        # Добавляем ID вопроса
        q['id'] = i
        questions.append(q)

    return questions

def normalize_text(s):
    """Нормализация для текстовых сравнений"""
    return s.strip().lower().replace(" ", "")

def to_number(s):
    """Преобразует строку в число"""
    try:
        return float(s.replace(",", "."))
    except:
        return None

def check_answer(user_answer, correct_answer):
    """Проверяет правильность ответа"""
    user_ans = user_answer.strip()
    correct_ans_str = correct_answer.strip()
    correct_options = [opt.strip() for opt in correct_ans_str.split("или")]

    user_norm_text = normalize_text(user_ans)

    for opt in correct_options:
        opt_norm_text = normalize_text(opt)

        # Точное текстовое совпадение
        if user_norm_text == opt_norm_text:
            return True

        # Проверка численных значений
        user_num = to_number(user_ans)
        opt_num = to_number(opt)

        if user_num is not None and opt_num is not None:
            if abs(user_num - opt_num) <= 0.01:
                return True

        # Для целых чисел
        if user_ans.isdigit() and user_ans in opt:
            return True

    return False

# Загружаем вопросы при старте
questions = load_questions_from_txt(QUESTIONS_FILE)

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Возвращает все вопросы (без ответов)"""
    questions_without_answers = []
    for q in questions:
        q_copy = q.copy()
        q_copy.pop('answer', None)  # Удаляем правильный ответ
        questions_without_answers.append(q_copy)
    return jsonify(questions_without_answers)

@app.route('/api/check-answer', methods=['POST'])
def check_answer_endpoint():
    """Проверяет ответ пользователя"""
    data = request.json
    question_id = data.get('question_id')
    user_answer = data.get('answer', '')

    if question_id is None or question_id >= len(questions):
        return jsonify({'error': 'Invalid question ID'}), 400

    question = questions[question_id]
    is_correct = check_answer(user_answer, question['answer'])

    return jsonify({
        'correct': is_correct,
        'score': question['score'] if is_correct else 0
    })

@app.route('/api/hint/<int:question_id>', methods=['GET'])
def get_hint(question_id):
    """Возвращает подсказку для вопроса"""
    if question_id >= len(questions):
        return jsonify({'error': 'Invalid question ID'}), 400

    return jsonify({'hint': questions[question_id].get('hint', 'Подсказка недоступна.')})

@app.route('/api/result', methods=['POST'])
def calculate_result():
    """Вычисляет итоговый результат"""
    data = request.json
    user_answers = data.get('answers', {})

    total_score = 0
    max_score = sum(q['score'] for q in questions)

    for question_id_str, user_answer in user_answers.items():
        question_id = int(question_id_str)
        if question_id < len(questions):
            question = questions[question_id]
            if check_answer(user_answer, question['answer']):
                total_score += question['score']

    percent = (total_score / max_score * 100) if max_score > 0 else 0
    
    if percent >= 80:
        grade = "Отлично!"
    elif percent >= 60:
        grade = "Хорошо!"
    else:
        grade = "Попробуйте ещё раз!"

    return jsonify({
        'score': total_score,
        'max_score': max_score,
        'percent': round(percent, 1),
        'grade': grade
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
