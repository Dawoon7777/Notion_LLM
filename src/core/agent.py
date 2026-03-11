"""
Agentic RAG 모듈

LLM이 도구를 선택하고 실행하는 ReAct 패턴 Agent
"""

import re
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AgentAction:
    """Agent의 행동"""
    tool: str
    tool_input: str
    reasoning: str


@dataclass
class AgentResult:
    """Agent 실행 결과"""
    answer: str
    actions: List[AgentAction]
    sources: List[Dict]


class NotionAgent:
    """
    Notion RAG Agent
    
    사용자 질문을 분석하고 적절한 도구를 선택하여 실행합니다.
    """
    
    def __init__(self, extractor, vector_store, embedding_processor, 
                 web_searcher, config):
        """
        Args:
            extractor: NotionPageExtractor 인스턴스
            vector_store: VectorStoreManager 인스턴스
            embedding_processor: EmbeddingProcessor 인스턴스
            web_searcher: WebSearcher 인스턴스
            config: 설정 딕셔너리
        """
        self.extractor = extractor
        self.vector_store = vector_store
        self.embedding_processor = embedding_processor
        self.web_searcher = web_searcher
        self.config = config
        
        self.base_url = config["OLLAMA_BASE_URL"]
        self.timeout = config["OLLAMA_TIMEOUT"]
        
        # 사용 가능한 도구 정의
        self.tools = {
            "notion_search": "Notion 문서에서 관련 정보를 검색합니다. 입력: 검색 쿼리",
            "web_search": "웹에서 최신 정보를 검색합니다. 입력: 검색 쿼리",
            "notion_append": "Notion 페이지에 내용을 추가합니다. 입력: page_id|내용",
            "notion_create": "새 Notion 페이지를 생성합니다. 입력: parent_id|제목|내용",
            "final_answer": "최종 답변을 반환합니다. 입력: 답변 내용"
        }
    
    def run(self, question: str, max_iterations: int = 5) -> AgentResult:
        """
        Agent 실행 (ReAct 패턴)
        
        Args:
            question: 사용자 질문
            max_iterations: 최대 반복 횟수
        
        Returns:
            AgentResult: 실행 결과
        """
        print(f"🤖 Agent 시작: {question}")
        
        actions = []
        sources = []
        context = []
        
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            
            # LLM에게 다음 행동 결정 요청
            action = self._decide_next_action(question, context, actions)
            
            if not action:
                print("⚠️ Agent가 행동을 결정하지 못했습니다")
                break
            
            print(f"🎯 도구: {action.tool}")
            print(f"💭 추론: {action.reasoning}")
            
            actions.append(action)
            
            # final_answer면 종료
            if action.tool == "final_answer":
                return AgentResult(
                    answer=action.tool_input,
                    actions=actions,
                    sources=sources
                )
            
            # 도구 실행
            observation = self._execute_tool(action.tool, action.tool_input)
            
            if observation:
                context.append({
                    "tool": action.tool,
                    "input": action.tool_input,
                    "output": observation
                })
                
                # 출처 추가
                if action.tool == "notion_search" and isinstance(observation, list):
                    for doc in observation:
                        sources.append({
                            "title": doc.get("title", ""),
                            "page_id": doc.get("page_id", ""),
                            "type": "notion"
                        })
                elif action.tool == "web_search" and isinstance(observation, list):
                    for result in observation:
                        sources.append({
                            "title": result.get("title", ""),
                            "url": result.get("link", ""),
                            "type": "web"
                        })
        
        # 최대 반복 도달 시 강제 종료
        print("⚠️ 최대 반복 횟수 도달")
        final_answer = self._generate_final_answer(question, context)
        
        return AgentResult(
            answer=final_answer,
            actions=actions,
            sources=sources
        )
    
    def _decide_next_action(self, question: str, context: List[Dict], 
                           actions: List[AgentAction]) -> Optional[AgentAction]:
        """
        LLM을 사용하여 다음 행동 결정
        
        Args:
            question: 사용자 질문
            context: 이전 실행 컨텍스트
            actions: 이전 행동 목록
        
        Returns:
            Optional[AgentAction]: 다음 행동 또는 None
        """
        # 도구 목록 포맷팅
        tools_desc = "\n".join([f"- {name}: {desc}" for name, desc in self.tools.items()])
        
        # 컨텍스트 포맷팅
        context_text = ""
        if context:
            context_text = "\n\n이전 실행 결과:\n"
            for ctx in context:
                context_text += f"도구: {ctx['tool']}\n입력: {ctx['input']}\n결과: {str(ctx['output'])[:200]}...\n\n"
        
        prompt = f"""당신은 Notion RAG 시스템의 Agent입니다. 사용자 질문에 답하기 위해 도구를 선택하고 실행합니다.

사용 가능한 도구:
{tools_desc}

사용자 질문: {question}
{context_text}

다음 형식으로 응답하세요:
Thought: [무엇을 해야 할지 생각]
Action: [도구 이름]
Action Input: [도구 입력값]

중요:
1. '추가해줘', '수정해줘', '작성해줘' → notion_append 또는 notion_create 사용
2. Notion 수정 후에는 반드시 해당 페이지를 다시 검색하여 확인
3. 충분한 정보를 얻었으면 final_answer로 종료

응답:"""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": "llama3.3:70b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            text = result.get("response", "")
            
            # 응답 파싱
            return self._parse_action(text)
        
        except Exception as e:
            print(f"❌ LLM 호출 오류: {e}")
            return None
    
    def _parse_action(self, text: str) -> Optional[AgentAction]:
        """
        LLM 응답에서 행동 파싱
        
        Args:
            text: LLM 응답 텍스트
        
        Returns:
            Optional[AgentAction]: 파싱된 행동 또는 None
        """
        try:
            # Thought 추출
            thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", text, re.DOTALL | re.IGNORECASE)
            reasoning = thought_match.group(1).strip() if thought_match else ""
            
            # Action 추출
            action_match = re.search(r"Action:\s*(\w+)", text, re.IGNORECASE)
            if not action_match:
                return None
            tool = action_match.group(1).strip()
            
            # Action Input 추출
            input_match = re.search(r"Action Input:\s*(.+?)(?=\n\n|$)", text, re.DOTALL | re.IGNORECASE)
            tool_input = input_match.group(1).strip() if input_match else ""
            
            return AgentAction(
                tool=tool,
                tool_input=tool_input,
                reasoning=reasoning
            )
        
        except Exception as e:
            print(f"⚠️ 행동 파싱 오류: {e}")
            return None
    
    def _execute_tool(self, tool: str, tool_input: str):
        """
        도구 실행
        
        Args:
            tool: 도구 이름
            tool_input: 도구 입력값
        
        Returns:
            도구 실행 결과
        """
        try:
            if tool == "notion_search":
                return self._tool_notion_search(tool_input)
            
            elif tool == "web_search":
                return self._tool_web_search(tool_input)
            
            elif tool == "notion_append":
                return self._tool_notion_append(tool_input)
            
            elif tool == "notion_create":
                return self._tool_notion_create(tool_input)
            
            else:
                print(f"⚠️ 알 수 없는 도구: {tool}")
                return None
        
        except Exception as e:
            print(f"❌ 도구 실행 오류 ({tool}): {e}")
            return None
    
    def _tool_notion_search(self, query: str) -> List[Dict]:
        """Notion 검색 도구"""
        print(f"📚 Notion 검색: {query}")
        
        try:
            # 쿼리 임베딩
            query_embedding = self.embedding_processor.embed_query_sync(query)
            
            # 벡터 검색
            results = self.vector_store.search(query_embedding, n_results=5)
            
            print(f"✅ {len(results)}개 문서 발견")
            return results
        
        except Exception as e:
            print(f"❌ Notion 검색 오류: {e}")
            return []
    
    def _tool_web_search(self, query: str) -> List[Dict]:
        """웹 검색 도구"""
        print(f"🌐 웹 검색: {query}")
        
        try:
            results = self.web_searcher.search(query, max_results=3)
            print(f"✅ {len(results)}개 결과 발견")
            return results
        
        except Exception as e:
            print(f"❌ 웹 검색 오류: {e}")
            return []
    
    def _tool_notion_append(self, tool_input: str) -> str:
        """
        Notion 페이지 내용 추가 도구
        
        입력 형식: page_id|내용
        """
        print(f"✍️ Notion 페이지 수정")
        
        try:
            parts = tool_input.split("|", 1)
            if len(parts) != 2:
                return "❌ 입력 형식 오류: page_id|내용"
            
            page_id, content = parts
            page_id = page_id.strip()
            content = content.strip()
            
            # 페이지에 내용 추가
            success = self.extractor.append_to_page(page_id, content)
            
            if not success:
                return "❌ 페이지 수정 실패"
            
            # 자동 재인덱싱
            print("🔄 페이지 재인덱싱 중...")
            self._reindex_page(page_id)
            
            return f"✅ 페이지 수정 완료 및 재인덱싱 완료"
        
        except Exception as e:
            return f"❌ 오류: {e}"
    
    def _tool_notion_create(self, tool_input: str) -> str:
        """
        새 Notion 페이지 생성 도구
        
        입력 형식: parent_id|제목|내용
        """
        print(f"📝 새 Notion 페이지 생성")
        
        try:
            parts = tool_input.split("|", 2)
            if len(parts) != 3:
                return "❌ 입력 형식 오류: parent_id|제목|내용"
            
            parent_id, title, content = parts
            parent_id = parent_id.strip()
            title = title.strip()
            content = content.strip()
            
            # 페이지 생성
            page_id = self.extractor.create_page(parent_id, title, content)
            
            if not page_id:
                return "❌ 페이지 생성 실패"
            
            # 자동 인덱싱
            print("🔄 새 페이지 인덱싱 중...")
            self._reindex_page(page_id)
            
            return f"✅ 페이지 생성 완료 (ID: {page_id}) 및 인덱싱 완료"
        
        except Exception as e:
            return f"❌ 오류: {e}"
    
    def _reindex_page(self, page_id: str) -> bool:
        """
        페이지 재인덱싱 (동기식)
        
        Args:
            page_id: 페이지 ID
        
        Returns:
            bool: 성공 여부
        """
        try:
            # 기존 청크 삭제
            self.vector_store.delete_page(page_id)
            
            # 페이지 콘텐츠 추출
            page_data = self.extractor.get_page_content(page_id)
            if not page_data:
                print(f"⚠️ 페이지 콘텐츠 추출 실패: {page_id}")
                return False
            
            # 청크 분할
            content = page_data.get("content", "")
            chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
            
            # 임베딩 생성 (동기식)
            embeddings = []
            for chunk in chunks:
                embedding = self.embedding_processor.embed_query_sync(chunk)
                embeddings.append(embedding)
            
            # ChromaDB 저장
            self.vector_store.add_chunks(
                page_id=page_id,
                title=page_data.get("title", ""),
                chunks=chunks,
                embeddings=embeddings
            )
            
            print(f"✅ 재인덱싱 완료: {page_data.get('title', page_id)} ({len(chunks)}개 청크)")
            return True
        
        except Exception as e:
            print(f"❌ 재인덱싱 오류: {e}")
            return False
    
    def _generate_final_answer(self, question: str, context: List[Dict]) -> str:
        """
        컨텍스트를 기반으로 최종 답변 생성
        
        Args:
            question: 사용자 질문
            context: 실행 컨텍스트
        
        Returns:
            str: 최종 답변
        """
        context_text = "\n\n".join([
            f"도구: {ctx['tool']}\n결과: {str(ctx['output'])[:500]}"
            for ctx in context
        ])
        
        prompt = f"""다음 정보를 바탕으로 질문에 답변하세요.

질문: {question}

수집한 정보:
{context_text}

답변:"""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": "llama3.3:70b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7}
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "답변을 생성할 수 없습니다.")
        
        except Exception as e:
            print(f"❌ 답변 생성 오류: {e}")
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {e}"
