# 🤖 Notion RAG 시스템

Notion 페이지를 ChromaDB에 인덱싱하고, 자연어 질문으로 검색할 수 있는 RAG(Retrieval-Augmented Generation) 시스템입니다.

## ✨ 기능

- 📖 여러 Notion 페이지 자동 인덱싱
- 🔄 페이지 업데이트 및 삭제 지원
- 🔍 벡터 검색을 통한 관련 문서 찾기
- 🤖 Ollama를 활용한 컨텍스트 기반 답변 생성
- 💾 ChromaDB를 사용한 로컬 벡터 저장소
- 🌐 REST API 및 CLI 인터페이스 제공

## 🛠 환경 요구사항

- **Docker** & **Docker Compose**
- **Ollama**: 로컬 또는 원격 서버에 설치 및 실행 중
- **Notion**: Integration Token 및 접근 권한

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
OLLAMA_BASE_URL=http://localhost:11434
```

## ⚙️ Notion API 설정

### 1. Integration 생성

1. https://www.notion.so/my-integrations 접속
2. `+ New integration` 클릭
3. Name 입력 및 Capabilities 설정 (Read content, Update content)
4. Integration Token 복사

### 2. 페이지 연결

1. Notion 페이지에서 `⋯` → `Connections` 클릭
2. 생성한 Integration 선택

### 3. Page ID 확인

URL에서 추출:
```
https://www.notion.so/My-Page-abc123def456?v=...
                           ^^^^^^^^^^^^^^^^
```

## 🚀 사용 방법

### Docker로 실행 (권장)

**1. 이미지 빌드**
```bash
docker-compose build
```

**2. 페이지 인덱싱**
```bash
# 단일 페이지
docker-compose run --rm notion-rag python main.py index <page_id>

# 여러 페이지
docker-compose run --rm notion-rag python main.py index <page_id1> <page_id2> <page_id3>

# .env의 기본 페이지
docker-compose run --rm notion-rag python main.py index
```

**3. 페이지 업데이트**
```bash
# Notion에서 수정한 페이지 재인덱싱
docker-compose run --rm notion-rag python main.py update <page_id>
```

**4. 페이지 삭제**
```bash
# 벡터 DB에서 페이지 제거
docker-compose run --rm notion-rag python main.py delete <page_id>
```

**5. 질문하기**
```bash
docker-compose run --rm notion-rag python main.py query "프로젝트의 주요 목표는?"
```

### 직접 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 인덱싱
python main.py index <page_id>

# 업데이트
python main.py update <page_id>

# 삭제
python main.py delete <page_id>

# 질문
python main.py query "질문 내용"
```

## 📋 사용 예시

### 1. 여러 페이지 인덱싱

```bash
docker-compose run --rm notion-rag python main.py index \
  abc123def456 \
  def789ghi012 \
  ghi345jkl678
```

출력:
```
🚀 Notion 페이지 인덱싱 시작

📖 페이지 abc123def456 처리 중...
✅ 페이지 '프로젝트 개요' 인덱싱 완료 (5 청크)
📖 페이지 def789ghi012 처리 중...
✅ 페이지 '기술 스택' 인덱싱 완료 (3 청크)

✅ 모든 페이지 인덱싱 완료!
```

### 2. 페이지 업데이트

```bash
docker-compose run --rm notion-rag python main.py update abc123def456
```

출력:
```
🔄 Notion 페이지 업데이트 시작

📖 페이지 abc123def456 처리 중...
🔄 기존 페이지 '프로젝트 개요' 삭제 중...
🗑️ 페이지 abc123def456 삭제 완료 (5 청크)
✅ 페이지 '프로젝트 개요' 인덱싱 완료 (6 청크)

✅ 모든 페이지 업데이트 완료!
```

### 3. 페이지 삭제

```bash
docker-compose run --rm notion-rag python main.py delete abc123def456
```

출력:
```
🗑️ 페이지 삭제 시작

🗑️ 페이지 abc123def456 삭제 완료 (6 청크)

✅ 삭제 완료!
```

### 4. 질문하기

```bash
docker-compose run --rm notion-rag python main.py query "이 프로젝트에서 사용하는 기술은?"
```

출력:
```
🔍 질문: 이 프로젝트에서 사용하는 기술은?

📚 관련 문서 검색 중...
✅ 3개 문서 발견

🤖 답변 생성 중...

💡 답변:
이 프로젝트는 Python, ChromaDB, Ollama를 주요 기술로 사용합니다...

📄 참고 문서:
  - 기술 스택
  - 프로젝트 개요
```

## 🏗 아키텍처

```
Notion 페이지들
    ↓
NotionPageExtractor (텍스트 추출)
    ↓
VectorStoreManager (청크 분할 & 임베딩)
    ↓
ChromaDB (벡터 저장)
    ↓
사용자 질문 → 벡터 검색 → 관련 문서 추출
    ↓
OllamaQA (컨텍스트 기반 답변 생성)
    ↓
답변 반환
```

## 📁 프로젝트 구조

```
.
├── main.py                 # RAG 시스템 메인 코드
├── requirements.txt        # Python 의존성
├── Dockerfile             # Docker 이미지 설정
├── docker-compose.yml     # Docker Compose 설정
├── .env                   # 환경 변수 (Git 제외)
├── .env.example          # 환경 변수 템플릿
└── chroma_db/            # ChromaDB 저장소 (자동 생성)
```

## 🔧 커스터마이징

### 청크 크기 조절

`VectorStoreManager._split_into_chunks()` 메서드의 `chunk_size` 파라미터 수정:

```python
def _split_into_chunks(self, text: str, chunk_size: int = 1000):  # 기본 500 → 1000
```

### 검색 결과 개수 변경

```python
relevant_docs = vector_store.search(question, n_results=5)  # 기본 3 → 5
```

### 다른 Ollama 모델 사용

`.env` 파일에 추가하거나 코드에서 직접 지정:

```python
embeddings = OllamaEmbeddings(OLLAMA_BASE_URL, model="llama3.1")
qa = OllamaQA(OLLAMA_BASE_URL, model="llama3.1")
```

## 🐛 문제 해결

### "임베딩 생성 오류"

- Ollama 서버 실행 확인: `curl http://localhost:11434/api/tags`
- 모델 설치 확인: `ollama list`
- 필요시 모델 다운로드: `ollama pull llama3`

### "관련 문서를 찾을 수 없습니다"

- 먼저 페이지를 인덱싱했는지 확인
- `chroma_db/` 디렉토리가 존재하는지 확인

### "페이지 읽기 오류"

- Notion Integration이 페이지에 연결되어 있는지 확인
- Token과 Page ID가 올바른지 확인

## 📝 라이선스

이 프로젝트는 교육 및 실습 목적으로 제작되었습니다.

---

**Made with ❤️ using Ollama, ChromaDB & Notion API**
