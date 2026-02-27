"""
CLI 진입점 (래퍼)

실제 구현은 src.core 모듈에 있습니다.
"""

import sys
from src.core.config import load_config, get_notion_client
from src.core.notion_extractor import NotionPageExtractor
from src.core.vector_store import VectorStoreManager


def main():
    """메인 실행 함수"""
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  페이지 목록: python main.py list")
        print("  전체 인덱싱: python main.py index-all")
        print("  개별 인덱싱: python main.py index <page_id1> <page_id2> ...")
        print("  페이지 삭제: python main.py delete <page_id1> <page_id2> ...")
        print("\n💡 고급 기능:")
        print("  API 서버: python api.py")
        print("  자동 동기화: python scheduler.py")
        return
    
    command = sys.argv[1]
    
    # 설정 로드
    config = load_config()
    notion = get_notion_client()
    
    extractor = NotionPageExtractor(notion)
    vector_store = VectorStoreManager()
    
    if command == "list":
        print("📋 Notion 페이지 목록 조회 중...\n")
        
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
        print("⚠️ 이 명령은 구버전 방식입니다. 증분 동기화를 사용하려면:")
        print("   - API 서버: POST /sync")
        print("   - 스케줄러: python scheduler.py\n")
        
        pages = extractor.search_all_pages()
        
        if not pages:
            print("❌ 인덱싱할 페이지를 찾을 수 없습니다.")
            return
        
        print(f"📚 총 {len(pages)}개 페이지 발견\n")
        
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
            print("❌ 인덱싱할 페이지 ID를 지정해주세요.")
            return
        
        page_ids = sys.argv[2:]
        print("🚀 Notion 페이지 인덱싱 시작\n")
        
        for page_id in page_ids:
            print(f"📖 페이지 {page_id} 처리 중...")
            page_data = extractor.get_page_content(page_id)
            if page_data:
                vector_store.add_page(page_data)
        
        print("\n✅ 모든 페이지 인덱싱 완료!")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ 삭제할 페이지 ID를 지정해주세요.")
            return
        
        page_ids = sys.argv[2:]
        print("🗑️ 페이지 삭제 시작\n")
        
        for page_id in page_ids:
            count = vector_store.delete_page(page_id)
            print(f"🗑️ 페이지 {page_id} 삭제 완료 ({count}개 청크)")
        
        print("\n✅ 삭제 완료!")
    
    else:
        print(f"❌ 알 수 없는 명령: {command}")
        print("사용 가능한 명령: list, index-all, index, delete")


if __name__ == "__main__":
    main()
