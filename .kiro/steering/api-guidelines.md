---
inclusion: fileMatch
fileMatchPattern: "api.py"
---

# API 개발 가이드

## 🎯 새 엔드포인트 추가 시 체크리스트

### 1. Pydantic 모델 정의
```python
class NewRequest(BaseModel):
    field1: str
    field2: Optional[int] = None
```

### 2. 엔드포인트 구현
```python
@app.post("/new-endpoint")
def new_endpoint(request: NewRequest):
    try:
        # 로직 구현
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. 에러 핸들링
- 모든 엔드포인트에 `try-except` 필수
- `HTTPException` 사용
- 적절한 HTTP 상태 코드 반환

### 4. 응답 형식 통일
```python
# 성공
{"status": "success", "message": "...", "data": {...}}

# 실패
{"status": "error", "message": "에러 설명"}
```

### 5. README 업데이트
- API 엔드포인트 문서화
- 요청/응답 예시 추가
- curl 명령어 예시 포함

## 📋 기존 엔드포인트 패턴

### 읽기 (Read)
- `GET /pages` - 목록 조회
- `POST /query` - 검색 및 질문

### 쓰기 (Write)
- `POST /append` - 내용 추가
- `POST /create-page` - 페이지 생성

### 관리 (Management)
- `POST /index` - 인덱싱
- `POST /update` - 업데이트
- `POST /delete` - 삭제

## 🔍 테스트 방법

### curl 테스트
```bash
curl -X POST http://localhost:8000/endpoint \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### 웹 UI 테스트
- http://localhost:8000 접속
- 브라우저 개발자 도구로 네트워크 확인

### API 문서
- http://localhost:8000/docs (Swagger UI)

## 🛡 보안 고려사항

- 민감한 정보는 환경 변수로 관리
- CORS 설정 확인
- 입력 값 검증 (Pydantic)
- SQL Injection 방지 (해당 시)

## 📚 참조 파일

- 환경 설정: #[[file:config.py]]
- 메인 로직: #[[file:main.py]]
- 프로젝트 문서: #[[file:README.md]]
