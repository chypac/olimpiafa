import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Download, Users, TrendingUp, Award } from 'lucide-react';
import './Results.css';

const API_URL = 'http://localhost:5000/api';

function Results() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/results/stats`);
      setStats(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Ошибка загрузки статистики:', error);
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    window.open(`${API_URL}/results/download`, '_blank');
  };

  const downloadJSON = async () => {
    try {
      const response = await axios.get(`${API_URL}/results/json`);
      const dataStr = JSON.stringify(response.data, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'quiz_results.json';
      link.click();
    } catch (error) {
      console.error('Ошибка скачивания JSON:', error);
    }
  };

  if (loading) {
    return (
      <div className="results-loading">
        <div className="spinner"></div>
        <p>Загрузка результатов...</p>
      </div>
    );
  }

  if (!stats || stats.total_users === 0) {
    return (
      <div className="results-empty">
        <p>Пока нет результатов</p>
      </div>
    );
  }

  return (
    <div className="results-container">
      <div className="results-header">
        <h1>Результаты тестирования</h1>
        <div className="download-buttons">
          <button className="btn btn-secondary" onClick={downloadCSV}>
            <Download size={18} />
            Скачать CSV
          </button>
          <button className="btn btn-secondary" onClick={downloadJSON}>
            <Download size={18} />
            Скачать JSON
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <Users size={32} />
          <div className="stat-content">
            <div className="stat-value">{stats.total_users}</div>
            <div className="stat-label">Всего пользователей</div>
          </div>
        </div>

        <div className="stat-card">
          <Award size={32} />
          <div className="stat-content">
            <div className="stat-value">{stats.average_score}</div>
            <div className="stat-label">Средний балл</div>
          </div>
        </div>

        <div className="stat-card">
          <TrendingUp size={32} />
          <div className="stat-content">
            <div className="stat-value">{stats.average_percent}%</div>
            <div className="stat-label">Средний процент</div>
          </div>
        </div>
      </div>

      <div className="results-table-container">
        <h2>Детальные результаты</h2>
        <table className="results-table">
          <thead>
            <tr>
              <th>Дата/Время</th>
              <th>ID Пользователя</th>
              <th>Баллы</th>
              <th>Процент</th>
              <th>Оценка</th>
            </tr>
          </thead>
          <tbody>
            {stats.results.map((result, index) => (
              <tr key={index}>
                <td>{result.timestamp}</td>
                <td>{result.user_id}</td>
                <td>{result.score} / {result.max_score}</td>
                <td>{result.percent}%</td>
                <td>
                  <span className={`grade-badge ${
                    result.percent >= 80 ? 'excellent' : 
                    result.percent >= 60 ? 'good' : 'try-again'
                  }`}>
                    {result.grade}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Results;
