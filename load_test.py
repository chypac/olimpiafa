"""
Скрипт нагрузочного тестирования для quiz-app
Симулирует реальных пользователей, проходящих викторину
"""
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

# Настройки
BASE_URL = "http://localhost:5000"  # Или ваша ngrok ссылка
NUM_USERS = 50  # Количество одновременных пользователей
DURATION_SECONDS = 60  # Длительность теста

# Статистика
results = {
    'success': 0,
    'failed': 0,
    'response_times': []
}
lock = threading.Lock()

def simulate_user(user_id):
    """Симулирует одного пользователя, проходящего викторину"""
    try:
        # 1. Загрузка главной страницы
        start = time.time()
        response = requests.get(f"{BASE_URL}/", timeout=10)
        elapsed = time.time() - start
        
        with lock:
            results['response_times'].append(elapsed)
        
        if response.status_code != 200:
            with lock:
                results['failed'] += 1
            return
        
        # 2. Получение вопросов
        start = time.time()
        response = requests.get(f"{BASE_URL}/api/questions", timeout=10)
        elapsed = time.time() - start
        
        with lock:
            results['response_times'].append(elapsed)
        
        if response.status_code != 200:
            with lock:
                results['failed'] += 1
            return
        
        questions = response.json()
        
        # 3. Отправка ответов на каждый вопрос
        for i, question in enumerate(questions):
            time.sleep(0.5)  # Пауза между ответами (реалистично)
            
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/check-answer",
                json={
                    'question_id': question['id'],
                    'answer': 'тестовый ответ'
                },
                timeout=10
            )
            elapsed = time.time() - start
            
            with lock:
                results['response_times'].append(elapsed)
            
            if response.status_code != 200:
                with lock:
                    results['failed'] += 1
                return
        
        # 4. Получение результата
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/result",
            json={'answers': {}},
            timeout=10
        )
        elapsed = time.time() - start
        
        with lock:
            results['response_times'].append(elapsed)
        
        if response.status_code == 200:
            with lock:
                results['success'] += 1
        else:
            with lock:
                results['failed'] += 1
                
    except Exception as e:
        print(f"Пользователь {user_id} ошибка: {e}")
        with lock:
            results['failed'] += 1

def run_load_test():
    """Запускает нагрузочный тест"""
    print("=" * 60)
    print("НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ QUIZ-APP")
    print("=" * 60)
    print(f"URL: {BASE_URL}")
    print(f"Количество пользователей: {NUM_USERS}")
    print(f"Длительность: {DURATION_SECONDS} секунд")
    print("=" * 60)
    print("\nЗапуск теста...\n")
    
    start_time = time.time()
    end_time = start_time + DURATION_SECONDS
    
    with ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
        user_count = 0
        while time.time() < end_time:
            executor.submit(simulate_user, user_count)
            user_count += 1
            time.sleep(0.1)  # Небольшая задержка между запуском пользователей
    
    # Ждем завершения всех потоков
    print("\nОжидание завершения всех запросов...\n")
    
    # Вывод результатов
    print("=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Успешных сессий: {results['success']}")
    print(f"Неудачных сессий: {results['failed']}")
    print(f"Всего запросов: {len(results['response_times'])}")
    
    if results['response_times']:
        print(f"\nВремя отклика:")
        print(f"  Среднее: {statistics.mean(results['response_times']):.3f} сек")
        print(f"  Медиана: {statistics.median(results['response_times']):.3f} сек")
        print(f"  Минимум: {min(results['response_times']):.3f} сек")
        print(f"  Максимум: {max(results['response_times']):.3f} сек")
    
    success_rate = (results['success'] / (results['success'] + results['failed']) * 100) if (results['success'] + results['failed']) > 0 else 0
    print(f"\nУспешность: {success_rate:.1f}%")
    
    print("=" * 60)
    
    # Оценка
    if success_rate >= 95:
        print("✅ ОТЛИЧНО! Система справляется с нагрузкой")
    elif success_rate >= 80:
        print("⚠️ ПРИЕМЛЕМО. Есть проблемы при высокой нагрузке")
    else:
        print("❌ ПЛОХО. Система не справляется с нагрузкой")

if __name__ == "__main__":
    print("\n⚠️ ВАЖНО: Убедитесь, что приложение запущено!")
    print(f"Проверьте: {BASE_URL}\n")
    
    input("Нажмите Enter для начала теста...")
    
    try:
        run_load_test()
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
