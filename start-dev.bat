@echo off
echo Starting BNS AI in development mode...
echo.

echo 1. Starting Backend (FastAPI) on port 8000...
start "BNS AI Backend" cmd /c "cd /d "%~dp0backend" && set ENVIRONMENT=development && set SECRET_KEY=dev-secret-key-change-in-production && set DATABASE_URL=sqlite+aiosqlite:///./bnsai_test.db && set REDIS_URL=redis://localhost:6379/0 && set OTEL_ENABLED=false && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo 2. Starting Frontend (Vite) on port 5173...
start "BNS AI Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop both servers...
pause >nul

echo Stopping servers...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
echo Done.
