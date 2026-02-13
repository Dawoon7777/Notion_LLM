import requests
import chromadb
from chromadb.config import Settings
from typing import List, Dict
import hashlib
from duckduckgo_search import DDGS
from config import notion, NOTION_PAGE_ID, OLLAMA_BASE_URL


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
            print(f"페이지 검색 오류: {e}")
            return []
    
    def _get_page_title_from_search(self, page):
        """검색 결과에서 페이지 제목 추출"""
        try:
            properties = page.get("properties", {})
            
            # title 속성 찾기
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    title_array = prop_value.get("title", [])
                    if title_array:
                        return title_array[0].get("plain_text", "Untitled")
            
            # title 속성이 없으면 다른 속성 확인
            if "title" in page:
                title_array = page.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "Untitled")
            
            return "Untitled"
        except:
            return "Untitled"
    
    def extract_text_from_rich_text(self, rich_text_array):
        """Rich text 배열에서 순수 텍스트 추출"""
        return "".join([text["plain_text"] for text in rich_text_array])
    
    def get_page_content(self, page_id: str) -> Dict[str, str]:
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
            print(f"페이지 {page_id} 읽기 오류: {e}")
            return None
    
    def _get_page_title(self, page_info):
        """페이지 제목 추출"""
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
    
    def create_page(self, parent_page_id: str, title: str, content: str) -> str:
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
            return "Untitled"
    
    def get_all_pages_from_database(self, database_id: str) -> List[str]:
        """데이터베이스의 모든 페이지 ID 가져오기"""
        try:
            results = self.notion.databases.query(database_id=database_id)
            return [page["id"] for page in results["results"]]
        except Exception as e:
            print(f"데이터베이스 조회 오류: {e}")
            return []


class OllamaEmbeddings:
    """Ollama를 사용한 임베딩 생성"""
    
    def __init__(self, base_url: str, model: str = "llama3"):
        self.base_url = base_url
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """여러 문서를 임베딩"""
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """단일 쿼리를 임베딩"""
        return self._get_embedding(text)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Ollama API를 통해 임베딩 생성"""
        try:
            url = f"{self.base_url}/api/embed"
            payload = {
                "model": "bge-m3",
                "input": text
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("embeddings", [[0.0] * 1024])[0]
        except Exception as e:
            print(f"임베딩 생성 오류: {e}")
            # 실패 시 더미 임베딩 반환
            return [0.0] * 1024


class VectorStoreManager:
    """ChromaDB를 사용한 벡터 저장소 관리"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="notion_pages",
            metadata={"hnsw:space": "cosine"}
        )
        self.embeddings = OllamaEmbeddings(OLLAMA_BASE_URL)
    
    def add_page(self, page_data: Dict[str, str]):
        """페이지를 벡터 DB에 추가"""
        if not page_data or not page_data.get("content"):
            return
        
        page_id = page_data["page_id"]
        title = page_data["title"]
        content = page_data["content"]
        
        # 청크로 분할 (간단한 문단 단위)
        chunks = self._split_into_chunks(content)
        
        for i, chunk in enumerate(chunks):
            doc_id = f"{page_id}_{i}"
            embedding = self.embeddings.embed_query(chunk)
            
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "page_id": page_id,
                    "title": title,
                    "chunk_index": i
                }]
            )
        
        print(f"✅ 페이지 '{title}' 인덱싱 완료 ({len(chunks)} 청크)")
    
    def delete_page(self, page_id: str):
        """특정 페이지의 모든 청크 삭제"""
        try:
            results = self.collection.get(where={"page_id": page_id})
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"🗑️ 페이지 {page_id} 삭제 완료 ({len(results['ids'])} 청크)")
            else:
                print(f"⚠️ 페이지 {page_id}를 찾을 수 없습니다")
        except Exception as e:
            print(f"삭제 오류: {e}")
    
    def update_page(self, page_data: Dict[str, str]):
        """페이지 업데이트 (기존 삭제 후 재추가)"""
        if not page_data:
            return
        
        page_id = page_data["page_id"]
        title = page_data["title"]
        
        # 기존 데이터 삭제
        results = self.collection.get(where={"page_id": page_id})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            print(f"🔄 기존 페이지 '{title}' 삭제 중...")
        
        # 새 데이터 추가
        self.add_page(page_data)
    
    def _split_into_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """텍스트를 청크로 분할"""
        paragraphs = text.split("\n")
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        
        return chunks
    
    def search(self, query: str, n_results: int = 3) -> List[Dict]:
        """쿼리와 관련된 문서 검색"""
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        documents = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                documents.append({
                    "content": doc,
                    "title": metadata.get("title", "Unknown"),
                    "page_id": metadata.get("page_id", ""),
                })
        
        return documents


class WebSearcher:
    """DuckDuckGo를 사용한 웹 검색"""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """웹 검색 수행"""
        try:
            results = []
            search_results = self.ddgs.text(query, max_results=max_results)
            
            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("body", ""),
                    "url": result.get("href", "")
                })
            
            if not results:
                print(f"⚠️ 웹 검색 결과 없음: {query}")
            
            return results
        except Exception as e:
            print(f"❌ 웹 검색 오류: {e}")
            return []


class OllamaQA:
    """Ollama를 사용한 질의응답"""
    
    def __init__(self, base_url: str, model: str = "llama3.3:70b"):
        self.base_url = base_url
        self.model = model
    
    def answer(self, query: str, context_docs: List[Dict]) -> str:
        """컨텍스트를 기반으로 질문에 답변"""
        context = "\n\n".join([
            f"[{doc['title']}]\n{doc['content']}" 
            for doc in context_docs
        ])
        
        prompt = f"""다음 문서들을 참고하여 질문에 답변해주세요.

문서:
{context}

질문: {query}

답변:"""
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()["response"]
        
        except Exception as e:
            return f"답변 생성 오류: {e}"
    
    def answer_with_history(self, query: str, context_docs: List[Dict], chat_history: List[Dict], web_results: List[Dict] = None) -> str:
        """대화 기록, 컨텍스트, 웹 검색 결과를 모두 고려하여 답변"""
        # 노션 문서 컨텍스트
        context = ""
        if context_docs:
            context = "\n\n".join([
                f"[{doc['title']}]\n{doc['content']}" 
                for doc in context_docs
            ])
        
        # 웹 검색 결과
        web_context = ""
        if web_results:
            web_context = "\n\n".join([
                f"[웹 검색: {result['title']}]\n{result['snippet']}"
                for result in web_results
            ])
        
        # 대화 기록 포맷팅
        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"{'사용자' if msg['role'] == 'user' else 'AI'}: {msg['content']}"
                for msg in chat_history[-6:]  # 최근 3턴(6개 메시지)만 사용
            ])
        
        # 최적화된 프롬프트
        prompt_parts = ["당신은 Notion 문서와 웹 검색을 활용하는 AI 어시스턴트입니다.\n"]
        
        if context:
            prompt_parts.append(f"# 참고 문서 (Notion)\n{context}\n")
        
        if web_context:
            prompt_parts.append(f"# 웹 검색 결과\n{web_context}\n")
        
        prompt_parts.append(f"# 이전 대화 내역\n{history_text if history_text else '(없음)'}\n")
        prompt_parts.append(f"# 현재 질문\n{query}\n")
        
        prompt_parts.append("""# 답변 지침
1. **우선순위**: Notion 문서 > 웹 검색 결과 > 일반 지식
2. Notion 문서에 관련 내용이 있다면 그것을 중심으로 답변하세요
3. 웹 검색 결과로 최신 정보나 추가 정보를 보충하세요
4. 이전 대화 맥락을 고려하여 자연스럽게 답변하세요
5. 간결하고 명확하게 답변하세요
6. 출처를 구분하지 말고 자연스럽게 통합하세요

답변:""")
        
        prompt = "\n".join(prompt_parts)
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()["response"]
        
        except Exception as e:
            return f"답변 생성 오류: {e}"


def index_notion_pages(page_ids: List[str]):
    """여러 Notion 페이지를 인덱싱"""
    print("🚀 Notion 페이지 인덱싱 시작\n")
    
    extractor = NotionPageExtractor(notion)
    vector_store = VectorStoreManager()
    
    for page_id in page_ids:
        print(f"📖 페이지 {page_id} 처리 중...")
        page_data = extractor.get_page_content(page_id)
        if page_data:
            vector_store.add_page(page_data)
    
    print("\n✅ 모든 페이지 인덱싱 완료!")


def query_rag_system(question: str):
    """RAG 시스템에 질문"""
    print(f"\n🔍 질문: {question}\n")
    
    vector_store = VectorStoreManager()
    qa = OllamaQA(OLLAMA_BASE_URL)
    
    # 관련 문서 검색
    print("📚 관련 문서 검색 중...")
    relevant_docs = vector_store.search(question, n_results=3)
    
    if not relevant_docs:
        print("❌ 관련 문서를 찾을 수 없습니다.")
        return
    
    print(f"✅ {len(relevant_docs)}개 문서 발견\n")
    
    # 답변 생성
    print("🤖 답변 생성 중...")
    answer = qa.answer(question, relevant_docs)
    
    print(f"\n💡 답변:\n{answer}\n")
    
    print("📄 참고 문서:")
    for doc in relevant_docs:
        print(f"  - {doc['title']}")


def main():
    """메인 실행 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  전체 인덱싱: python main.py index-all")
        print("  개별 인덱싱: python main.py index <page_id1> <page_id2> ...")
        print("  페이지 목록: python main.py list")
        print("  업데이트: python main.py update <page_id1> <page_id2> ...")
        print("  삭제: python main.py delete <page_id1> <page_id2> ...")
        print("  질문: python main.py query '<질문>'")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        print("📋 Notion 페이지 목록 조회 중...\n")
        
        extractor = NotionPageExtractor(notion)
        pages = extractor.search_all_pages()
        
        if not pages:
            print("❌ 페이지를 찾을 수 없습니다.")
            return
        
        print(f"✅ 총 {len(pages)}개 페이지 발견:\n")
        for i, page in enumerate(pages, 1):
            print(f"{i}. {page['title']}")
            print(f"   ID: {page['id']}\n")
    
    elif command == "index-all":
        print("🚀 전체 Notion 페이지 인덱싱 시작\n")
        
        extractor = NotionPageExtractor(notion)
        pages = extractor.search_all_pages()
        
        if not pages:
            print("❌ 인덱싱할 페이지를 찾을 수 없습니다.")
            return
        
        print(f"📚 총 {len(pages)}개 페이지 발견\n")
        
        vector_store = VectorStoreManager()
        success_count = 0
        
        for page in pages:
            print(f"📖 '{page['title']}' 처리 중...")
            page_data = extractor.get_page_content(page['id'])
            if page_data:
                vector_store.add_page(page_data)
                success_count += 1
        
        print(f"\n✅ 인덱싱 완료! ({success_count}/{len(pages)} 성공)")
    
    elif command == "index":
        if len(sys.argv) < 3:
            # 기본 페이지 ID 사용
            page_ids = [NOTION_PAGE_ID] if NOTION_PAGE_ID else []
        else:
            page_ids = sys.argv[2:]
        
        if not page_ids:
            print("❌ 인덱싱할 페이지 ID를 지정해주세요.")
            return
        
        index_notion_pages(page_ids)
    
    elif command == "update":
        if len(sys.argv) < 3:
            print("❌ 업데이트할 페이지 ID를 지정해주세요.")
            return
        
        page_ids = sys.argv[2:]
        print("🔄 Notion 페이지 업데이트 시작\n")
        
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        
        for page_id in page_ids:
            print(f"📖 페이지 {page_id} 처리 중...")
            page_data = extractor.get_page_content(page_id)
            if page_data:
                vector_store.update_page(page_data)
        
        print("\n✅ 모든 페이지 업데이트 완료!")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ 삭제할 페이지 ID를 지정해주세요.")
            return
        
        page_ids = sys.argv[2:]
        print("🗑️ 페이지 삭제 시작\n")
        
        vector_store = VectorStoreManager()
        
        for page_id in page_ids:
            vector_store.delete_page(page_id)
        
        print("\n✅ 삭제 완료!")
    
    elif command == "query":
        if len(sys.argv) < 3:
            print("❌ 질문을 입력해주세요.")
            return
        
        question = sys.argv[2]
        query_rag_system(question)
    
    else:
        print(f"❌ 알 수 없는 명령: {command}")


if __name__ == "__main__":
    main()
