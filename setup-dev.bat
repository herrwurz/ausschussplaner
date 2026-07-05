@echo off
REM AusschussPlaner Development Setup Script

echo ====================================
echo AusschussPlaner Development Setup
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo Step 1/4: Creating Python Virtual Environment...
if exist ".venv" (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)

echo.
echo Step 2/4: Installing Backend Dependencies...
call .venv\Scripts\activate.bat
pip install -e .
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies!
    pause
    exit /b 1
)

pip install -e ".[dev]"
if errorlevel 1 (
    echo ERROR: Failed to install dev dependencies!
    pause
    exit /b 1
)
echo Backend dependencies installed

echo.
echo Step 3/4: Installing Frontend Dependencies...
if exist "frontend\node_modules" (
    echo node_modules already exists, skipping npm install...
) else (
    cd frontend
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies!
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo Frontend dependencies installed
)

echo.
echo Step 4/4: Running Database Migrations...
REM Alembic ist (noch) nicht konfiguriert - Migrationen laufen als Skripte (idempotent)
python migrate_verfuegbarkeit_periode.py
if errorlevel 1 (
    echo WARNING: Database migration encountered an issue
)

REM Admin-Login sicherstellen (legt admin@ausschussplaner.local an bzw. setzt Passwort zurueck)
python create_admin.py
if errorlevel 1 (
    echo WARNING: Admin-Anlage fehlgeschlagen
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Next steps:
echo 1. Run 'start-dev.bat' to start development servers
echo 2. Or run 'start-docker.bat' to use Docker
echo.
echo Services will be available at:
echo - Frontend:  http://localhost:5173
echo - Admin UI:  http://localhost:5173/admin/login (admin@ausschussplaner.local / admin123)
echo - Backend:   http://localhost:8000
echo - API Docs:  http://localhost:8000/docs
echo.
pause
