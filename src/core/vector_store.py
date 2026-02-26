"""
ChromaDB 벡터 저장소 관리 모듈

페이지 청크의 추가, 삭제, 검색을 담당합니다.
"""

import chromadb
from typing import List, Dict, Optional


class VectorStoreManager:
    """
    ChromaDB 벡터 저장소 관리자
    
    페이지 청크와 임베딩을 ChromaDB에 저장하고 검색합니다.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Args:
            persist_directory: ChromaDB 저장 디렉토리
        """
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="notion_pages",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunks(self, page_id: str, title: str, chunks: List[str],
                   embeddings: List[List[float]]) -> None:
        """
        청크와 임베딩을 ChromaDB에 저장
        
        Args:
            page_id: Notion 페이지 ID
            title: 페이지 제목
            chunks: 텍스트 청크 목록
            embeddings: 임베딩 벡터 목록
        """
        if not chunks or not embeddings:
            print(f"⚠️ 빈 청크 또는 임베딩: {page_id}")
            return
        
        if len(chunks) != len(embeddings):
            print(f"⚠️ 청크와 임베딩 개수 불일치: {len(chunks)} vs {len(embeddings)}")
            return
        
        try:
            ids = []
            metadatas = []
            
            for i in range(len(chunks)):
                doc_id = f"{page_id}_{i}"
                ids.append(doc_id)
                metadatas.append({
                    "page_id": page_id,
                    "title": title,
                    "chunk_index": i
                })
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            print(f"✅ 페이지 '{title}' 저장 완료 ({len(chunks)}개 청크)")
        
        except Exception as e:
            print(f"❌ ChromaDB 저장 오류: {e}")
    
    def delete_page(self, page_id: str) -> int:
        """
        페이지의 모든 청크 삭제
        
        Args:
            page_id: Notion 페이지 ID
        
        Returns:
            int: 삭제된 청크 수
        """
        try:
            results = self.collection.get(where={"page_id": page_id})
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                count = len(results["ids"])
                print(f"🗑️ 페이지 {page_id} 삭제 완료 ({count}개 청크)")
                return count
            else:
                print(f"⚠️ 페이지 {page_id}를 찾을 수 없습니다")
                return 0
        
        except Exception as e:
            print(f"❌ ChromaDB 삭제 오류: {e}")
            return 0
    
    def search(self, query_embedding: List[float], n_results: int = 20) -> List[Dict]:
        """
        벡터 유사도 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            n_results: 반환할 결과 수
        
        Returns:
            List[Dict]: 검색 결과 (content, title, page_id, distance 포함)
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            documents = []
            
            if results["documents"] and results["documents"][0]:
                for i in range(len(results["documents"][0])):
                    doc = results["documents"][0][i]
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if results.get("distances") else 0.0
                    
                    documents.append({
                        "content": doc,
                        "title": metadata.get("title", "Unknown"),
                        "page_id": metadata.get("page_id", ""),
                        "distance": distance
                    })
            
            return documents
        
        except Exception as e:
            print(f"❌ ChromaDB 검색 오류: {e}")
            return []
    
    def get_collection_stats(self) -> Dict:
        """
        컬렉션 통계 반환
        
        Returns:
            Dict: 총 문서 수, 페이지 수 등
        """
        try:
            count = self.collection.count()
            
            # 고유 페이지 수 계산
            all_data = self.collection.get()
            unique_pages = set()
            
            if all_data["metadatas"]:
                for metadata in all_data["metadatas"]:
                    page_id = metadata.get("page_id")
                    if page_id:
                        unique_pages.add(page_id)
            
            return {
                "total_chunks": count,
                "unique_pages": len(unique_pages)
            }
        
        except Exception as e:
            print(f"❌ ChromaDB 통계 조회 오류: {e}")
            return {
                "total_chunks": 0,
                "unique_pages": 0
            }
