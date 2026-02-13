@echo off
chcp 65001 > nul
echo ========================================
echo 🛑 Notion RAG 시스템 종료
echo ========================================
echo.

cd /d "%~dp0"

echo 📦 Docker 컨테이너 종료 중...
docker-compose down

if %errorlevel% neq 0 (
    echo ❌ 종료 실패
    pause
    exit /b 1
)

echo.
echo ✅ 종료 완료!
echo ========================================
pause
