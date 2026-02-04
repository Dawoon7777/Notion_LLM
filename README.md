# 🤖 Notion + Ollama RAG 시스템

Notion 페이지의 내용을 읽어와 로컬 Ollama 서버로 요약한 후, 다시 Notion에 자동으로 업데이트하는 Python 기반 RAG 시스템입니다.

## 📋 목차

- [기능](#기능)
- [환경 요구사항](#환경-요구사항)
- [설치 방법](#설치-방법)
- [설정 방법](#설정-방법)
- [사용 방법](#사용-방법)
- [문제 해결](#문제-해결)

## ✨ 기능

- 📖 Notion 페이지의 다양한 블록 타입 읽기 (제목, 문단, 리스트 등)
- 🤖 로컬 Ollama 서버를 통한 AI 요약 생성
- 📝 요약 결과를 Notion 페이지에 자동 추가
- 🔄 완전 자동화된 워크플로우

## 🛠 환경 요구사항

- **OS**: WSL (Ubuntu) 또는 Linux/macOS
- **Python**: 3.8 이상
- **Ollama**: 로컬 또는 원격 서버에 설치 및 실행 중
- **Notion**: Integration Token 및 접근 권한이 있는 페이지

## 📦 설치 방법

### 1. 저장소 클론 또는 파일 다운로드

```bash
# 프로젝트 디렉토리로 이동
cd your-project-directory
```

### 2. 필요한 라이브러리 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:

```bash
pip install langchain langchain-community notion-client python-dotenv requests
```

## ⚙️ 설정 방법

### 1. Notion Integration 생성

1. [Notion Integrations 페이지](https://www.notion.so/my-integrations) 접속
2. `+ New integration` 클릭
3. Integration 이름 입력 (예: "Ollama RAG Bot")
4. Workspace 선택
5. `Submit` 클릭
6. **Internal Integration Token** 복사 (나중에 사용)

### 2. Notion 페이지 연결

1. 요약하고 싶은 Notion 페이지 열기
2. 페이지 우측 상단 `...` (더보기) 클릭
3. `Add connections` 선택
4. 생성한 Integration 선택하여 연결

### 3. Notion Page ID 확인

Notion 페이지 URL에서 Page ID 추출:

```
https://www.notion.so/My-Page-Title-abc123def456?v=...
                                  ^^^^^^^^^^^^
                                  이 부분이 Page ID
```

### 4. .env 파일 설정

`.env` 파일을 열어 다음 값들을 입력:

```env
# Notion API 설정
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PAGE_ID=abc123def456

# Ollama 서버 설정
OLLAMA_BASE_URL=http://localhost:11434
```

**주의**: `.env` 파일은 민감한 정보를 포함하므로 Git에 커밋하지 마세요!

### 5. Ollama 서버 확인

Ollama가 실행 중인지 확인:

```bash
curl http://localhost:11434/api/tags
```

llama3 모델이 설치되어 있는지 확인:

```bash
ollama list
```

없다면 설치:

```bash
ollama pull llama3
```

## 🚀 사용 방법

### 기본 실행

```bash
python main.py
```

### 실행 과정

프로그램은 다음 단계를 자동으로 수행합니다:

1. 📖 Notion 페이지 내용 읽기
2. 🤖 Ollama로 요약 생성
3. 📝 Notion 페이지에 요약 추가

### 실행 결과 예시

```
🚀 Notion + Ollama RAG 시스템 시작

📖 노션 페이지 읽는 중...
✅ 읽어온 내용 (1234 글자):
# 프로젝트 개요
이 프로젝트는...

🤖 Ollama로 요약 생성 중...
✅ 요약 완료:
이 문서는 프로젝트의 주요 목표와 구현 방법을 설명합니다...

📝 노션 페이지에 요약 추가 중...
✅ 노션 페이지에 요약이 추가되었습니다.

🎉 모든 작업이 완료되었습니다!
```

## 🔧 커스터마이징

### 다른 Ollama 모델 사용

`main.py`의 `summarize_with_ollama()` 함수에서 모델 변경:

```python
summary = summarize_with_ollama(content, model="llama3.1")  # 또는 다른 모델
```

### 프롬프트 수정

`summarize_with_ollama()` 함수 내의 `prompt` 변수를 수정하여 요약 스타일 변경:

```python
prompt = f"""다음 텍스트를 3줄로 요약해주세요:

{text}

요약:"""
```

### 원격 Ollama 서버 사용

`.env` 파일에서 서버 주소 변경:

```env
OLLAMA_BASE_URL=http://your-server-ip:11434
```

## 🐛 문제 해결

### "노션 페이지를 읽을 수 없습니다"

- Notion Integration이 페이지에 연결되어 있는지 확인
- `NOTION_TOKEN`과 `NOTION_PAGE_ID`가 올바른지 확인
- Integration에 읽기 권한이 있는지 확인

### "요약을 생성할 수 없습니다"

- Ollama 서버가 실행 중인지 확인: `curl http://localhost:11434/api/tags`
- llama3 모델이 설치되어 있는지 확인: `ollama list`
- `OLLAMA_BASE_URL`이 올바른지 확인

### "요약 추가에 실패했습니다"

- Notion Integration에 쓰기 권한이 있는지 확인
- 페이지가 삭제되거나 이동되지 않았는지 확인

### 한글이 깨져 보이는 경우

WSL 환경에서 로케일 설정:

```bash
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8
```

## 📁 프로젝트 구조

```
.
├── main.py              # 메인 실행 파일
├── requirements.txt     # Python 의존성 목록
├── .env                 # 환경 변수 설정 (Git 제외)
└── README.md           # 프로젝트 문서
```

## 📝 라이선스

이 프로젝트는 교육 및 실습 목적으로 제작되었습니다.

## 🤝 기여

버그 리포트나 기능 제안은 언제든 환영합니다!

---

**Made with ❤️ using Ollama & Notion API**
