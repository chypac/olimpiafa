@echo off
echo Starting Frontend...
cd frontend
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
npm start
