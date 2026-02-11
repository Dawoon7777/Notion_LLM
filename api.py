from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from notion_client import Client
import requests
import chromadb
from typing import Dict

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

notion = Client(auth=NOTION_TOKEN)

app = FastAPI(title="Notion RAG API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexRequest(BaseModel):
    page_ids: List[str]


class QueryRequest(BaseModel):
    question: str
    n_results: Optional[int] = 3


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]


# main.py의 클래스들 임포트
from main import NotionPageExtractor, VectorStoreManager, OllamaQA


@app.get("/")
def root():
    return {"message": "Notion RAG API", "status": "running"}


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


@app.post("/query", response_model=QueryResponse)
def query_rag(request: QueryRequest):
    """RAG 시스템에 질문"""
    try:
        vector_store = VectorStoreManager()
        qa = OllamaQA(OLLAMA_BASE_URL)
        
        # 관련 문서 검색
        relevant_docs = vector_store.search(request.question, n_results=request.n_results)
        
        if not relevant_docs:
            raise HTTPException(status_code=404, detail="관련 문서를 찾을 수 없습니다")
        
        # 답변 생성
        answer = qa.answer(request.question, relevant_docs)
        
        sources = [
            {"title": doc["title"], "page_id": doc["page_id"]}
            for doc in relevant_docs
        ]
        
        return QueryResponse(answer=answer, sources=sources)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "ollama": OLLAMA_BASE_URL,
        "notion": "connected" if NOTION_TOKEN else "not configured"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
