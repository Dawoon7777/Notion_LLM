import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

# 환경변수 검증
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

if not NOTION_TOKEN:
    raise ValueError("❌ NOTION_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")

if not OLLAMA_BASE_URL:
    raise ValueError("❌ OLLAMA_BASE_URL이 설정되지 않았습니다. .env 파일을 확인하세요.")

# Notion Client 싱글톤
notion = Client(auth=NOTION_TOKEN)
