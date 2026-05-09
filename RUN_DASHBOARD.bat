@echo off
title NSE Quant Engine v2
color 0A

echo.
echo  ============================================
echo   NSE Quant Engine v2 - Local Launcher
echo  ============================================
echo.

:: Use short variable to avoid quoting hell with spaces in path
set "P=%~dp0"

:: ── Kill any old processes on our ports ──────────────────────
echo [0/4] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000.*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: ── Check Python ─────────────────────────────────────────────
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python launcher 'py' not found.
    pause
    exit /b 1
)
echo       Python: OK

:: ── Check Node ───────────────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found.
    pause
    exit /b 1
)
echo       Node:   OK

:: ── Backend Setup ────────────────────────────────────────────
echo.
echo [1/4] Setting up backend...
pushd "%P%backend"

if not exist "venv\Scripts\activate.bat" (
    echo       Creating virtual environment...
    py -3 -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        popd
        pause
        exit /b 1
    )
    echo       venv created.
)

call "venv\Scripts\activate.bat"
echo       venv activated.

echo       Installing Python dependencies...
pip install -q --upgrade pip >nul 2>&1
if exist "requirements-local.txt" (
    pip install -q -r "requirements-local.txt" 2>nul
) else if exist "requirements.txt" (
    pip install -q -r "requirements.txt" 2>nul
)
echo       Dependencies ready.
popd

:: ── Dashboard Setup ──────────────────────────────────────────
echo.
echo [2/4] Setting up dashboard...
pushd "%P%dashboard"

if not exist "node_modules" (
    echo       Installing npm packages...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        popd
        pause
        exit /b 1
    )
) else (
    echo       node_modules exists, skipping.
)
popd

:: ── Start Backend ────────────────────────────────────────────
echo.
echo [3/4] Starting backend on http://localhost:8000 ...
start "Backend" /D "%P%backend" cmd /k "call venv\Scripts\activate.bat && py -3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"

echo       Waiting for backend...
timeout /t 5 /nobreak >nul

:: ── Start Dashboard ──────────────────────────────────────────
echo.
echo [4/4] Starting dashboard on http://localhost:3000 ...
start "Dashboard" /D "%P%dashboard" cmd /k "npm run dev"

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
