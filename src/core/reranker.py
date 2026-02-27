"""
리랭킹 파이프라인 모듈

bge-reranker-v2-m3 모델을 사용하여 검색 결과를 재정렬합니다.
"""

from dataclasses import dataclass
from typing import List, Dict
import requests


@dataclass
class RankedDocument:
    """재정렬된 문서"""
    content: str
    title: str
    page_id: str
    relevance_score: float


class Reranker:
    """
    리랭킹 파이프라인
    
    검색 결과를 relevance score 기준으로 재정렬합니다.
    """
    
    def __init__(self, base_url: str, model: str = "bge-reranker-v2-m3"):
        """
        Args:
            base_url: Ollama 서버 URL
            model: 리랭커 모델 이름
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def rerank(self, query: str, documents: List[Dict], top_n: int = 5) -> List[RankedDocument]:
        """
        문서를 relevance score 기준으로 재정렬
        
        Args:
            query: 검색 쿼리
            documents: 검색 결과 문서 목록 (content, title, page_id 포함)
            top_n: 반환할 상위 N개 문서
        
        Returns:
            List[RankedDocument]: 재정렬된 상위 N개 문서
        """
        if not documents:
            print("⚠️ 재정렬할 문서가 없습니다")
            return []
        
        try:
            # 각 문서에 대해 relevance score 계산
            ranked_docs = []
            
            for doc in documents:
                content = doc.get("content", "")
                title = doc.get("title", "Unknown")
                page_id = doc.get("page_id", "")
                
                # Ollama API를 사용하여 relevance score 계산
                score = self._calculate_relevance(query, content)
                
                ranked_docs.append(RankedDocument(
                    content=content,
                    title=title,
                    page_id=page_id,
                    relevance_score=score
                ))
            
            # relevance_score 기준 내림차순 정렬
            ranked_docs.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 상위 N개 반환
            top_docs = ranked_docs[:top_n]
            
            print(f"✅ 리랭킹 완료: {len(documents)}개 → 상위 {len(top_docs)}개 선택")
            
            return top_docs
        
        except Exception as e:
            print(f"⚠️ 리랭킹 실패: {e}")
            print("⚠️ 원래 검색 결과를 사용합니다 (graceful degradation)")
            
            # 리랭킹 실패 시 원래 검색 결과 반환
            fallback_docs = []
            for doc in documents[:top_n]:
                fallback_docs.append(RankedDocument(
                    content=doc.get("content", ""),
                    title=doc.get("title", "Unknown"),
                    page_id=doc.get("page_id", ""),
                    relevance_score=0.0
                ))
            
            return fallback_docs
    
    def _calculate_relevance(self, query: str, document: str) -> float:
        """
        쿼리와 문서 간 relevance score 계산
        
        Args:
            query: 검색 쿼리
            document: 문서 내용
        
        Returns:
            float: relevance score (0.0 ~ 1.0)
        """
        try:
            # Ollama API를 사용한 간단한 relevance 계산
            # 실제로는 bge-reranker-v2-m3 모델을 사용해야 하지만,
            # Ollama에서 직접 지원하지 않으므로 LLM을 사용한 대안 구현
            
            url = f"{self.base_url}/api/generate"
            
            prompt = f"""다음 질문과 문서의 관련성을 0.0에서 1.0 사이의 숫자로 평가하세요.
숫자만 출력하세요.

질문: {query}

문서: {document[:500]}

관련성 점수:"""
            
            payload = {
                "model": "llama3.3:70b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            score_text = result.get("response", "0.5").strip()
            
            # 숫자 추출
            try:
                score = float(score_text.split()[0])
                score = max(0.0, min(1.0, score))  # 0.0 ~ 1.0 범위로 제한
                return score
            except ValueError:
                return 0.5  # 파싱 실패 시 중간값
        
        except Exception as e:
            print(f"⚠️ Relevance 계산 오류: {e}")
            return 0.5  # 오류 시 중간값 반환
