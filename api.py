"""
FastAPI 서버 진입점 (래퍼)

실제 구현은 src.api.server 모듈에 있습니다.
"""

from src.api.server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
