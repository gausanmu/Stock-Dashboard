@echo off
title NSE Quant Engine v2 - Local Launcher
color 0A

echo ============================================
echo   NSE Quant Engine v2 - Starting Locally
echo ============================================
echo.

:: Get the directory this script lives in
set "PROJECT_DIR=%~dp0"

:: ── Check Python via py launcher ─────────────────────────────
where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python launcher (py) not found.
    echo         Install Python 3.10+ from python.org and ensure "py launcher" is checked.
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

:: ── Backend Setup ──────────────────────────────────────────
echo [1/4] Setting up backend...
cd /d "%PROJECT_DIR%backend"
if not exist "venv" (
    echo       Creating virtual environment...
    py -3 -m venv venv
)
call venv\Scripts\activate.bat

:: Install dependencies if needed
if not exist "venv\Lib\site-packages\fastapi" (
    echo       Installing Python dependencies...
    pip install -q -r requirements-local.txt 2>nul
    if %errorlevel% neq 0 (
        echo [WARN] Some packages failed. Trying full requirements...
        pip install -q -r requirements.txt 2>nul
    )
) else (
    echo       Dependencies already installed, skipping.
)

:: ── Dashboard Setup ─────────────────────────────────────────
echo [2/4] Setting up dashboard...
cd /d "%PROJECT_DIR%dashboard"
if not exist "node_modules" (
    echo       Installing npm dependencies (first run only)...
    call npm install
) else (
    echo       node_modules exists, skipping install.
)

:: ── Start Backend ──────────────────────────────────────────
echo [3/4] Starting backend on http://localhost:8000 ...
cd /d "%PROJECT_DIR%backend"
start "Backend - Uvicorn" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"

:: Give backend a moment to boot
timeout /t 4 /nobreak >nul

:: ── Start Dashboard ────────────────────────────────────────
echo [4/4] Starting dashboard on http://localhost:3000 ...
cd /d "%PROJECT_DIR%dashboard"
start "Dashboard - Vite" cmd /k "npm run dev"

:: Wait for Vite dev server to be ready
timeout /t 5 /nobreak >nul

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
