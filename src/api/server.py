from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import uuid
from config import notion, OLLAMA_BASE_URL
from main import NotionPageExtractor, VectorStoreManager, OllamaQA, WebSearcher

app = FastAPI(title="Notion RAG API")

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


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class IndexRequest(BaseModel):
    page_ids: List[str]


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    n_results: Optional[int] = 3
    use_web_search: Optional[bool] = True


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]
    session_id: str


class AppendRequest(BaseModel):
    page_id: str
    content: str


class CreatePageRequest(BaseModel):
    parent_page_id: str
    title: str
    content: str


@app.get("/")
def root():
    """index.html 서빙"""
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"message": "Notion RAG API", "status": "running"}


@app.get("/pages")
def list_pages():
    """Notion 워크스페이스의 모든 페이지 목록"""
    try:
        extractor = NotionPageExtractor(notion)
        pages = extractor.search_all_pages()
        
        return {
            "status": "success",
            "count": len(pages),
            "pages": pages
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index-all")
def index_all_pages():
    """워크스페이스의 모든 페이지 인덱싱"""
    try:
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        
        pages = extractor.search_all_pages()
        
        if not pages:
            raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다")
        
        indexed = []
        failed = []
        
        for page in pages:
            try:
                page_data = extractor.get_page_content(page['id'])
                if page_data:
                    vector_store.add_page(page_data)
                    indexed.append({
                        "page_id": page['id'],
                        "title": page['title']
                    })
            except Exception as e:
                failed.append({
                    "page_id": page['id'],
                    "title": page['title'],
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "total": len(pages),
            "indexed": len(indexed),
            "failed": len(failed),
            "indexed_pages": indexed,
            "failed_pages": failed
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index")
def index_pages(request: IndexRequest):
    """Notion 페이지 인덱싱"""
    try:
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        
        indexed = []
        for page_id in request.page_ids:
            page_data = extractor.get_page_content(page_id)
            if page_data:
                vector_store.add_page(page_data)
                indexed.append({
                    "page_id": page_id,
                    "title": page_data["title"]
                })
        
        return {
            "status": "success",
            "indexed_pages": indexed,
            "count": len(indexed)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update")
def update_pages(request: IndexRequest):
    """Notion 페이지 업데이트"""
    try:
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        
        updated = []
        for page_id in request.page_ids:
            page_data = extractor.get_page_content(page_id)
            if page_data:
                vector_store.update_page(page_data)
                updated.append({
                    "page_id": page_id,
                    "title": page_data["title"]
                })
        
        return {
            "status": "success",
            "updated_pages": updated,
            "count": len(updated)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/delete")
def delete_pages(request: IndexRequest):
    """페이지 삭제"""
    try:
        vector_store = VectorStoreManager()
        
        deleted = []
        for page_id in request.page_ids:
            vector_store.delete_page(page_id)
            deleted.append(page_id)
        
        return {
            "status": "success",
            "deleted_pages": deleted,
            "count": len(deleted)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """RAG 시스템에 질문 (대화 기록 포함, 웹 검색 + 일반 지식 혼합)"""
    try:
        # 세션 ID 생성 또는 가져오기
        session_id = request.session_id or str(uuid.uuid4())
        
        # 세션 초기화
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []
        
        vector_store = VectorStoreManager()
        qa = OllamaQA(OLLAMA_BASE_URL)
        
        # 관련 문서 검색 (없어도 계속 진행)
        relevant_docs = vector_store.search(request.question, n_results=request.n_results)
        
        # 웹 검색 (옵션)
        web_results = []
        if request.use_web_search:
            try:
                web_searcher = WebSearcher()
                web_results = web_searcher.search(request.question, max_results=3)
            except Exception as e:
                print(f"웹 검색 실패: {e}")
        
        # 대화 기록 가져오기
        chat_history = chat_sessions[session_id]
        
        # 답변 생성 (Notion + 웹 검색 + 일반 지식)
        answer = qa.answer_with_history(request.question, relevant_docs, chat_history, web_results)
        
        # 대화 기록 저장
        chat_sessions[session_id].append({"role": "user", "content": request.question})
        chat_sessions[session_id].append({"role": "assistant", "content": answer})
        
        # 최근 10개 대화만 유지
        if len(chat_sessions[session_id]) > 20:
            chat_sessions[session_id] = chat_sessions[session_id][-20:]
        
        # 출처 정리 (Notion + 웹)
        sources = []
        if relevant_docs:
            sources.extend([
                {"title": f"📄 {doc['title']}", "page_id": doc["page_id"]}
                for doc in relevant_docs
            ])
        if web_results:
            sources.extend([
                {"title": f"🌐 {result['title']}", "page_id": result['url']}
                for result in web_results[:2]  # 상위 2개만
            ])
        
        return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "ollama": OLLAMA_BASE_URL,
        "notion": "connected" if NOTION_TOKEN else "not configured",
        "active_sessions": len(chat_sessions)
    }


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """세션 대화 기록 삭제"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "success", "message": "세션 삭제 완료"}
    return {"status": "not_found", "message": "세션을 찾을 수 없습니다"}


@app.post("/append")
def append_to_page(request: AppendRequest):
    """Notion 페이지에 내용 추가"""
    try:
        extractor = NotionPageExtractor(notion)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/create-page")
def create_new_page(request: CreatePageRequest):
    """새 Notion 페이지 생성"""
    try:
        extractor = NotionPageExtractor(notion)
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
        raise HTTPException(status_code=500, detail=str(e))
        return {"status": "success", "message": f"세션 {session_id} 삭제 완료"}
    return {"status": "not_found", "message": "세션을 찾을 수 없습니다"}


@app.get("/session/{session_id}")
def get_session_history(session_id: str):
    """세션 대화 기록 조회"""
    if session_id in chat_sessions:
        return {"session_id": session_id, "history": chat_sessions[session_id]}
    raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
