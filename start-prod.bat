@echo off
echo Starting BNS AI in production mode with Docker...
echo.
docker-compose up -d --build
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8080
echo.
docker-compose logs -f
