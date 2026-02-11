import os
from dotenv import load_dotenv
from notion_client import Client
import requests
import chromadb
from chromadb.config import Settings
from typing import List, Dict
import hashlib

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

notion = Client(auth=NOTION_TOKEN)


class NotionPageExtractor:
    """Notion 페이지에서 텍스트를 추출하는 클래스"""
    
    def __init__(self, notion_client):
        self.notion = notion_client
    
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
        print("  인덱싱: python main.py index <page_id1> <page_id2> ...")
        print("  업데이트: python main.py update <page_id1> <page_id2> ...")
        print("  삭제: python main.py delete <page_id1> <page_id2> ...")
        print("  질문: python main.py query '<질문>'")
        return
    
    command = sys.argv[1]
    
    if command == "index":
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
