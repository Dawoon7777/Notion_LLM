"""
FastAPI 서버 모듈

Notion RAG 시스템의 REST API를 제공합니다.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
import asyncio

from src.core.config import load_config, get_notion_client
from src.core.notion_extractor import NotionPageExtractor
from src.core.vector_store import VectorStoreManager
from src.core.embedding_processor import EmbeddingProcessor
from src.core.incremental_sync import IncrementalSyncEngine
from src.core.reranker import Reranker
from src.core.context_router import ContextRouter
from src.core.qa_engine import QAEngine
from src.utils.web_searcher import WebSearcher

# 설정 로드
config = load_config()
notion = get_notion_client()

# 컴포넌트 초기화
extractor = NotionPageExtractor(notion)
vector_store = VectorStoreManager()
embedding_processor = EmbeddingProcessor(
    config["OLLAMA_BASE_URL"],
    concurrency=config["EMBEDDING_CONCURRENCY"],
    max_retries=config["EMBEDDING_MAX_RETRIES"]
)
reranker = Reranker(config["OLLAMA_BASE_URL"])
context_router = ContextRouter(config["OLLAMA_BASE_URL"])
web_searcher = WebSearcher()
qa_engine = QAEngine(vector_store, reranker, context_router, web_searcher, config)

# 증분 동기화 엔진
sync_engine = IncrementalSyncEngine(
    extractor,
    vector_store,
    embedding_processor,
    config["SYNC_STATE_PATH"]
)

app = FastAPI(title="Notion RAG API v2.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 세션별 대화 기록 저장소
chat_sessions = {}


# ===== Pydantic 모델 =====

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    use_reranking: Optional[bool] = True


class QueryResponse(BaseModel):
    status: str
    answer: str
    sources: List[Dict]
    source_type: str
    category: str
    session_id: str


class SyncResponse(BaseModel):
    status: str
    message: str
    added: int
    modified: int
    deleted: int
    elapsed_seconds: float


class SyncStatusResponse(BaseModel):
    status: str
    last_sync_time: Optional[str]
    total_pages: int


class IndexRequest(BaseModel):
    page_ids: List[str]


class AppendRequest(BaseModel):
    page_id: str
    content: str


class CreatePageRequest(BaseModel):
    parent_page_id: str
    title: str
    content: str


# ===== 엔드포인트 =====

@app.get("/")
def root():
    """index.html 서빙"""
    return FileResponse("index.html")


@app.get("/health")
def health_check():
    """헬스 체크"""
    try:
        stats = vector_store.get_collection_stats()
        
        return {
            "status": "success",
            "message": "Notion RAG API v2.0 실행 중",
            "ollama": config["OLLAMA_BASE_URL"],
            "notion": "연결됨" if notion else "미설정",
            "active_sessions": len(chat_sessions),
            "total_chunks": stats["total_chunks"],
            "unique_pages": stats["unique_pages"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")


@app.get("/pages")
def list_pages():
    """Notion 워크스페이스의 모든 페이지 목록"""
    try:
        pages = extractor.search_all_pages()
        
        return {
            "status": "success",
            "count": len(pages),
            "pages": pages
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 목록 조회 실패: {str(e)}")


@app.post("/sync", response_model=SyncResponse)
async def manual_sync():
    """증분 동기화 수동 트리거"""
    try:
        print("🔄 수동 동기화 시작...")
        
        result = await sync_engine.sync()
        
        return SyncResponse(
            status="success",
            message=f"동기화 완료: 추가 {len(result.added)}, 수정 {len(result.modified)}, 삭제 {len(result.deleted)}",
            added=len(result.added),
            modified=len(result.modified),
            deleted=len(result.deleted),
            elapsed_seconds=result.elapsed_seconds
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"동기화 실패: {str(e)}")


@app.get("/sync/status", response_model=SyncStatusResponse)
def sync_status():
    """마지막 동기화 상태 조회"""
    try:
        import json
        from pathlib import Path
        
        state_path = Path(config["SYNC_STATE_PATH"])
        
        if not state_path.exists():
            return SyncStatusResponse(
                status="success",
                last_sync_time=None,
                total_pages=0
            )
        
        with open(state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return SyncStatusResponse(
            status="success",
            last_sync_time=data.get("last_sync_time"),
            total_pages=len(data.get("pages", {}))
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"동기화 상태 조회 실패: {str(e)}")


@app.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """RAG 시스템에 질문"""
    try:
        # 세션 ID 생성 또는 가져오기
        session_id = request.session_id or str(uuid.uuid4())
        
        # 세션 초기화
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        # QA 엔진으로 답변 생성
        result = qa_engine.answer(
            request.question,
            session_id=session_id,
            use_reranking=request.use_reranking
        )
        
        # 대화 기록 저장
        chat_sessions[session_id].append({"role": "user", "content": request.question})
        chat_sessions[session_id].append({"role": "assistant", "content": result.answer})
        
        # 최근 20개 메시지만 유지
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]
        
        return QueryResponse(
            status="success",
            answer=result.answer,
            sources=result.sources,
            source_type=result.source_type,
            category=result.category,
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질문 처리 실패: {str(e)}")


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """세션 대화 기록 삭제"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "success", "message": f"세션 {session_id} 삭제 완료"}
    
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")


@app.get("/session/{session_id}")
def get_session_history(session_id: str):
    """세션 대화 기록 조회"""
    if session_id in chat_sessions:
        return {
            "status": "success",
            "session_id": session_id,
            "history": chat_sessions[session_id]
        }
    
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")


@app.post("/append")
def append_to_page(request: AppendRequest):
    """Notion 페이지에 내용 추가"""
    try:
        success = extractor.append_to_page(request.page_id, request.content)
        
        if success:
            return {
                "status": "success",
                "message": "페이지에 내용이 추가되었습니다",
                "page_id": request.page_id
            }
        else:
            raise HTTPException(status_code=500, detail="페이지 수정 실패")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 수정 실패: {str(e)}")


@app.post("/create-page")
def create_new_page(request: CreatePageRequest):
    """새 Notion 페이지 생성"""
    try:
        page_id = extractor.create_page(
            request.parent_page_id,
            request.title,
            request.content
        )
        
        if page_id:
            return {
                "status": "success",
                "message": "새 페이지가 생성되었습니다",
                "page_id": page_id,
                "title": request.title
            }
        else:
            raise HTTPException(status_code=500, detail="페이지 생성 실패")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 생성 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
