@echo off
chcp 65001 > nul
echo ========================================
echo 🚀 Notion RAG 시스템 시작
echo ========================================
echo.

cd /d "%~dp0"

echo 📦 Docker 컨테이너 시작 중...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ❌ Docker 시작 실패
    pause
    exit /b 1
)

echo.
echo ✅ API 서버 시작 완료!
echo.
echo 🌐 웹 페이지를 여는 중...
timeout /t 2 /nobreak > nul

start "" "index.html"

echo.
echo ========================================
echo ✨ 실행 완료!
echo ========================================
echo.
echo 🌐 웹 UI: file:///%CD%/index.html
echo 📍 API 서버: http://localhost:8000
echo 📍 API 문서: http://localhost:8000/docs
echo 💚 헬스 체크: http://localhost:8000/health
echo.
echo 종료하려면 stop.bat 실행
echo ========================================
echo.
echo 브라우저에서 접속하세요:
echo http://localhost:8000/docs
echo.
pause
