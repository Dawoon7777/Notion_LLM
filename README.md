# 🤖 Notion RAG 시스템

Notion 페이지를 ChromaDB에 인덱싱하고, 자연어 질문으로 검색 및 수정할 수 있는 RAG 시스템입니다.

## 📁 프로젝트 구조

```
.
├── src/
│   ├── core/              # 핵심 로직
│   │   ├── config.py      # 환경변수 관리
│   │   ├── notion_extractor.py  # Notion 연동
│   │   └── scheduler.py   # 자동 업데이트
│   ├── api/               # API 서버
│   │   └── server.py      # FastAPI 서버
│   └── utils/             # 유틸리티
│       └── notion_rag_tool.py  # Open WebUI Function
├── scripts/               # 실행 스크립트
│   ├── start.bat
│   ├── stop.bat
│   ├── restart.bat
│   └── logs.bat
├── main.py               # CLI 진입점
├── api.py                # API 진입점
├── scheduler.py          # 스케줄러 진입점
├── index.html            # 웹 UI
├── requirements.txt      # Python 의존성
├── Dockerfile
├── docker-compose.yml
└── README.md

## ✨ 기능

- 📖 Notion 페이지 자동 인덱싱
- 🔄 페이지 업데이트 및 삭제
- ✍️ **페이지 내용 수정 및 생성**
- 🔍 벡터 검색을 통한 관련 문서 찾기
- 🌐 DuckDuckGo 웹 검색 통합
- 🤖 Ollama를 활용한 AI 답변 생성
- 💾 ChromaDB 로컬 벡터 저장소
- 🌐 REST API 및 웹 UI
- 🔧 Open WebUI 통합
- ⏰ 자동 인덱싱 스케줄러

## 🚀 빠른 시작

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 수정

# 2. 서버 시작 (Windows)
scripts\start.bat

# 3. 웹 UI 접속
http://localhost:8000
```

## 📋 API 엔드포인트

### 읽기
- `GET /pages` - 페이지 목록
- `POST /query` - 질문하기

### 쓰기
- `POST /append` - 페이지에 내용 추가
- `POST /create-page` - 새 페이지 생성

### 관리
- `POST /index` - 페이지 인덱싱
- `POST /update` - 페이지 업데이트
- `POST /delete` - 페이지 삭제

## 🔧 환경변수

```env
NOTION_TOKEN=secret_xxxxx
NOTION_PAGE_ID=xxxxx
OLLAMA_BASE_URL=http://192.168.50.192:11434
```

## 📝 라이선스

MIT License
