@echo off
REM AusschussPlaner Docker Startup Script

echo ====================================
echo AusschussPlaner Docker Setup
echo ====================================
echo.

REM Check if docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker not found!
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Stopping existing containers...
docker-compose down

echo.
echo Building and starting Docker containers...
docker-compose up --build

echo.
echo ====================================
echo Docker Services:
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Docs: http://localhost:8000/docs
echo - Admin UI: http://localhost:8000/admin/login (admin123)
echo ====================================
