import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ChevronLeft, 
  ChevronRight, 
  Trophy,
  Clock,
  User,
  Award,
  CheckCircle
} from 'lucide-react';
import './App.css';
import backgroundImage from './background.jpg';

const API_URL = '/api';

function App() {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState({});
  const [questionTimers, setQuestionTimers] = useState({}); // Индивидуальные таймеры для каждого вопроса
  const [loading, setLoading] = useState(true);
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState(null);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [userId, setUserId] = useState('');
  const [showIdForm, setShowIdForm] = useState(true);

  // Функция сохранения прогресса в localStorage и на сервере
  const saveProgress = async () => {
    const progress = {
      userId,
      currentIndex,
      userAnswers,
      questionTimers,
      timestamp: Date.now()
    };
    localStorage.setItem('quizProgress', JSON.stringify(progress));
    
    // Также сохраняем на сервере (без await чтобы не блокировать UI)
    if (userId) {
      try {
        await axios.post(`${API_URL}/save-progress`, {
          user_id: userId,
          current_index: currentIndex,
          user_answers: userAnswers,
          question_timers: questionTimers
        });
      } catch (error) {
        console.error('Ошибка сохранения прогресса на сервере:', error);
      }
    }
  };

  // Функция восстановления прогресса из localStorage
  const restoreProgress = () => {
    const saved = localStorage.getItem('quizProgress');
    if (saved) {
      try {
        const progress = JSON.parse(saved);
        // Проверяем что прогресс не старше 24 часов
        const hoursPassed = (Date.now() - progress.timestamp) / (1000 * 60 * 60);
        if (hoursPassed < 24 && progress.userId) {
          setUserId(progress.userId);
          setCurrentIndex(progress.currentIndex || 0);
          setUserAnswers(progress.userAnswers || {});
          setQuestionTimers(progress.questionTimers || {});
          setShowIdForm(false);
          return true;
        }
      } catch (e) {
        console.error('Ошибка восстановления прогресса:', e);
      }
    }
    return false;
  };

  // Функция очистки прогресса
  const clearProgress = () => {
    localStorage.removeItem('quizProgress');
  };

  // Устанавливаем фоновое изображение и восстанавливаем прогресс
  useEffect(() => {
    document.body.style.backgroundImage = `url(${backgroundImage})`;
    // Пытаемся восстановить прогресс при загрузке
    restoreProgress();
    return () => {
      document.body.style.backgroundImage = '';
    };
  }, []);

  // Загрузка вопросов (только после ввода ID)
  useEffect(() => {
    if (!showIdForm) {
      axios.get(`${API_URL}/questions`)
        .then(response => {
          setQuestions(response.data);
          setLoading(false);
          // Инициализируем таймеры для всех вопросов
          const timers = {};
          response.data.forEach(q => {
            timers[q.id] = q.time_limit;
          });
          setQuestionTimers(timers);
        })
        .catch(error => {
          console.error('Ошибка загрузки вопросов:', error);
          setLoading(false);
        });
    }
  }, [showIdForm]);

  // Таймер для текущего вопроса
  useEffect(() => {
    if (questions.length === 0 || showResult) return;
    
    const currentQuestion = questions[currentIndex];
    const currentTime = questionTimers[currentQuestion.id];
    
    if (currentTime > 0) {
      const timer = setTimeout(() => {
        setQuestionTimers(prev => ({
          ...prev,
          [currentQuestion.id]: currentTime - 1
        }));
      }, 1000);
      return () => clearTimeout(timer);
    } else if (currentTime === 0) {
      handleAutoSubmit();
    }
  }, [questionTimers, currentIndex, questions, showResult]);

  // Загрузка сохраненного ответа при смене вопроса
  useEffect(() => {
    if (questions.length > 0) {
      const currentQuestion = questions[currentIndex];
      setCurrentAnswer(userAnswers[currentQuestion.id] || '');
    }
  }, [currentIndex, questions, userAnswers]);

  // Автосохранение при изменении ответов или таймеров
  useEffect(() => {
    if (!showIdForm && questions.length > 0) {
      saveProgress();
    }
  }, [userAnswers, questionTimers, currentIndex]);

  const handleAutoSubmit = () => {
    // Автоматическая отправка при истечении времени
    const currentQuestion = questions[currentIndex];
    setUserAnswers(prev => ({
      ...prev,
      [currentQuestion.id]: currentAnswer
    }));
    
    // Переход на следующий вопрос
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      // Если это последний вопрос - показываем результат
      calculateResult();
    }
  };

  // Автосохранение ответа при изменении
  const saveCurrentAnswer = () => {
    const currentQuestion = questions[currentIndex];
    setUserAnswers(prev => ({
      ...prev,
      [currentQuestion.id]: currentAnswer
    }));
    // Сохраняем прогресс в localStorage
    saveProgress();
  };

  const showHint = async () => {
    const currentQuestion = questions[currentIndex];
    
    try {
      const response = await axios.get(`${API_URL}/hint/${currentQuestion.id}`);
      alert(`💡 Подсказка: ${response.data.hint}`);
    } catch (error) {
      console.error('Ошибка получения подсказки:', error);
    }
  };

  const goToPrev = () => {
    if (currentIndex > 0) {
      saveCurrentAnswer(); // Сохраняем ответ перед переходом
      setCurrentIndex(currentIndex - 1);
      saveProgress(); // Сохраняем прогресс
    }
  };

  const goToNext = () => {
    if (currentIndex < questions.length - 1) {
      saveCurrentAnswer(); // Сохраняем ответ перед переходом
      setCurrentIndex(currentIndex + 1);
      saveProgress(); // Сохраняем прогресс
    }
  };

  const calculateResult = async () => {
    // Сохраняем последний ответ
    const currentQuestion = questions[currentIndex];
    const finalAnswers = {
      ...userAnswers,
      [currentQuestion.id]: currentAnswer
    };
    
    try {
      const response = await axios.post(`${API_URL}/result`, {
        answers: finalAnswers,
        user_id: userId
      });
      setResult(response.data);
      setShowResult(true);
      // Очищаем прогресс после завершения теста
      clearProgress();
    } catch (error) {
      console.error('Ошибка расчета результата:', error);
    }
  };

  const handleIdSubmit = async (e) => {
    e.preventDefault();
    const trimmedId = userId.trim();
    
    if (!trimmedId) {
      alert('Пожалуйста, введите ваш ID');
      return;
    }

    try {
      // Проверяем ID на сервере
      const response = await axios.post(`${API_URL}/validate-id`, {
        user_id: trimmedId
      });

      if (response.data.valid) {
        setShowIdForm(false);
        setLoading(true);
        // Сохраняем ID в прогресс
        saveProgress();
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Ошибка проверки ID:', error);
      alert('Ошибка проверки ID. Попробуйте еще раз.');
    }
  };

  // Форма ввода ID
  if (showIdForm) {
    return (
      <div className="id-form-container">
        <div className="id-form-card">
          <User className="id-icon" size={64} />
          <h1>IT Спринт</h1>
          <p className="id-subtitle">Добро пожаловать! Введите ваш ID для начала</p>
          
          <div className="warning-box">
            <h3>⚠️ ВНИМАНИЕ!</h3>
            <p><strong>У вас только ОДНА попытка!</strong></p>
            <p>После завершения теста ваш ID будет заблокирован.</p>
            <p>Вы не сможете пройти тест повторно.</p>
          </div>
          
          <form onSubmit={handleIdSubmit}>
            <input
              type="text"
              className="id-input"
              placeholder="Введите ваш ID (например: 2533)"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              autoFocus
            />
            <button type="submit" className="btn btn-primary btn-large">
              Начать тест
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Загрузка вопросов...</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="error">
        <p>Ошибка: вопросы не найдены</p>
      </div>
    );
  }

  if (showResult && result) {
    return (
      <div className="result-container">
        <div className="result-card">
          <Trophy className="result-icon" size={64} />
          <h1>Ваши результаты</h1>
          <div className="result-stats">
            <div className="stat">
              <Award size={32} />
              <div>
                <div className="stat-value">{result.score} / {result.max_score}</div>
                <div className="stat-label">Баллы</div>
              </div>
            </div>
            <div className="stat">
              <CheckCircle size={32} />
              <div>
                <div className="stat-value">{result.percent}%</div>
                <div className="stat-label">Процент</div>
              </div>
            </div>
          </div>
          <p className="result-message">Спасибо за участие в олимпиаде IT спринт!</p>
        </div>
      </div>
    );
  }

  const currentQuestion = questions[currentIndex];
  const currentTime = questionTimers[currentQuestion.id] || 0;
  const minutes = Math.floor(currentTime / 60);
  const seconds = currentTime % 60;

  return (
    <div className="app">
      <div className="quiz-container">
        {/* Header */}
        <div className="quiz-header">
          <div className={`timer ${currentTime < 30 ? 'timer-warning' : ''}`}>
            <Clock size={20} />
            <span>{String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}</span>
          </div>
        </div>

        {/* Progress */}
        <div className="progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
            ></div>
          </div>
          <div className="progress-text">
            Вопрос {currentIndex + 1} из {questions.length}
          </div>
        </div>

        {/* Question */}
        <div className="question-card">
          <h2 className="question-title">{currentQuestion.title}</h2>
          <div className="question-text">
            {currentQuestion.text.split('\n').map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          <input
            type="text"
            className="answer-input"
            placeholder="Введите ваш ответ..."
            value={currentAnswer}
            onChange={(e) => {
              setCurrentAnswer(e.target.value);
              // Автосохранение при вводе
              const currentQuestion = questions[currentIndex];
              setUserAnswers(prev => ({
                ...prev,
                [currentQuestion.id]: e.target.value
              }));
            }}
          />

          {/* Buttons */}
          {currentIndex === questions.length - 1 && (
            <button 
              className="btn btn-success"
              onClick={calculateResult}
            >
              <Trophy size={18} />
              Завершить тест
            </button>
          )}
        </div>

        {/* Navigation */}
        <div className="navigation">
          <button 
            className="nav-btn"
            onClick={goToPrev}
            disabled={currentIndex === 0}
          >
            <ChevronLeft size={24} />
          </button>
          <button 
            className="nav-btn"
            onClick={goToNext}
            disabled={currentIndex === questions.length - 1}
          >
            <ChevronRight size={24} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
