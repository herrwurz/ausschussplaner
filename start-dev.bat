@echo off
REM AusschussPlaner Development Environment Startup Script
REM Starts Backend (FastAPI) and Frontend (Vite) in separate windows

echo ====================================
echo AusschussPlaner Development Setup
echo ====================================
echo.

REM Check if .venv exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\pip install -e .
    echo Then run: .venv\Scripts\pip install -e ".[dev]"
    pause
    exit /b 1
)

echo Starting Backend Server (FastAPI)...
start "AusschussPlaner Backend" cmd /k ^
    ".venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload"

timeout /t 2 /nobreak

echo Starting Frontend Server (Vite)...
start "AusschussPlaner Frontend" cmd /k ^
    "cd frontend && npm run dev"

echo.
echo ====================================
echo Services Starting:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:5173
echo - Test Dashboard: http://localhost:5173/test (MAIN)
echo - API Docs: http://localhost:8000/docs
echo - Admin UI: http://localhost:8000/admin/login (admin123)
echo ====================================
echo.
echo Press Ctrl+C in each window to stop services
pause
