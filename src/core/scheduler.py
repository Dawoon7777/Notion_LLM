"""
자동 동기화 스케줄러 모듈

APScheduler를 사용하여 IncrementalSyncEngine을 주기적으로 실행합니다.
"""

import asyncio
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import load_config, get_notion_client
from src.core.notion_extractor import NotionPageExtractor
from src.core.vector_store import VectorStoreManager
from src.core.embedding_processor import EmbeddingProcessor
from src.core.incremental_sync import IncrementalSyncEngine


def run_sync_job():
    """
    동기화 작업 실행
    
    비동기 함수를 동기 컨텍스트에서 실행합니다.
    """
    try:
        print(f"\n🔄 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 자동 동기화 시작")
        
        # 설정 로드
        config = load_config()
        notion = get_notion_client()
        
        # 컴포넌트 초기화
        extractor = NotionPageExtractor(notion)
        vector_store = VectorStoreManager()
        embedding_processor = EmbeddingProcessor(
            config["OLLAMA_BASE_URL"],
            concurrency=config["EMBEDDING_CONCURRENCY"],
            max_retries=config["EMBEDDING_MAX_RETRIES"]
        )
        
        # 증분 동기화 엔진
        sync_engine = IncrementalSyncEngine(
            extractor,
            vector_store,
            embedding_processor,
            config["SYNC_STATE_PATH"]
        )
        
        # 비동기 함수 실행
        result = asyncio.run(sync_engine.sync())
        
        print(f"✅ 자동 동기화 완료:")
        print(f"   - 추가: {len(result.added)}개")
        print(f"   - 수정: {len(result.modified)}개")
        print(f"   - 삭제: {len(result.deleted)}개")
        print(f"   - 소요 시간: {result.elapsed_seconds:.2f}초\n")
    
    except Exception as e:
        print(f"❌ 자동 동기화 오류: {e}\n")


def start_scheduler():
    """
    스케줄러 시작
    
    SYNC_INTERVAL_MINUTES 환경 변수로 설정된 주기로 동기화를 실행합니다.
    """
    config = load_config()
    interval_minutes = config["SYNC_INTERVAL_MINUTES"]
    
    print("🚀 Notion 자동 동기화 스케줄러 시작")
    print(f"⏰ {interval_minutes}분마다 자동 동기화됩니다.")
    print("💡 Ctrl+C로 종료할 수 있습니다.\n")
    
    scheduler = BlockingScheduler()
    
    # 주기적 실행 설정
    scheduler.add_job(
        run_sync_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id='sync_job',
        name='Notion 증분 동기화',
        replace_existing=True
    )
    
    # 시작 시 한 번 실행 (선택사항)
    # run_sync_job()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 스케줄러 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler()
