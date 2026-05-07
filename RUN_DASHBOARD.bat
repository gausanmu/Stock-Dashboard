@echo off
title NSE Quant Engine - Local Launcher
color 0A

echo ============================================
echo   NSE Quant Engine - Starting Locally
echo ============================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node 18+ and add to PATH.
    pause
    exit /b 1
)

:: Get the directory this script lives in
set "PROJECT_DIR=%~dp0"

:: ── Backend Setup ──────────────────────────────────────────
echo [1/4] Installing backend dependencies...
cd /d "%PROJECT_DIR%backend"
if not exist "venv" (
    echo       Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: Use the lightweight local requirements (avoids C-extension issues on Windows)
pip install -q -r requirements-local.txt 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Some packages failed. Trying full requirements...
    pip install -q -r requirements.txt 2>nul
)

:: ── Frontend Setup ─────────────────────────────────────────
echo [2/4] Installing frontend dependencies...
cd /d "%PROJECT_DIR%frontend"
if not exist "node_modules" (
    call npm install --legacy-peer-deps
) else (
    echo       node_modules exists, skipping install.
)

:: ── Start Backend ──────────────────────────────────────────
echo [3/4] Starting backend on http://localhost:8000 ...
cd /d "%PROJECT_DIR%backend"
start "Backend - Uvicorn" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"

:: Give backend a moment to boot
timeout /t 3 /nobreak >nul

:: ── Start Frontend ─────────────────────────────────────────
echo [4/4] Starting frontend on http://localhost:3000 ...
cd /d "%PROJECT_DIR%frontend"
start "Frontend - React" cmd /k "set BROWSER=none&& npm start"

:: Wait for frontend dev server to be ready
timeout /t 8 /nobreak >nul

:: ── Open Browser ───────────────────────────────────────────
echo.
echo ============================================
echo   Dashboard: http://localhost:3000
echo   API Docs:  http://localhost:8000/docs
echo ============================================
echo.
echo Close both terminal windows to stop.
echo.
start http://localhost:3000
pause
