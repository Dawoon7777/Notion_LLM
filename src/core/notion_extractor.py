"""
Notion 페이지 추출 모듈

Notion API를 사용하여 페이지 콘텐츠를 추출, 추가, 생성합니다.
"""

from typing import List, Dict, Optional


class NotionPageExtractor:
    """Notion 페이지에서 텍스트를 추출하는 클래스"""
    
    def __init__(self, notion_client):
        self.notion = notion_client
    
    def search_all_pages(self) -> List[Dict]:
        """워크스페이스의 모든 페이지 검색"""
        try:
            all_pages = []
            has_more = True
            start_cursor = None
            
            while has_more:
                params = {"filter": {"property": "object", "value": "page"}}
                if start_cursor:
                    params["start_cursor"] = start_cursor
                
                response = self.notion.search(**params)
                
                for page in response.get("results", []):
                    page_id = page["id"]
                    title = self._get_page_title_from_search(page)
                    all_pages.append({
                        "id": page_id,
                        "title": title
                    })
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            return all_pages
        
        except Exception as e:
            print(f"❌ 페이지 검색 오류: {e}")
            return []

    def get_pages_with_timestamps(self) -> Dict[str, str]:
        """
        모든 페이지의 {page_id: last_edited_time} 매핑 반환

        Returns:
            Dict[str, str]: 페이지 ID와 마지막 수정 시간 매핑
        """
        try:
            pages_timestamps = {}
            has_more = True
            start_cursor = None

            while has_more:
                params = {"filter": {"property": "object", "value": "page"}}
                if start_cursor:
                    params["start_cursor"] = start_cursor

                response = self.notion.search(**params)

                for page in response.get("results", []):
                    page_id = page["id"]
                    last_edited_time = page.get("last_edited_time", "")
                    pages_timestamps[page_id] = last_edited_time

                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            return pages_timestamps

        except Exception as e:
            print(f"❌ Notion API 오류: {e}")
            return {}
    
    def _get_page_title_from_search(self, page) -> str:
        """검색 결과에서 페이지 제목 추출"""
        try:
            properties = page.get("properties", {})
            
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    if title_array:
                        return title_array[0].get("plain_text", "Untitled")
            
            if "title" in page:
                title_array = page.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "Untitled")
            
            return "Untitled"
        except:
            return "Untitled"
    
    def _get_page_title(self, page_info) -> str:
        """페이지 정보에서 제목 추출"""
        try:
            properties = page_info.get("properties", {})
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    if title_array:
                        return title_array[0].get("plain_text", "Untitled")
            return "Untitled"
        except:
            return "Untitled"
    
    def extract_text_from_rich_text(self, rich_text_array) -> str:
        """Rich text 배열에서 순수 텍스트 추출"""
        return "".join([text["plain_text"] for text in rich_text_array])
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, str]]:
        """페이지 내용 추출"""
        try:
            blocks = self.notion.blocks.children.list(block_id=page_id)
            content = []
            
            for block in blocks["results"]:
                block_type = block["type"]
                
                if block_type == "paragraph":
                    text = self.extract_text_from_rich_text(block["paragraph"]["rich_text"])
                    if text:
                        content.append(text)
                elif block_type == "heading_1":
                    text = self.extract_text_from_rich_text(block["heading_1"]["rich_text"])
                    if text:
                        content.append(f"# {text}")
                elif block_type == "heading_2":
                    text = self.extract_text_from_rich_text(block["heading_2"]["rich_text"])
                    if text:
                        content.append(f"## {text}")
                elif block_type == "heading_3":
                    text = self.extract_text_from_rich_text(block["heading_3"]["rich_text"])
                    if text:
                        content.append(f"### {text}")
                elif block_type == "bulleted_list_item":
                    text = self.extract_text_from_rich_text(block["bulleted_list_item"]["rich_text"])
                    if text:
                        content.append(f"• {text}")
                elif block_type == "numbered_list_item":
                    text = self.extract_text_from_rich_text(block["numbered_list_item"]["rich_text"])
                    if text:
                        content.append(f"- {text}")
            
            page_info = self.notion.pages.retrieve(page_id=page_id)
            title = self._get_page_title(page_info)
            
            return {
                "page_id": page_id,
                "title": title,
                "content": "\n".join(content)
            }
        
        except Exception as e:
            print(f"❌ 페이지 {page_id} 읽기 오류: {e}")
            return None
    
    def append_to_page(self, page_id: str, content: str) -> bool:
        """페이지 끝에 내용 추가"""
        try:
            self.notion.blocks.children.append(
                block_id=page_id,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": content}
                                }
                            ]
                        }
                    }
                ]
            )
            print(f"✅ 페이지에 내용 추가 완료")
            return True
        except Exception as e:
            print(f"❌ 페이지 수정 오류: {e}")
            return False
    
    def create_page(self, parent_page_id: str, title: str, content: str) -> Optional[str]:
        """새 페이지 생성"""
        try:
            new_page = self.notion.pages.create(
                parent={"page_id": parent_page_id},
                properties={
                    "title": {
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": title}
                            }
                        ]
                    }
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": content}
                                }
                            ]
                        }
                    }
                ]
            )
            page_id = new_page["id"]
            print(f"✅ 새 페이지 생성 완료: {title} (ID: {page_id})")
            return page_id
        except Exception as e:
            print(f"❌ 페이지 생성 오류: {e}")
            return None
    
    def get_all_pages_from_database(self, database_id: str) -> List[str]:
        """데이터베이스의 모든 페이지 ID 가져오기"""
        try:
            results = self.notion.databases.query(database_id=database_id)
            return [page["id"] for page in results["results"]]
        except Exception as e:
            print(f"❌ 데이터베이스 조회 오류: {e}")
            return []
