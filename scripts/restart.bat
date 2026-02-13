@echo off
chcp 65001 > nul
echo ========================================
echo 🔄 Notion RAG 시스템 재시작
echo ========================================
echo.

cd /d "%~dp0"

echo 📦 Docker 컨테이너 재시작 중...
docker-compose restart

if %errorlevel% neq 0 (
    echo ❌ 재시작 실패
    pause
    exit /b 1
)

echo.
echo ✅ 재시작 완료!
echo 📍 API 서버: http://localhost:8000
echo ========================================
pause
