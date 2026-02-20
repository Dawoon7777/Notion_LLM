---
inclusion: always
---

# Notion RAG 프로젝트 규칙

## 📝 코딩 스타일

### 네이밍 규칙
- 함수명: `snake_case` (예: `get_page_content`, `index_all_pages`)
- 클래스명: `PascalCase` (예: `NotionPageExtractor`, `VectorStoreManager`)
- 상수: `UPPER_SNAKE_CASE` (예: `NOTION_TOKEN`, `OLLAMA_BASE_URL`)

### 언어 규칙
- 모든 에러 메시지는 **한글**로 출력
- 로그 메시지도 한글 사용 (예: `print("✅ 인덱싱 완료")`)
- 주석은 한글로 작성

### API 설계
- RESTful 규칙 준수
- 응답 형식 통일: `{"status": "success/error", "message": "...", ...}`
- HTTP 상태 코드 적절히 사용 (200, 404, 500 등)

## 🛡 필수 체크사항

### Notion API 호출
```python
# ✅ 올바른 예시
try:
    result = notion.blocks.children.list(block_id=page_id)
except Exception as e:
    print(f"❌ Notion API 오류: {e}")
    return None
```

### Ollama 연결
- 연결 실패 시 재시도 로직 포함
- 타임아웃 설정 필수
- 에러 발생 시 명확한 메시지

### 환경 변수
- 누락 시 `ValueError`로 명확한 에러 메시지
- `.env.example` 파일 항상 최신 상태 유지

## 📁 파일 구조

### 중요 파일
- `main.py`: CLI 진입점
- `api.py`: FastAPI 서버
- `config.py`: 환경 변수 관리
- `scheduler.py`: 자동 업데이트

### 참조 파일
- API 스펙: #[[file:api.py]]
- 환경 설정 예시: #[[file:.env.example]]
- 프로젝트 문서: #[[file:README.md]]

## 🔧 개발 워크플로우

1. 기능 개발 전 관련 파일 확인
2. 에러 핸들링 필수 포함
3. 테스트 후 README 업데이트
4. 환경 변수 변경 시 `.env.example` 동기화

## 🚫 금지 사항

- `.env` 파일을 Git에 커밋하지 않기
- `chroma_db/` 디렉토리를 Git에 올리지 않기
- 하드코딩된 토큰이나 비밀번호 사용 금지
- 에러를 무시하고 넘어가지 않기
