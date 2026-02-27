"""
웹 검색 모듈

DuckDuckGo를 사용한 웹 검색 기능을 제공합니다.
"""

from typing import List, Dict
from duckduckgo_search import DDGS


class WebSearcher:
    """DuckDuckGo를 사용한 웹 검색"""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        웹 검색 수행
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
        
        Returns:
            List[Dict]: 검색 결과 목록
        """
        try:
            results = []
            search_results = self.ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("body", ""),
                    "link": result.get("href", ""),
                    "url": result.get("href", "")  # 하위 호환성
                })
            
            if not results:
                print(f"⚠️ 웹 검색 결과 없음: {query}")
            
            return results
        
        except Exception as e:
            print(f"❌ 웹 검색 오류: {e}")
            return []
