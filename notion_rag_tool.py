"""
title: Notion RAG Search
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1.0
license: MIT
"""

import requests
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        NOTION_RAG_API_URL: str = Field(
            default="http://host.docker.internal:8000",
            description="Notion RAG API URL"
        )

    def __init__(self):
        self.valves = self.Valves()

    def search_notion(
        self,
        query: str,
        use_web_search: bool = True,
        __user__: dict = {}
    ) -> str:
        """
        Notion 문서를 검색하고 AI 답변을 생성합니다.
        웹 검색과 일반 지식도 함께 활용합니다.
        
        :param query: 검색할 질문
        :param use_web_search: 웹 검색 사용 여부 (기본: True)
        :return: AI가 생성한 답변과 출처
        """
        try:
            response = requests.post(
                f"{self.valves.NOTION_RAG_API_URL}/query",
                json={
                    "question": query,
                    "use_web_search": use_web_search,
                    "n_results": 3
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "답변을 생성할 수 없습니다.")
                sources = data.get("sources", [])
                
                result = f"{answer}\n\n"
                
                if sources:
                    result += "📚 참고 문서:\n"
                    for source in sources:
                        title = source.get("title", "Unknown")
                        result += f"  - {title}\n"
                
                return result
            else:
                return f"❌ API 오류: {response.status_code}"
                
        except Exception as e:
            return f"❌ 검색 실패: {str(e)}"

    def list_notion_pages(self, __user__: dict = {}) -> str:
        """
        인덱싱된 Notion 페이지 목록을 조회합니다.
        
        :return: 페이지 목록
        """
        try:
            response = requests.get(
                f"{self.valves.NOTION_RAG_API_URL}/pages",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("pages", [])
                
                if not pages:
                    return "📭 인덱싱된 페이지가 없습니다."
                
                result = f"📄 총 {len(pages)}개의 페이지:\n\n"
                for page in pages:
                    result += f"  - {page.get('title', 'Untitled')}\n"
                
                return result
            else:
                return f"❌ API 오류: {response.status_code}"
                
        except Exception as e:
            return f"❌ 조회 실패: {str(e)}"
