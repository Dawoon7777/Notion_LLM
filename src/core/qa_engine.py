"""
질의응답 엔진 모듈

VectorStore, Reranker, ContextRouter, WebSearcher를 통합한 질의응답 파이프라인입니다.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import requests


@dataclass
class AnswerResult:
    """답변 결과"""
    answer: str
    sources: List[Dict]        # 사용된 출처 목록
    source_type: str           # "notion" | "web" | "general" | "mixed"
    category: str              # 질문 카테고리


class QAEngine:
    """
    질의응답 엔진
    
    Context Routing → 검색 → 리랭킹 → LLM 답변 파이프라인을 실행합니다.
    """
    
    def __init__(self, vector_store, reranker, context_router, web_searcher, config):
        """
        Args:
            vector_store: VectorStoreManager 인스턴스
            reranker: Reranker 인스턴스
            context_router: ContextRouter 인스턴스
            web_searcher: WebSearcher 인스턴스
            config: 설정 딕셔너리
        """
        self.vector_store = vector_store
        self.reranker = reranker
        self.context_router = context_router
        self.web_searcher = web_searcher
        self.config = config
        
        self.base_url = config["OLLAMA_BASE_URL"]
        self.num_ctx = config["OLLAMA_NUM_CTX"]
        self.keep_alive = config["OLLAMA_KEEP_ALIVE"]
        self.timeout = config["OLLAMA_TIMEOUT"]
    
    def answer(self, question: str, session_id: str = None,
               use_reranking: bool = True) -> AnswerResult:
        """
        질문에 대한 답변 생성
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID (선택)
            use_reranking: 리랭킹 사용 여부
        
        Returns:
            AnswerResult: 답변 결과
        """
        print(f"🤔 질문: {question}")
        
        # 1. Context Routing - 질문 의도 분류
        routing = self.context_router.classify(question)
        print(f"📍 질문 카테고리: {routing.category.value}")
        
        sources = []
        context_docs = []
        
        # 2. Notion 문서 검색
        if routing.use_notion:
            print("📚 Notion 문서 검색 중...")
            
            # 임베딩 생성 (동기식)
            from src.core.embedding_processor import EmbeddingProcessor
            embedder = EmbeddingProcessor(
                self.base_url,
                concurrency=1,
                max_retries=self.config["EMBEDDING_MAX_RETRIES"]
            )
            
            try:
                query_embedding = embedder.embed_query_sync(question)
                
                # 벡터 검색
                search_results = self.vector_store.search(
                    query_embedding,
                    n_results=self.config["SEARCH_TOP_K"]
                )
                
                # 리랭킹
                if use_reranking and search_results:
                    print("🔄 리랭킹 중...")
                    ranked_docs = self.reranker.rerank(
                        question,
                        search_results,
                        top_n=self.config["RERANK_TOP_N"]
                    )
                    
                    for doc in ranked_docs:
                        context_docs.append(doc.content)
                        sources.append({
                            "title": doc.title,
                            "page_id": doc.page_id,
                            "type": "notion"
                        })
                else:
                    # 리랭킹 없이 사용
                    for doc in search_results[:self.config["RERANK_TOP_N"]]:
                        context_docs.append(doc["content"])
                        sources.append({
                            "title": doc["title"],
                            "page_id": doc["page_id"],
                            "type": "notion"
                        })
            
            except Exception as e:
                print(f"⚠️ Notion 검색 오류: {e}")
        
        # 3. 웹 검색
        web_results = []
        if routing.use_web:
            print("🌐 웹 검색 중...")
            try:
                web_results = self.web_searcher.search(question, max_results=3)
                
                for result in web_results:
                    context_docs.append(result.get("snippet", ""))
                    sources.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "type": "web"
                    })
            
            except Exception as e:
                print(f"⚠️ 웹 검색 오류: {e}")
        
        # 4. LLM 답변 생성
        print("🤖 답변 생성 중...")
        
        # 출처 타입 결정
        notion_count = sum(1 for s in sources if s.get("type") == "notion")
        web_count = sum(1 for s in sources if s.get("type") == "web")
        
        if notion_count > 0 and web_count > 0:
            source_type = "mixed"
        elif notion_count > 0:
            source_type = "notion"
        elif web_count > 0:
            source_type = "web"
        else:
            source_type = "general"
        
        # 컨텍스트 구성
        context_text = "\n\n".join(context_docs) if context_docs else "관련 문서를 찾을 수 없습니다."
        
        # LLM 호출
        answer = self._generate_answer(question, context_text, source_type)
        
        print(f"✅ 답변 완료 (출처: {source_type})")
        
        return AnswerResult(
            answer=answer,
            sources=sources,
            source_type=source_type,
            category=routing.category.value
        )
    
    def _generate_answer(self, question: str, context: str, source_type: str) -> str:
        """
        LLM을 사용하여 답변 생성
        
        Args:
            question: 질문
            context: 컨텍스트 문서
            source_type: 출처 타입
        
        Returns:
            str: 생성된 답변
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            prompt = f"""다음 컨텍스트를 참고하여 질문에 답변하세요.

컨텍스트:
{context}

질문: {question}

답변:"""
            
            payload = {
                "model": "llama3.3:70b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": self.num_ctx,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "답변을 생성할 수 없습니다.")
        
        except Exception as e:
            print(f"❌ LLM 답변 생성 오류: {e}")
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {e}"
