@echo off
chcp 65001 > nul
echo ========================================
echo 📊 Notion RAG 스케줄러 로그 확인
echo ========================================
echo.

cd /d "%~dp0"

docker-compose logs -f scheduler

pause
