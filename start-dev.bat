@echo off
setlocal
set "OLLAMA_STARTED=0"

echo Starting BNS AI in development mode...
echo.

echo 1. Checking Ollama...
set "OLLAMA_EXE="
where ollama >nul 2>&1 && set "OLLAMA_EXE=ollama"
if not defined OLLAMA_EXE if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"

if not defined OLLAMA_EXE (
    echo    [SKIP] Ollama not found. Install it from https://ollama.com to enable local AI.
) else (
    echo    Checking if Ollama server is already running on port 11434...
    netstat -an | findstr /r ":11434 .*LISTENING" >nul 2>&1
    if errorlevel 1 (
        echo    Starting Ollama server...
        start "BNS AI Ollama" cmd /c ""%OLLAMA_EXE%" serve"
        set "OLLAMA_STARTED=1"
        timeout /t 3 /nobreak >nul
    ) else (
        echo    Ollama server already running.
    )

    echo    Ensuring model llama3.2:3b is available...
    "%OLLAMA_EXE%" list 2>nul | findstr /c:"llama3.2:3b" >nul 2>&1
    if errorlevel 1 (
        echo    Pulling llama3.2:3b - this may take a few minutes on first run...
        "%OLLAMA_EXE%" pull llama3.2:3b
    ) else (
        echo    Model llama3.2:3b already available.
    )
)

echo.
echo 2. Starting Backend (FastAPI) on port 8000...
start "BNS AI Backend" cmd /c "cd /d "%~dp0backend" && set ENVIRONMENT=development && set SECRET_KEY=dev-secret-key-change-in-production && set DATABASE_URL=sqlite+aiosqlite:///./bnsai_test.db && set REDIS_URL=redis://localhost:6379/0 && set OTEL_ENABLED=false && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo 3. Starting Frontend (Vite) on port 5173...
start "BNS AI Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Ollama:   http://localhost:11434
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop all processes...
pause >nul

echo Stopping servers...
if "%OLLAMA_STARTED%"=="1" taskkill /f /im ollama.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
echo Done.
endlocal
