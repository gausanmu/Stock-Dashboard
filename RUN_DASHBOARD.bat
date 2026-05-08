@echo off
setlocal EnableDelayedExpansion
title NSE Quant Engine v2
color 0A

echo.
echo  ============================================
echo   NSE Quant Engine v2 - Local Launcher
echo  ============================================
echo.

set "PROJECT_DIR=%~dp0"

:: ── Kill any old processes on our ports ──────────────────────
echo [0/4] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: ── Check Python ─────────────────────────────────────────────
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python launcher 'py' not found.
    echo         Install Python 3.10+ from python.org
    pause
    exit /b 1
)
echo       Python: OK

:: ── Check Node ───────────────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node 18+ from nodejs.org
    pause
    exit /b 1
)
echo       Node:   OK

:: ── Backend Setup ────────────────────────────────────────────
echo.
echo [1/4] Setting up backend...
cd /d "%PROJECT_DIR%backend"

:: Create venv if missing
if not exist "venv\Scripts\activate.bat" (
    echo       Creating virtual environment...
    py -3 -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv. Check Python installation.
        pause
        exit /b 1
    )
    echo       venv created successfully.
)

:: Activate venv
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate venv.
    pause
    exit /b 1
)
echo       venv activated.

:: Install/update dependencies
echo       Installing Python dependencies...
pip install -q --upgrade pip >nul 2>&1
if exist "requirements-local.txt" (
    pip install -q -r requirements-local.txt 2>nul
    if %errorlevel% neq 0 (
        echo       [WARN] requirements-local.txt failed, trying requirements.txt...
        pip install -q -r requirements.txt 2>nul
    )
) else if exist "requirements.txt" (
    pip install -q -r requirements.txt 2>nul
)
echo       Dependencies ready.

:: ── Dashboard Setup ──────────────────────────────────────────
echo.
echo [2/4] Setting up dashboard...
cd /d "%PROJECT_DIR%dashboard"

if not exist "node_modules" (
    echo       Installing npm packages (first run, may take a minute)...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
) else (
    echo       node_modules exists, skipping install.
)

:: ── Start Backend ────────────────────────────────────────────
echo.
echo [3/4] Starting backend on http://localhost:8000 ...
cd /d "%PROJECT_DIR%backend"
start "Backend - Uvicorn" cmd /k "title Backend - Uvicorn && call venv\Scripts\activate.bat && py -3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for backend to boot
echo       Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Verify backend is up
py -3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/admin/health')" >nul 2>&1
if %errorlevel% neq 0 (
    echo       [WARN] Backend may still be starting. Continuing anyway...
) else (
    echo       Backend is running!
)

:: ── Start Dashboard ──────────────────────────────────────────
echo.
echo [4/4] Starting dashboard on http://localhost:3000 ...
cd /d "%PROJECT_DIR%dashboard"
start "Dashboard - Vite" cmd /k "title Dashboard - Vite && npm run dev"

:: Wait for Vite
timeout /t 4 /nobreak >nul

:: ── Open Browser ─────────────────────────────────────────────
echo.
echo  ============================================
echo   Dashboard: http://localhost:3000
echo   API Docs:  http://localhost:8000/docs
echo   Evening:   http://localhost:3000/evening
echo  ============================================
echo.
echo  Close both terminal windows to stop.
echo.

start http://localhost:3000
pause
