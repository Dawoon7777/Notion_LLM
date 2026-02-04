import os
from dotenv import load_dotenv
from notion_client import Client
import requests
import json

# 환경 변수 로드
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# Notion 클라이언트 초기화
notion = Client(auth=NOTION_TOKEN)


def get_notion_page_content(page_id):
    """노션 페이지의 텍스트 블록을 읽어오는 함수"""
    try:
        blocks = notion.blocks.children.list(block_id=page_id)
        content = []
        
        for block in blocks["results"]:
            block_type = block["type"]
            
            # 다양한 블록 타입 처리
            if block_type == "paragraph":
                text = extract_text_from_rich_text(block["paragraph"]["rich_text"])
                if text:
                    content.append(text)
            elif block_type == "heading_1":
                text = extract_text_from_rich_text(block["heading_1"]["rich_text"])
                if text:
                    content.append(f"# {text}")
            elif block_type == "heading_2":
                text = extract_text_from_rich_text(block["heading_2"]["rich_text"])
                if text:
                    content.append(f"## {text}")
            elif block_type == "heading_3":
                text = extract_text_from_rich_text(block["heading_3"]["rich_text"])
                if text:
                    content.append(f"### {text}")
            elif block_type == "bulleted_list_item":
                text = extract_text_from_rich_text(block["bulleted_list_item"]["rich_text"])
                if text:
                    content.append(f"• {text}")
            elif block_type == "numbered_list_item":
                text = extract_text_from_rich_text(block["numbered_list_item"]["rich_text"])
                if text:
                    content.append(f"- {text}")
        
        return "\n".join(content)
    
    except Exception as e:
        print(f"노션 페이지 읽기 오류: {e}")
        return None


def extract_text_from_rich_text(rich_text_array):
    """Rich text 배열에서 순수 텍스트 추출"""
    return "".join([text["plain_text"] for text in rich_text_array])


def summarize_with_ollama(text, model="llama3"):
    """Ollama를 사용하여 텍스트 요약"""
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        
        prompt = f"""다음 텍스트를 한국어로 간결하게 요약해주세요:

{text}

요약:"""
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result["response"]
    
    except Exception as e:
        print(f"Ollama 요약 오류: {e}")
        return None


def add_summary_to_notion(page_id, summary):
    """노션 페이지에 AI 요약 블록 추가"""
    try:
        # 구분선 추가
        notion.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            ]
        )
        
        # AI 요약 제목 추가
        notion.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "🤖 AI 요약"}
                            }
                        ]
                    }
                }
            ]
        )
        
        # 요약 내용 추가
        notion.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": summary}
                            }
                        ]
                    }
                }
            ]
        )
        
        print("✅ 노션 페이지에 요약이 추가되었습니다.")
        return True
    
    except Exception as e:
        print(f"노션 페이지 업데이트 오류: {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 Notion + Ollama RAG 시스템 시작\n")
    
    # 1. 노션 페이지 내용 읽기
    print("📖 노션 페이지 읽는 중...")
    content = get_notion_page_content(NOTION_PAGE_ID)
    
    if not content:
        print("❌ 노션 페이지를 읽을 수 없습니다.")
        return
    
    print(f"✅ 읽어온 내용 ({len(content)} 글자):\n")
    print(content[:200] + "...\n" if len(content) > 200 else content + "\n")
    
    # 2. Ollama로 요약 생성
    print("🤖 Ollama로 요약 생성 중...")
    summary = summarize_with_ollama(content)
    
    if not summary:
        print("❌ 요약을 생성할 수 없습니다.")
        return
    
    print(f"✅ 요약 완료:\n{summary}\n")
    
    # 3. 노션에 요약 추가
    print("📝 노션 페이지에 요약 추가 중...")
    success = add_summary_to_notion(NOTION_PAGE_ID, summary)
    
    if success:
        print("\n🎉 모든 작업이 완료되었습니다!")
    else:
        print("\n❌ 요약 추가에 실패했습니다.")


if __name__ == "__main__":
    main()
