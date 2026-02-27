"""
질문 의도 라우팅 모듈

LLM을 사용하여 질문을 분류하고 정보 소스 우선순위를 결정합니다.
"""

from dataclasses import dataclass
from enum import Enum
import requests


class QuestionCategory(Enum):
    """질문 카테고리"""
    INTERNAL_DOC = "내부 문서 질문"
    LATEST_INFO = "최신 정보 질문"
    GENERAL_KNOWLEDGE = "일반 지식 질문"


@dataclass
class RoutingDecision:
    """라우팅 결정"""
    category: QuestionCategory
    use_notion: bool
    use_web: bool
    notion_weight: float  # 0.0 ~ 1.0
    web_weight: float     # 0.0 ~ 1.0


class ContextRouter:
    """
    질문 의도 라우팅
    
    LLM을 사용하여 질문을 분류하고 정보 소스 우선순위를 결정합니다.
    """
    
    def __init__(self, base_url: str, model: str = "llama3.3:70b"):
        """
        Args:
            base_url: Ollama 서버 URL
            model: LLM 모델 이름
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
    
    def classify(self, question: str) -> RoutingDecision:
        """
        질문 의도를 분류하고 라우팅 결정 반환
        
        Args:
            question: 사용자 질문
        
        Returns:
            RoutingDecision: 라우팅 결정
        """
        try:
            # LLM을 사용하여 질문 분류
            category = self._classify_question(question)
            
            # 카테고리별 라우팅 결정
            if category == QuestionCategory.INTERNAL_DOC:
                return RoutingDecision(
                    category=category,
                    use_notion=True,
                    use_web=False,
                    notion_weight=1.0,
                    web_weight=0.0
                )
            
            elif category == QuestionCategory.LATEST_INFO:
                return RoutingDecision(
                    category=category,
                    use_notion=True,
                    use_web=True,
                    notion_weight=0.3,
                    web_weight=0.7
                )
            
            else:  # GENERAL_KNOWLEDGE
                return RoutingDecision(
                    category=category,
                    use_notion=True,
                    use_web=False,
                    notion_weight=0.2,
                    web_weight=0.0
                )
        
        except Exception as e:
            print(f"⚠️ 질문 분류 실패: {e}")
            print("⚠️ 기본값 INTERNAL_DOC으로 폴백")
            
            # 분류 실패 시 기본값 반환
            return RoutingDecision(
                category=QuestionCategory.INTERNAL_DOC,
                use_notion=True,
                use_web=False,
                notion_weight=1.0,
                web_weight=0.0
            )
    
    def _classify_question(self, question: str) -> QuestionCategory:
        """
        LLM을 사용하여 질문 분류
        
        Args:
            question: 사용자 질문
        
        Returns:
            QuestionCategory: 질문 카테고리
        """
        try:
            url = f"{self.base_url}/api/generate"
            
            prompt = f"""다음 질문을 분류하세요. 정확히 하나의 카테고리만 선택하세요.

질문: {question}

카테고리:
1. 내부문서 - 회사/프로젝트 내부 문서, 업무 관련 질문
2. 최신정보 - 최근 뉴스, 실시간 정보, 날씨, 주가 등
3. 일반지식 - 일반적인 지식, 개념 설명, 역사적 사실 등

답변은 "내부문서", "최신정보", "일반지식" 중 하나만 출력하세요.

분류:"""
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            classification = result.get("response", "").strip().lower()
            
            # 분류 결과 매핑
            if "내부" in classification or "문서" in classification:
                return QuestionCategory.INTERNAL_DOC
            elif "최신" in classification or "정보" in classification:
                return QuestionCategory.LATEST_INFO
            elif "일반" in classification or "지식" in classification:
                return QuestionCategory.GENERAL_KNOWLEDGE
            else:
                # 매핑 실패 시 기본값
                return QuestionCategory.INTERNAL_DOC
        
        except Exception as e:
            print(f"⚠️ LLM 분류 오류: {e}")
            return QuestionCategory.INTERNAL_DOC
