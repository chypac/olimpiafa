@echo off
echo ========================================
echo   Сборка и запуск единого приложения
echo ========================================
echo.

echo [1/3] Сборка React приложения...
cd frontend
if not exist node_modules (
    echo Установка зависимостей...
    call npm install
)
call npm run build
echo.

echo [2/3] Подготовка backend...
cd ..\backend
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo.

echo [3/3] Запуск сервера...
echo.
echo ========================================
echo   Приложение доступно на:
echo   http://localhost:5000
echo ========================================
echo.
python app_unified.py
