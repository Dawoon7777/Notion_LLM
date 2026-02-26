"""
증분 동기화 엔진

Notion API의 last_edited_time을 기반으로 변경된 페이지만 선별하여 인덱싱합니다.
"""

import json
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from pathlib import Path


@dataclass
class SyncResult:
    """동기화 결과"""
    added: List[str]       # 추가된 페이지 ID 목록
    modified: List[str]    # 수정된 페이지 ID 목록
    deleted: List[str]     # 삭제된 페이지 ID 목록
    elapsed_seconds: float


class IncrementalSyncEngine:
    """
    증분 동기화 엔진
    
    Notion 페이지의 last_edited_time을 추적하여 변경된 페이지만 인덱싱합니다.
    """
    
    def __init__(self, extractor, vector_store, embedding_processor, state_path: str):
        """
        Args:
            extractor: NotionPageExtractor 인스턴스
            vector_store: VectorStoreManager 인스턴스
            embedding_processor: EmbeddingProcessor 인스턴스
            state_path: 동기화 상태 파일 경로
        """
        self.extractor = extractor
        self.vector_store = vector_store
        self.embedding_processor = embedding_processor
        self.state_path = Path(state_path)
    
    def load_state(self) -> Dict[str, str]:
        """
        sync_state.json에서 {page_id: last_edited_time} 로드
        
        Returns:
            Dict[str, str]: 페이지 ID와 마지막 수정 시간 매핑
        """
        if not self.state_path.exists():
            print(f"⚠️ 동기화 상태 파일이 없습니다: {self.state_path}")
            return {}
        
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("pages", {})
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ 동기화 상태 파일 손상: {e}")
            return {}
    
    def save_state(self, state: Dict[str, str]) -> None:
        """
        동기화 상태를 sync_state.json에 저장
        
        Args:
            state: {page_id: last_edited_time} 딕셔너리
        """
        data = {
            "last_sync_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pages": state
        }
        
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 동기화 상태 저장 완료: {self.state_path}")
        except Exception as e:
            print(f"❌ 동기화 상태 저장 실패: {e}")
    
    def detect_changes(self, current: Dict[str, str], saved: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
        """
        변경 사항 감지
        
        Args:
            current: 현재 Notion에서 조회한 {page_id: last_edited_time}
            saved: 저장된 {page_id: last_edited_time}
        
        Returns:
            Tuple[List[str], List[str], List[str]]: (added, modified, deleted)
        """
        current_ids = set(current.keys())
        saved_ids = set(saved.keys())
        
        # 새로 추가된 페이지
        added = list(current_ids - saved_ids)
        
        # 삭제된 페이지
        deleted = list(saved_ids - current_ids)
        
        # 수정된 페이지 (양쪽에 존재하지만 timestamp가 다른 경우)
        modified = [
            page_id for page_id in (current_ids & saved_ids)
            if current[page_id] != saved[page_id]
        ]
        
        return added, modified, deleted
    
    async def sync(self) -> SyncResult:
        """
        증분 동기화 실행
        
        상태 파일이 없거나 손상된 경우 전체 재인덱싱을 수행합니다.
        
        Returns:
            SyncResult: 동기화 결과
        """
        start_time = time.time()
        
        print("🔄 증분 동기화 시작...")
        
        # 현재 Notion 페이지 타임스탬프 조회
        try:
            current_state = self.extractor.get_pages_with_timestamps()
            print(f"📊 현재 Notion 페이지 수: {len(current_state)}")
        except Exception as e:
            print(f"❌ Notion 페이지 조회 실패: {e}")
            return SyncResult([], [], [], time.time() - start_time)
        
        # 저장된 상태 로드
        saved_state = self.load_state()
        
        # 상태 파일이 없으면 전체 재인덱싱
        if not saved_state:
            print("⚠️ 저장된 상태가 없습니다. 전체 재인덱싱을 수행합니다.")
            added = list(current_state.keys())
            modified = []
            deleted = []
        else:
            # 변경 사항 감지
            added, modified, deleted = self.detect_changes(current_state, saved_state)
            print(f"📈 변경 사항: 추가 {len(added)}, 수정 {len(modified)}, 삭제 {len(deleted)}")
        
        # 삭제된 페이지 처리
        for page_id in deleted:
            try:
                count = self.vector_store.delete_page(page_id)
                print(f"🗑️ 페이지 삭제: {page_id} ({count}개 청크)")
            except Exception as e:
                print(f"❌ 페이지 삭제 실패 {page_id}: {e}")
        
        # 수정된 페이지 처리 (삭제 후 재인덱싱)
        for page_id in modified:
            try:
                # 기존 청크 삭제
                self.vector_store.delete_page(page_id)
                
                # 페이지 콘텐츠 추출
                page_data = self.extractor.get_page_content(page_id)
                if not page_data:
                    print(f"⚠️ 페이지 콘텐츠 추출 실패: {page_id}")
                    continue
                
                # 청크 분할 (간단한 구현: 1000자 단위)
                content = page_data.get("content", "")
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                
                # 임베딩 생성
                result = await self.embedding_processor.embed_texts(chunks)
                
                # ChromaDB에 저장
                self.vector_store.add_chunks(
                    page_id=page_id,
                    title=page_data.get("title", ""),
                    chunks=chunks,
                    embeddings=result.embeddings
                )
                
                print(f"🔄 페이지 수정: {page_data.get('title', page_id)} ({len(chunks)}개 청크)")
            except Exception as e:
                print(f"❌ 페이지 수정 실패 {page_id}: {e}")
        
        # 새로 추가된 페이지 처리
        for page_id in added:
            try:
                # 페이지 콘텐츠 추출
                page_data = self.extractor.get_page_content(page_id)
                if not page_data:
                    print(f"⚠️ 페이지 콘텐츠 추출 실패: {page_id}")
                    continue
                
                # 청크 분할
                content = page_data.get("content", "")
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                
                # 임베딩 생성
                result = await self.embedding_processor.embed_texts(chunks)
                
                # ChromaDB에 저장
                self.vector_store.add_chunks(
                    page_id=page_id,
                    title=page_data.get("title", ""),
                    chunks=chunks,
                    embeddings=result.embeddings
                )
                
                print(f"➕ 페이지 추가: {page_data.get('title', page_id)} ({len(chunks)}개 청크)")
            except Exception as e:
                print(f"❌ 페이지 추가 실패 {page_id}: {e}")
        
        # 상태 저장
        self.save_state(current_state)
        
        elapsed = time.time() - start_time
        print(f"✅ 증분 동기화 완료 (소요 시간: {elapsed:.2f}초)")
        
        return SyncResult(
            added=added,
            modified=modified,
            deleted=deleted,
            elapsed_seconds=elapsed
        )
