"""
환경 변수 중앙 관리 모듈

모든 환경 변수 로드, 검증, 기본값 설정을 담당합니다.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from notion_client import Client

# 환경 변수 로드
load_dotenv()

# 싱글톤 Notion 클라이언트
_notion_client: Optional[Client] = None


def load_config() -> dict:
    """
    환경 변수를 로드하고 필수 값을 검증합니다.
    
    Returns:
        dict: 모든 설정 값을 포함한 딕셔너리
        
    Raises:
        ValueError: 필수 환경 변수가 누락된 경우
    """
    # 필수 환경 변수 검증
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        raise ValueError("❌ 필수 환경 변수 NOTION_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    if not ollama_base_url:
        raise ValueError("❌ 필수 환경 변수 OLLAMA_BASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")
    
    # 선택적 환경 변수 (기본값 포함)
    config = {
        # Notion 설정
        "NOTION_TOKEN": notion_token,
        "NOTION_PAGE_ID": os.getenv("NOTION_PAGE_ID"),
        
        # Ollama 서버 설정
        "OLLAMA_BASE_URL": ollama_base_url,
        "OLLAMA_NUM_CTX": int(os.getenv("OLLAMA_NUM_CTX", "32768")),
        "OLLAMA_KEEP_ALIVE": int(os.getenv("OLLAMA_KEEP_ALIVE", "-1")),
        "OLLAMA_TIMEOUT": int(os.getenv("OLLAMA_TIMEOUT", "120")),
        "OLLAMA_MAX_RETRIES": int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
        
        # 임베딩 설정
        "EMBEDDING_CONCURRENCY": int(os.getenv("EMBEDDING_CONCURRENCY", "8")),
        "EMBEDDING_MAX_RETRIES": int(os.getenv("EMBEDDING_MAX_RETRIES", "3")),
        
        # 검색 설정
        "SEARCH_TOP_K": int(os.getenv("SEARCH_TOP_K", "20")),
        "RERANK_TOP_N": int(os.getenv("RERANK_TOP_N", "5")),
        
        # 동기화 설정
        "SYNC_INTERVAL_MINUTES": int(os.getenv("SYNC_INTERVAL_MINUTES", "60")),
        "SYNC_STATE_PATH": os.getenv("SYNC_STATE_PATH", "./sync_state.json"),
    }
    
    return config


def get_notion_client() -> Client:
    """
    Notion 클라이언트 싱글톤을 반환합니다.
    
    Returns:
        Client: Notion API 클라이언트
        
    Raises:
        ValueError: NOTION_TOKEN이 설정되지 않은 경우
    """
    global _notion_client
    
    if _notion_client is None:
        notion_token = os.getenv("NOTION_TOKEN")
        if not notion_token:
            raise ValueError("❌ 필수 환경 변수 NOTION_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        _notion_client = Client(auth=notion_token)
    
    return _notion_client


# 하위 호환성을 위한 전역 변수 (기존 코드에서 사용)
# 모듈 임포트 시점에 초기화 시도
try:
    _config = load_config()
    NOTION_TOKEN = _config["NOTION_TOKEN"]
    NOTION_PAGE_ID = _config["NOTION_PAGE_ID"]
    OLLAMA_BASE_URL = _config["OLLAMA_BASE_URL"]
    notion = get_notion_client()
except ValueError as e:
    # 환경 변수 누락 시 에러 메시지 출력하고 None으로 설정
    print(f"⚠️ 설정 로드 실패: {e}")
    NOTION_TOKEN = None
    NOTION_PAGE_ID = None
    OLLAMA_BASE_URL = None
    notion = None
