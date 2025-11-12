from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import os
import csv
from datetime import datetime
import json

# Определяем путь к build папке
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, '..', 'frontend', 'build')

app = Flask(__name__, static_folder=BUILD_DIR, static_url_path='')
CORS(app)

QUESTIONS_FILE = "questions.txt"
RESULTS_FILE = "results.csv"
RESULTS_JSON_FILE = "results.json"
VALID_IDS_FILE = "valid_ids.txt"
USED_IDS_FILE = "used_ids.txt"
PROGRESS_FILE = "progress.json"
ACTIVE_SESSIONS_FILE = "active_sessions.txt"

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
    except (ValueError, AttributeError):
        return None

def check_answer(user_answer, correct_answer):
    """Проверяет правильность ответа"""
    user_ans = user_answer.strip()
    correct_ans_str = correct_answer.strip()
    correct_options = [opt.strip() for opt in correct_ans_str.split("или")]

    user_norm_text = normalize_text(user_ans)

    for opt in correct_options:
        opt_norm_text = normalize_text(opt)

        if user_norm_text == opt_norm_text:
            return True

        user_num = to_number(user_ans)
        opt_num = to_number(opt)

        if user_num is not None and opt_num is not None:
            if abs(user_num - opt_num) <= 0.01:
                return True

        if user_ans.isdigit() and user_ans in opt:
            return True

    return False

def load_valid_ids():
    """Загружает список валидных ID"""
    if not os.path.exists(VALID_IDS_FILE):
        return set()
    with open(VALID_IDS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def load_used_ids():
    """Загружает список использованных ID"""
    if not os.path.exists(USED_IDS_FILE):
        return set()
    with open(USED_IDS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip() and not line.startswith('#'))

def mark_id_as_used(user_id):
    """Помечает ID как использованный"""
    with open(USED_IDS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{user_id}\n")

def load_active_sessions():
    """Загружает активные сессии"""
    if not os.path.exists(ACTIVE_SESSIONS_FILE):
        return {}
    sessions = {}
    with open(ACTIVE_SESSIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '|' in line:
                user_id, timestamp_str = line.split('|', 1)
                sessions[user_id] = datetime.fromisoformat(timestamp_str)
    return sessions

def save_active_sessions(sessions):
    """Сохраняет активные сессии"""
    with open(ACTIVE_SESSIONS_FILE, 'w', encoding='utf-8') as f:
        for user_id, timestamp in sessions.items():
            f.write(f"{user_id}|{timestamp.isoformat()}\n")

def clean_dead_sessions(sessions, timeout_minutes=2):
    """Удаляет мертвые сессии (старше timeout_minutes)"""
    now = datetime.now()
    alive_sessions = {}
    for user_id, timestamp in sessions.items():
        if (now - timestamp).total_seconds() < timeout_minutes * 60:
            alive_sessions[user_id] = timestamp
    return alive_sessions

def add_active_session(user_id):
    """Добавляет активную сессию"""
    sessions = load_active_sessions()
    sessions = clean_dead_sessions(sessions)
    sessions[user_id] = datetime.now()
    save_active_sessions(sessions)

def update_session_heartbeat(user_id):
    """Обновляет heartbeat для сессии"""
    sessions = load_active_sessions()
    sessions = clean_dead_sessions(sessions)
    if user_id in sessions:
        sessions[user_id] = datetime.now()
        save_active_sessions(sessions)
        return True
    return False

def remove_active_session(user_id):
    """Удаляет активную сессию"""
    sessions = load_active_sessions()
    if user_id in sessions:
        del sessions[user_id]
        save_active_sessions(sessions)

def is_session_active(user_id):
    """Проверяет, активна ли сессия"""
    sessions = load_active_sessions()
    sessions = clean_dead_sessions(sessions)
    return user_id in sessions

def is_id_valid(user_id):
    """Проверяет, валиден ли ID и не использован ли он"""
    valid_ids = load_valid_ids()
    used_ids = load_used_ids()
    
    if user_id not in valid_ids:
        return False, "Неверный ID"
    
    if user_id in used_ids:
        return False, "Этот ID уже был использован. Тест завершен."
    
    # Проверяем активные сессии
    if is_session_active(user_id):
        return False, "Кто-то уже решает тест под этим ID. Подождите или обратитесь к организатору."
    
    return True, "OK"

# Загружаем вопросы при старте
questions = load_questions_from_txt(QUESTIONS_FILE)

# Инициализация файла результатов
if not os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата/Время', 'ID Пользователя', 'Баллы', 'Макс. баллы', 'Процент', 'Время', 'Детали ответов'])

if not os.path.exists(RESULTS_JSON_FILE):
    with open(RESULTS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

# API endpoints
@app.route('/api/validate-id', methods=['POST'])
def validate_id():
    """Проверяет валидность ID и создает активную сессию"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    
    is_valid, message = is_id_valid(user_id)
    
    if is_valid:
        # Создаем активную сессию (НЕ блокируем навсегда!)
        add_active_session(user_id)
    
    return jsonify({
        'valid': is_valid,
        'message': message
    })

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Обновляет heartbeat для активной сессии"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    
    if update_session_heartbeat(user_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Сессия не найдена'}), 404

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Возвращает все вопросы (без ответов)"""
    questions_without_answers = []
    for q in questions:
        q_copy = q.copy()
        q_copy.pop('answer', None)
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

@app.route('/api/save-progress', methods=['POST'])
def save_progress():
    """Сохраняет прогресс пользователя на сервере"""
    data = request.json
    user_id = data.get('user_id', '').strip()
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    progress_data = {
        'user_id': user_id,
        'current_index': data.get('current_index', 0),
        'user_answers': data.get('user_answers', {}),
        'question_timers': data.get('question_timers', {}),
        'timestamp': datetime.now().isoformat()
    }
    
    # Загружаем существующие данные прогресса
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)
        else:
            all_progress = {}
    except (FileNotFoundError, json.JSONDecodeError):
        all_progress = {}
    
    # Сохраняем прогресс для данного пользователя
    all_progress[user_id] = progress_data
    
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)
    
    return jsonify({'success': True})

@app.route('/api/get-progress/<user_id>', methods=['GET'])
def get_progress(user_id):
    """Получает сохраненный прогресс пользователя"""
    try:
        if not os.path.exists(PROGRESS_FILE):
            return jsonify({'progress': None})
        
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
        
        progress = all_progress.get(user_id)
        
        if progress:
            # Проверяем что прогресс не старше 24 часов
            timestamp = datetime.fromisoformat(progress['timestamp'])
            hours_passed = (datetime.now() - timestamp).total_seconds() / 3600
            
            if hours_passed < 24:
                return jsonify({'progress': progress})
        
        return jsonify({'progress': None})
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({'progress': None})

@app.route('/api/result', methods=['POST'])
def calculate_result():
    """Вычисляет итоговый результат и сохраняет его"""
    data = request.json
    user_answers = data.get('answers', {})
    user_id = data.get('user_id', 'Неизвестный')
    total_time = data.get('total_time', 0)  # Время в секундах

    total_score = 0
    max_score = sum(q['score'] for q in questions)
    details = []

    for question_id_str, user_answer in user_answers.items():
        question_id = int(question_id_str)
        if question_id < len(questions):
            question = questions[question_id]
            is_correct = check_answer(user_answer, question['answer'])
            if is_correct:
                total_score += question['score']
            
            details.append({
                'question_id': question_id,
                'title': question['title'],
                'user_answer': user_answer,
                'correct': is_correct,
                'score': question['score'] if is_correct else 0
            })

    percent = (total_score / max_score * 100) if max_score > 0 else 0

    # Форматируем время
    time_minutes = total_time // 60
    time_seconds = total_time % 60
    time_formatted = f"{time_minutes}:{time_seconds:02d}"
    
    # Сохранение результата в CSV
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(RESULTS_FILE, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            user_id,
            total_score,
            max_score,
            round(percent, 1),
            time_formatted,
            json.dumps(details, ensure_ascii=False)
        ])
    
    # Сохранение в JSON для удобного чтения
    try:
        with open(RESULTS_JSON_FILE, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_results = []
    
    all_results.append({
        'timestamp': timestamp,
        'user_id': user_id,
        'score': total_score,
        'max_score': max_score,
        'percent': round(percent, 1),
        'time': time_formatted,
        'time_seconds': total_time,
        'details': details
    })
    
    with open(RESULTS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Блокируем ID НАВСЕГДА и удаляем активную сессию
    mark_id_as_used(user_id)
    remove_active_session(user_id)

    return jsonify({
        'score': total_score,
        'max_score': max_score,
        'percent': round(percent, 1)
    })

@app.route('/api/results/download', methods=['GET'])
def download_results():
    """Скачать результаты в CSV"""
    if os.path.exists(RESULTS_FILE):
        return send_file(RESULTS_FILE, as_attachment=True, download_name='quiz_results.csv')
    return jsonify({'error': 'Результаты не найдены'}), 404

@app.route('/api/results/json', methods=['GET'])
def get_results_json():
    """Получить результаты в JSON"""
    if os.path.exists(RESULTS_JSON_FILE):
        with open(RESULTS_JSON_FILE, 'r', encoding='utf-8') as f:
            results = json.load(f)
        return jsonify(results)
    return jsonify([])

@app.route('/api/results/stats', methods=['GET'])
def get_stats():
    """Получить статистику по всем результатам"""
    if not os.path.exists(RESULTS_JSON_FILE):
        return jsonify({'total_users': 0, 'average_score': 0, 'average_percent': 0})
    
    with open(RESULTS_JSON_FILE, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    if not results:
        return jsonify({'total_users': 0, 'average_score': 0, 'average_percent': 0})
    
    total_users = len(results)
    average_score = sum(r['score'] for r in results) / total_users
    average_percent = sum(r['percent'] for r in results) / total_users
    
    return jsonify({
        'total_users': total_users,
        'average_score': round(average_score, 1),
        'average_percent': round(average_percent, 1),
        'results': results
    })

@app.route('/results_viewer.html')
def results_viewer():
    """Отдает страницу просмотра результатов"""
    return send_file('results_viewer.html')

# Serve React App
@app.route('/')
def serve():
    """Отдает главную страницу React"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Отдает статические файлы React"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Используем переменную окружения PORT для Railway, иначе 3000
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', debug=False, port=port)
