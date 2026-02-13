import schedule
import time
from datetime import datetime
from config import notion
from main import NotionPageExtractor, VectorStoreManager

def auto_update_pages():
    """모든 인덱싱된 페이지를 자동으로 업데이트"""
    print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 자동 업데이트 시작")
    
    try:
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        
        # 워크스페이스의 모든 페이지 조회
        pages = extractor.search_all_pages()
        
        if not pages:
            print("📭 업데이트할 페이지가 없습니다.")
            return
        
        print(f"📄 총 {len(pages)}개 페이지 업데이트 중...")
        
        updated = 0
        failed = 0
        
        for page in pages:
            try:
                page_id = page['id']
                page_data = extractor.get_page_content(page_id)
                
                if page_data:
                    # 기존 페이지 삭제 후 재인덱싱
                    vector_store.delete_page(page_id)
                    vector_store.add_page(page_data)
                    updated += 1
                    print(f"  ✅ {page['title']}")
                    
            except Exception as e:
                failed += 1
                print(f"  ❌ {page['title']}: {e}")
        
        print(f"\n✅ 업데이트 완료: 성공 {updated}개, 실패 {failed}개")
        
    except Exception as e:
        print(f"❌ 자동 업데이트 오류: {e}")

def run_scheduler():
    """스케줄러 실행"""
    print("🚀 Notion 자동 인덱싱 스케줄러 시작")
    print("⏰ 매일 오전 3시에 자동 업데이트됩니다.")
    print("💡 Ctrl+C로 종료할 수 있습니다.\n")
    
    # 매일 오전 3시에 실행
    schedule.every().day.at("03:00").do(auto_update_pages)
    
    # 시작 시 한 번 실행 (선택사항)
    # auto_update_pages()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크

if __name__ == "__main__":
    run_scheduler()
