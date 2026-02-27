"""
웹 검색 모듈

DuckDuckGo를 사용하여 웹 검색을 수행합니다.
"""

from typing import List, Dict
from duckduckgo_search import DDGS


class WebSearcher:
    """
    웹 검색기
    
    DuckDuckGo를 사용하여 웹 검색을 수행합니다.
    """
    
    def __init__(self):
        """웹 검색기 초기화"""
        self.ddgs = DDGS()
    
    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        웹 검색 수행
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
        
        Returns:
            List[Dict]: 검색 결과 (title, link, snippet 포함)
        """
        try:
            results = []
            
            # DuckDuckGo 검색
            search_results = self.ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "link": result.get("href", ""),
                    "snippet": result.get("body", "")
                })
            
            print(f"🌐 웹 검색 완료: {len(results)}개 결과")
            return results
        
        except Exception as e:
            print(f"❌ 웹 검색 오류: {e}")
            return []
