# 🔒 보안 가이드

## ⚠️ 현재 보안 상태

이 프로젝트는 **개발/테스트 환경**을 위해 설계되었습니다. 프로덕션 환경에서 사용하기 전에 반드시 보안 강화가 필요합니다.

## 🚨 주요 보안 취약점

### 1. CORS 설정 (심각도: 높음)
**현재:** 모든 도메인에서 API 접근 가능
```python
allow_origins=["*"]  # ⚠️ 위험!
```

**해결 방법:**
`src/api/server.py` 수정:
```python
# 환경 변수로 허용 도메인 설정
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # 필요한 메서드만
    allow_headers=["Content-Type", "Authorization"],
)
```

`.env` 파일에 추가:
```env
ALLOWED_ORIGINS=http://localhost:8000,https://yourdomain.com
```

### 2. API 인증 부재 (심각도: 높음)
**현재:** 모든 엔드포인트가 인증 없이 접근 가능

**해결 방법:**
간단한 API 키 인증 추가:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not API_KEY:
        return  # API 키 미설정 시 인증 비활성화
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키")
    return api_key

# 민감한 엔드포인트에 적용
@app.post("/sync", dependencies=[Depends(verify_api_key)])
async def manual_sync():
    ...
```

`.env` 파일에 추가:
```env
API_KEY=your-secret-api-key-here
```

### 3. 입력 검증 부족 (심각도: 중간)
**현재:** 입력값 길이 제한 없음

**해결 방법:**
Pydantic 모델에 검증 추가:

```python
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, max_length=100)
    use_reranking: Optional[bool] = True
    
    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('질문은 비어있을 수 없습니다')
        return v.strip()

class AppendRequest(BaseModel):
    page_id: str = Field(..., min_length=32, max_length=36)
    content: str = Field(..., min_length=1, max_length=10000)
    
    @validator('page_id')
    def validate_page_id(cls, v):
        # Notion 페이지 ID 형식 검증 (UUID 형식)
        import re
        if not re.match(r'^[a-f0-9]{32}$', v.replace('-', '')):
            raise ValueError('유효하지 않은 페이지 ID 형식')
        return v
```

### 4. Rate Limiting 부재 (심각도: 중간)
**현재:** 요청 제한 없음

**해결 방법:**
slowapi 라이브러리 사용:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/query")
@limiter.limit("60/minute")  # 분당 60회 제한
def query_rag(request: Request, query_request: QueryRequest):
    ...

@app.post("/sync")
@limiter.limit("10/hour")  # 시간당 10회 제한
async def manual_sync(request: Request):
    ...
```

### 5. 민감 정보 노출 (심각도: 중간)
**현재:** `/health` 엔드포인트에서 내부 정보 노출

**해결 방법:**
```python
@app.get("/health")
def health_check():
    """헬스 체크"""
    try:
        stats = vector_store.get_collection_stats()
        
        # 프로덕션 환경에서는 민감 정보 마스킹
        is_production = os.getenv("ENVIRONMENT") == "production"
        
        return {
            "status": "success",
            "message": "Notion RAG API v2.0 실행 중",
            "ollama": "연결됨" if not is_production else None,  # 프로덕션에서는 숨김
            "notion": "연결됨" if notion else "미설정",
            "active_sessions": len(chat_sessions) if not is_production else None,
            "total_chunks": stats["total_chunks"] if not is_production else None,
            "unique_pages": stats["unique_pages"] if not is_production else None
        }
    except Exception as e:
        # 프로덕션에서는 상세 에러 숨김
        detail = str(e) if not is_production else "서버 오류"
        raise HTTPException(status_code=500, detail=detail)
```

## 🛡️ 프로덕션 체크리스트

### 필수 사항
- [ ] CORS 설정을 특정 도메인으로 제한
- [ ] API 키 인증 활성화
- [ ] 입력 검증 강화
- [ ] Rate Limiting 적용
- [ ] HTTPS 사용 (리버스 프록시)
- [ ] 환경 변수 `.env` 파일 보안 설정
- [ ] Docker 컨테이너 비특권 사용자로 실행

### 권장 사항
- [ ] 로깅 시스템 구축
- [ ] 모니터링 및 알림 설정
- [ ] 정기적인 보안 업데이트
- [ ] 백업 및 복구 계획
- [ ] 침입 탐지 시스템 (IDS)

## 🔐 환경 변수 보안

### .env 파일 권한 설정
```bash
chmod 600 .env  # 소유자만 읽기/쓰기 가능
```

### Docker Secrets 사용 (권장)
```yaml
# docker-compose.yml
services:
  api:
    secrets:
      - notion_token
      - api_key
    environment:
      NOTION_TOKEN_FILE: /run/secrets/notion_token
      API_KEY_FILE: /run/secrets/api_key

secrets:
  notion_token:
    file: ./secrets/notion_token.txt
  api_key:
    file: ./secrets/api_key.txt
```

## 📚 추가 리소스

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

## 🚀 빠른 보안 강화

최소한의 보안을 위해 다음 환경 변수를 설정하세요:

```env
# .env
ALLOWED_ORIGINS=http://localhost:8000
API_KEY=your-random-secret-key-min-32-chars
ENVIRONMENT=production
```

그리고 `src/api/server.py`에서 CORS 설정만 수정하면 기본적인 보안이 적용됩니다.

---

**⚠️ 주의:** 이 가이드는 기본적인 보안 조치만 다룹니다. 실제 프로덕션 환경에서는 전문적인 보안 감사가 필요합니다.
