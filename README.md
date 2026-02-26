# 🤖 Notion RAG 시스템

Notion 페이지를 ChromaDB에 인덱싱하고, 자연어 질문으로 검색 및 수정할 수 있는 RAG(Retrieval-Augmented Generation) 시스템입니다.

> **🚧 현재 v2.0 고도화 작업 진행 중** - 증분 동기화, 병렬 임베딩, 리랭킹 등 엔터프라이즈 기능 추가 중입니다.

## ✨ 주요 기능

### 현재 버전 (v1.0)
- 📖 **Notion 페이지 자동 인덱싱** - 워크스페이스의 모든 페이지를 벡터 DB에 저장
- 🔄 **페이지 업데이트 및 삭제** - 변경된 내용 자동 반영
- ✍️ **페이지 내용 수정 및 생성** - API를 통한 Notion 페이지 직접 수정
- 🔍 **벡터 검색** - 관련 문서를 의미 기반으로 검색
- 🌐 **DuckDuckGo 웹 검색 통합** - 실시간 웹 정보 활용
- 🤖 **Ollama 기반 AI 답변** - 로컬 LLM을 활용한 답변 생성
- 💾 **ChromaDB 로컬 저장소** - 벡터 임베딩 영구 저장
- 🌐 **REST API 및 웹 UI** - 다양한 인터페이스 제공
- 🔧 **Open WebUI 통합** - 채팅 UI로 사용 가능
- ⏰ **자동 인덱싱 스케줄러** - 매일 자동으로 페이지 업데이트

### 🚀 v2.0 고도화 (진행 중 - 30% 완료)

#### ✅ 완료된 기능
- **Python 패키지 구조 표준화** - `src/` 중심의 모듈화된 아키텍처
- **ConfigManager** - 환경 변수 중앙 관리 및 검증
- **IncrementalSyncEngine** - 변경된 페이지만 선별적으로 인덱싱 (시간 절약)
- **EmbeddingProcessor** - asyncio 기반 병렬 임베딩 (8배 속도 향상)
- **VectorStoreManager** - 개선된 ChromaDB 관리

#### 🚧 개발 예정
- **Reranker** - bge-reranker-v2-m3 기반 검색 결과 재정렬 (정확도 향상)
- **ContextRouter** - LLM 기반 질문 의도 분류 및 정보 소스 라우팅
- **QAEngine** - 통합 질의응답 파이프라인
- **확장된 API** - 증분 동기화 수동 트리거, 상태 조회 엔드포인트
- **자동 스케줄러 통합** - Incremental Sync 자동 실행

## 📁 프로젝트 구조

```
Notion_LLM/
├── src/                    # 소스 코드
│   ├── core/              # 핵심 로직
│   │   ├── config.py      # 환경변수 관리 및 검증
│   │   ├── notion_extractor.py  # Notion API 연동
│   │   └── scheduler.py   # 자동 업데이트 스케줄러
│   ├── api/               # API 서버
│   │   └── server.py      # FastAPI REST API
│   └── utils/             # 유틸리티
│       └── notion_rag_tool.py  # Open WebUI Function
├── scripts/               # 실행 스크립트
│   ├── start.bat          # 서버 시작
│   ├── stop.bat           # 서버 중지
│   ├── restart.bat        # 서버 재시작
│   └── logs.bat           # 스케줄러 로그 확인
├── main.py               # CLI 진입점
├── api.py                # API 서버 진입점
├── config.py             # 설정 진입점
├── scheduler.py          # 스케줄러 진입점
├── index.html            # 웹 UI
├── requirements.txt      # Python 의존성
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🛠 환경 요구사항

- **Docker** & **Docker Compose**
- **Ollama**: 로컬 또는 원격 서버에 설치 및 실행 중
- **Notion**: Integration Token 및 페이지 접근 권한
- **(선택) Open WebUI**: 채팅 UI로 사용

## 📦 설치 방법

### 1. 저장소 클론

```bash
git clone https://github.com/Dawoon7777/Notion_LLM.git
cd Notion_LLM
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PAGE_ID=abc123def456
OLLAMA_BASE_URL=http://192.168.50.192:11434
```

### 3. Notion API 설정

#### Integration 생성

1. https://www.notion.so/my-integrations 접속
2. `+ New integration` 클릭
3. Name 입력 및 Capabilities 설정:
   - ✅ Read content
   - ✅ Update content
   - ✅ Insert content
4. Integration Token 복사 → `.env`의 `NOTION_TOKEN`에 입력

#### 페이지 연결

1. Notion 페이지에서 `⋯` (더보기) 클릭
2. `Connections` 선택
3. 생성한 Integration 추가

#### Page ID 확인

URL에서 추출:
```
https://www.notion.so/My-Page-abc123def456?v=...
                           ^^^^^^^^^^^^^^^^
                           이 부분이 Page ID
```

## 🚀 사용 방법

### 방법 1: API 서버 + 웹 UI (권장)

**1. 서버 시작**
```bash
# Windows
scripts\start.bat

# Linux/Mac
docker-compose up -d
```

**2. 웹 브라우저 접속**
- 웹 UI: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

**3. 서버 관리**
```bash
# 중지
scripts\stop.bat

# 재시작
scripts\restart.bat

# 스케줄러 로그 확인
scripts\logs.bat
```

### 방법 2: Open WebUI 통합 (추천)

**1. Open WebUI 설치 및 실행**
```bash
docker run -d -p 3000:8080 \
  -e OLLAMA_BASE_URL=http://192.168.50.192:11434 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

**2. Notion RAG API 시작**
```bash
docker-compose up -d
```

**3. Open WebUI에서 Function 등록**
1. http://localhost:3000 접속
2. Settings (⚙️) → Admin Panel → Functions
3. "+" 버튼 클릭 → "Create New Function"
4. `src/utils/notion_rag_tool.py` 파일 내용 복사 & 붙여넣기
5. Save 후 활성화

**4. 채팅에서 사용**
```
Notion에서 "프로젝트 목표"를 검색해줘
```

### 방법 3: CLI 사용

```bash
# 페이지 인덱싱
docker-compose run --rm api python main.py index <page_id>

# 페이지 업데이트
docker-compose run --rm api python main.py update <page_id>

# 페이지 삭제
docker-compose run --rm api python main.py delete <page_id>

# 질문하기
docker-compose run --rm api python main.py query "질문 내용"
```

## 📋 API 엔드포인트

### 읽기 (Read)

#### `GET /pages`
워크스페이스의 모든 페이지 목록 조회

**응답:**
```json
{
  "status": "success",
  "count": 10,
  "pages": [
    {"id": "xxx", "title": "페이지 제목"}
  ]
}
```

#### `POST /query`
자연어 질문으로 검색 및 답변 생성

**요청:**
```json
{
  "question": "프로젝트의 주요 목표는?",
  "session_id": "optional-session-id",
  "n_results": 3,
  "use_web_search": true
}
```

**응답:**
```json
{
  "answer": "AI가 생성한 답변...",
  "sources": [
    {"title": "📄 관련 문서", "page_id": "xxx"}
  ],
  "session_id": "session-id"
}
```

### 쓰기 (Write)

#### `POST /append`
페이지 끝에 내용 추가

**요청:**
```json
{
  "page_id": "abc123def456",
  "content": "추가할 내용"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "페이지에 내용이 추가되었습니다",
  "page_id": "abc123def456"
}
```

#### `POST /create-page`
새 페이지 생성

**요청:**
```json
{
  "parent_page_id": "abc123def456",
  "title": "새 페이지 제목",
  "content": "페이지 내용"
}
```

**응답:**
```json
{
  "status": "success",
  "message": "새 페이지가 생성되었습니다",
  "page_id": "new-page-id",
  "title": "새 페이지 제목"
}
```

### 관리 (Management)

#### `POST /index`
특정 페이지 인덱싱

**요청:**
```json
{
  "page_ids": ["page-id-1", "page-id-2"]
}
```

#### `POST /index-all`
워크스페이스의 모든 페이지 인덱싱

#### `POST /update`
페이지 업데이트 (재인덱싱)

**요청:**
```json
{
  "page_ids": ["page-id-1", "page-id-2"]
}
```

#### `POST /delete`
벡터 DB에서 페이지 삭제

**요청:**
```json
{
  "page_ids": ["page-id-1", "page-id-2"]
}
```

#### `GET /health`
서버 상태 확인

**응답:**
```json
{
  "status": "healthy",
  "ollama": "http://192.168.50.192:11434",
  "notion": "connected",
  "active_sessions": 5
}
```

## 🔧 환경변수

### 필수 변수
| 변수 | 설명 | 예시 |
|------|------|------|
| `NOTION_TOKEN` | Notion Integration Token | `secret_xxxxx` |
| `OLLAMA_BASE_URL` | Ollama 서버 URL | `http://192.168.50.192:11434` |

### 선택 변수
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `NOTION_PAGE_ID` | 기본 페이지 ID | - |
| `OLLAMA_NUM_CTX` | LLM 컨텍스트 길이 | `32768` |
| `OLLAMA_KEEP_ALIVE` | 모델 상주 설정 | `-1` (항상 유지) |
| `OLLAMA_TIMEOUT` | API 타임아웃 (초) | `120` |
| `OLLAMA_MAX_RETRIES` | 최대 재시도 횟수 | `3` |
| `EMBEDDING_CONCURRENCY` | 동시 임베딩 요청 수 | `8` |
| `EMBEDDING_MAX_RETRIES` | 임베딩 재시도 횟수 | `3` |
| `SEARCH_TOP_K` | 초기 검색 결과 수 | `20` |
| `RERANK_TOP_N` | 리랭킹 후 최종 결과 수 | `5` |
| `SYNC_INTERVAL_MINUTES` | 자동 동기화 주기 (분) | `60` |
| `SYNC_STATE_PATH` | 동기화 상태 파일 경로 | `./sync_state.json` |

## ⏰ 자동 스케줄러

스케줄러는 백그라운드에서 자동으로 실행되며, 매일 오전 3시에 모든 페이지를 업데이트합니다.

### 스케줄 변경

`scheduler.py` 파일 수정:

```python
# 매일 오전 3시 (기본)
schedule.every().day.at("03:00").do(auto_update_pages)

# 매 시간마다
schedule.every().hour.do(auto_update_pages)

# 30분마다
schedule.every(30).minutes.do(auto_update_pages)
```

### 로그 확인

```bash
# Windows
scripts\logs.bat

# Linux/Mac
docker-compose logs -f scheduler
```

## 🏗 아키텍처

```
사용자 질문
    ↓
VectorStoreManager (벡터 검색)
    ↓
ChromaDB → 관련 Notion 문서 추출
    ↓
WebSearcher (DuckDuckGo) → 웹 검색 결과
    ↓
OllamaQA (AI 답변 생성)
    ↓
통합 답변 반환
```

## 🔧 커스터마이징

### 청크 크기 조절

`main.py`의 `VectorStoreManager._split_into_chunks()`:

```python
def _split_into_chunks(self, text: str, chunk_size: int = 1000):  # 기본 500
```

### 검색 결과 개수 변경

```python
relevant_docs = vector_store.search(question, n_results=5)  # 기본 3
```

### Ollama 모델 변경

`.env` 파일 또는 코드에서:

```python
embeddings = OllamaEmbeddings(OLLAMA_BASE_URL, model="llama3.1")
qa = OllamaQA(OLLAMA_BASE_URL, model="llama3.1")
```

## 🐛 문제 해결

### "임베딩 생성 오류"

- Ollama 서버 실행 확인: `curl http://192.168.50.192:11434/api/tags`
- 모델 설치 확인: `ollama list`
- 필요시 모델 다운로드: `ollama pull llama3.3:70b`

### "관련 문서를 찾을 수 없습니다"

- 먼저 페이지를 인덱싱했는지 확인
- `chroma_db/` 디렉토리가 존재하는지 확인
- API 문서에서 `/index-all` 실행

### "페이지 읽기 오류"

- Notion Integration이 페이지에 연결되어 있는지 확인
- Token과 Page ID가 올바른지 확인
- Integration에 필요한 권한이 있는지 확인

### "웹 검색 실패"

- `duckduckgo-search` 패키지 설치 확인
- 네트워크 연결 확인
- `use_web_search: false`로 비활성화 가능

## 📝 사용 예시

### 1. 페이지 인덱싱

```bash
curl -X POST http://localhost:8000/index-all
```

### 2. 질문하기

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "프로젝트의 주요 목표는?",
    "use_web_search": true
  }'
```

### 3. 페이지에 내용 추가

```bash
curl -X POST http://localhost:8000/append \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "abc123def456",
    "content": "🤖 AI가 추가한 내용입니다."
  }'
```

### 4. 새 페이지 생성

```bash
curl -X POST http://localhost:8000/create-page \
  -H "Content-Type: application/json" \
  -d '{
    "parent_page_id": "abc123def456",
    "title": "회의록 2026-02-13",
    "content": "오늘 회의 내용..."
  }'
```

## 📚 기술 스택

- **Backend**: Python 3.11, FastAPI
- **Vector DB**: ChromaDB
- **Embeddings**: Ollama (bge-m3)
- **LLM**: Ollama (llama3.3:70b)
- **Web Search**: DuckDuckGo
- **Notion API**: notion-client
- **Scheduler**: schedule
- **Frontend**: HTML/CSS/JavaScript

## 📝 라이선스

MIT License

---

**Made with ❤️ using Ollama, ChromaDB & Notion API**
