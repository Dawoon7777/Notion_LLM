# 요구사항 문서

## 소개

Notion RAG 시스템 고도화 프로젝트이다. 현재 분산된 코드 구조를 표준화하고, RTX 3090 x4 (96GB VRAM) 환경에 최적화된 인덱싱 파이프라인을 구축하며, 하이브리드 검색과 리랭커를 도입하여 답변 품질을 엔터프라이즈 수준으로 향상시킨다.

현재 시스템의 주요 문제점:
- 루트(`main.py`, `api.py`, `config.py`)와 `src/` 디렉토리에 동일한 코드가 중복 존재
- 인덱싱 시 모든 페이지를 매번 전체 재처리 (Incremental Sync 미지원)
- 임베딩 생성이 동기식 순차 처리로 병목 발생
- 단순 벡터 유사도 검색만 사용하여 정확도 한계
- 웹 검색과 Notion 문서 간 우선순위 라우팅 로직 부재

## 용어 사전

- **RAG_System**: Notion 문서와 웹 검색 결과를 활용하여 질문에 답변하는 Retrieval-Augmented Generation 시스템
- **Indexer**: Notion 페이지를 추출하고 임베딩하여 ChromaDB에 저장하는 인덱싱 모듈
- **Incremental_Sync_Engine**: Notion API의 last_edited_time을 기반으로 변경된 페이지만 선별하여 인덱싱하는 엔진
- **Embedding_Processor**: bge-m3 모델을 사용하여 텍스트 청크를 벡터로 변환하는 임베딩 처리기
- **Vector_Store**: ChromaDB를 사용한 벡터 저장소 관리 모듈
- **Reranker**: bge-reranker-v2-m3 모델을 사용하여 검색 결과를 재정렬하는 리랭킹 모듈
- **Context_Router**: 질문 의도를 분석하여 Notion 문서와 웹 검색 결과의 우선순위를 결정하는 라우팅 모듈
- **Config_Manager**: 환경 변수 로드 및 검증을 중앙 집중화하는 설정 관리 모듈
- **Scheduler**: 주기적으로 Notion 페이지 변경 사항을 감지하고 인덱싱을 수행하는 스케줄러

## 요구사항

### 요구사항 1: 프로젝트 구조 표준화 및 패키지화

**사용자 스토리:** 개발자로서, 분산된 코드를 단일 패키지 구조로 통합하여, 유지보수성과 코드 재사용성을 확보하고 싶다.

#### 인수 조건

1. THE RAG_System SHALL 모든 핵심 비즈니스 로직을 `src/` 디렉토리 내부의 Python 패키지로 구성한다
2. THE RAG_System SHALL 루트의 `main.py`와 `api.py`를 `src` 모듈을 호출하는 래퍼(Wrapper) 역할로만 유지한다
3. THE Config_Manager SHALL 환경 변수 로드 로직을 `src/core/config.py` 하나로 중앙 집중화하여 중복된 `config.py`를 제거한다
4. THE RAG_System SHALL `src/` 디렉토리에 `__init__.py` 파일을 포함하여 올바른 Python 패키지 구조를 갖춘다
5. WHEN 환경 변수가 누락된 경우, THE Config_Manager SHALL `ValueError`와 함께 누락된 변수명을 포함한 한글 에러 메시지를 반환한다

### 요구사항 2: Incremental Sync 구현

**사용자 스토리:** 운영자로서, 변경된 페이지만 선별적으로 인덱싱하여, 불필요한 전체 재인덱싱을 방지하고 처리 시간을 단축하고 싶다.

#### 인수 조건

1. THE Incremental_Sync_Engine SHALL 각 Notion 페이지의 `last_edited_time`을 로컬에 저장한다
2. WHEN 인덱싱이 실행될 때, THE Incremental_Sync_Engine SHALL 저장된 `last_edited_time`과 현재 Notion API에서 조회한 `last_edited_time`을 비교하여 변경된 페이지만 식별한다
3. WHEN 변경된 페이지가 식별되면, THE Indexer SHALL 해당 페이지만 ChromaDB에서 삭제 후 재인덱싱한다
4. WHEN 새로 생성된 페이지가 발견되면, THE Indexer SHALL 해당 페이지를 ChromaDB에 추가한다
5. WHEN Notion에서 삭제된 페이지가 감지되면, THE Indexer SHALL 해당 페이지의 모든 청크를 ChromaDB에서 제거한다
6. IF `last_edited_time` 저장 파일이 손상되거나 존재하지 않는 경우, THEN THE Incremental_Sync_Engine SHALL 전체 재인덱싱을 수행하고 새로운 저장 파일을 생성한다

### 요구사항 3: 병렬 임베딩 처리

**사용자 스토리:** 운영자로서, 대량의 텍스트 청크를 병렬로 임베딩하여, RTX 3090 x4 환경에서 인덱싱 속도를 극대화하고 싶다.

#### 인수 조건

1. THE Embedding_Processor SHALL asyncio를 사용하여 여러 텍스트 청크의 임베딩 생성을 병렬로 처리한다
2. THE Embedding_Processor SHALL 동시 임베딩 요청 수를 설정 가능한 값으로 제한하여 Ollama 서버 과부하를 방지한다
3. IF 개별 청크의 임베딩 생성이 실패한 경우, THEN THE Embedding_Processor SHALL 해당 청크를 건너뛰고 나머지 청크의 처리를 계속한다
4. THE Embedding_Processor SHALL 임베딩 생성 실패 시 최대 3회까지 재시도한다
5. WHEN 임베딩 처리가 완료되면, THE Embedding_Processor SHALL 처리된 청크 수, 실패한 청크 수, 소요 시간을 로그로 출력한다

### 요구사항 4: Ollama 설정 최적화

**사용자 스토리:** 운영자로서, RTX 3090 x4의 96GB VRAM을 충분히 활용하도록 Ollama 설정을 최적화하여, LLM 응답 품질과 속도를 향상시키고 싶다.

#### 인수 조건

1. THE RAG_System SHALL Ollama API 호출 시 `num_ctx` 파라미터를 최소 32768 이상으로 설정한다
2. THE RAG_System SHALL Ollama API 호출 시 `keep_alive` 파라미터를 -1로 설정하여 모델 상주 상태를 유지한다
3. THE Config_Manager SHALL `num_ctx`, `keep_alive` 값을 환경 변수로 설정 가능하게 한다
4. WHEN Ollama 서버 연결이 실패한 경우, THE RAG_System SHALL 최대 3회까지 재시도하며 각 재시도 간 대기 시간을 점진적으로 증가시킨다
5. THE RAG_System SHALL Ollama API 호출에 타임아웃을 설정한다

### 요구사항 5: Reranking 파이프라인 도입

**사용자 스토리:** 사용자로서, 검색 결과의 정확도를 높여, 질문에 가장 관련성 높은 문서를 기반으로 답변을 받고 싶다.

#### 인수 조건

1. THE Reranker SHALL ChromaDB에서 검색된 Top-k 결과를 bge-reranker-v2-m3 모델을 통해 재정렬한다
2. THE Reranker SHALL 재정렬 후 상위 N개의 문서만 LLM 컨텍스트로 전달한다
3. THE Reranker SHALL 각 문서에 대해 relevance score를 산출한다
4. WHEN Reranker 모델 호출이 실패한 경우, THE RAG_System SHALL 리랭킹 없이 원래 ChromaDB 검색 결과를 사용하여 답변을 생성한다
5. THE Config_Manager SHALL 초기 검색 결과 수(Top-k)와 리랭킹 후 최종 결과 수(Top-N)를 환경 변수로 설정 가능하게 한다

### 요구사항 6: Context Routing 구현

**사용자 스토리:** 사용자로서, 질문의 의도에 따라 Notion 문서와 웹 검색 결과를 적절히 활용한 답변을 받고 싶다.

#### 인수 조건

1. THE Context_Router SHALL 질문을 분석하여 "내부 문서 질문", "최신 정보 질문", "일반 지식 질문" 중 하나로 분류한다
2. WHEN 질문이 "내부 문서 질문"으로 분류되면, THE Context_Router SHALL Notion 문서 검색 결과를 최우선으로 사용한다
3. WHEN 질문이 "최신 정보 질문"으로 분류되면, THE Context_Router SHALL 웹 검색 결과를 우선적으로 사용하고 Notion 문서로 보충한다
4. WHEN 질문이 "일반 지식 질문"으로 분류되면, THE Context_Router SHALL LLM의 기본 지식을 활용하되 관련 Notion 문서가 있으면 참고한다
5. THE Context_Router SHALL 답변 생성 시 사용된 정보 출처(Notion, 웹, 일반 지식)를 응답에 포함한다

### 요구사항 7: Incremental Sync 스케줄러 통합

**사용자 스토리:** 운영자로서, Incremental Sync가 스케줄러와 통합되어 자동으로 변경 사항을 감지하고 인덱싱하여, 수동 개입 없이 최신 상태를 유지하고 싶다.

#### 인수 조건

1. THE Scheduler SHALL 설정된 주기에 따라 Incremental_Sync_Engine을 자동으로 실행한다
2. THE Scheduler SHALL 실행 주기를 환경 변수로 설정 가능하게 한다
3. WHEN 자동 인덱싱이 완료되면, THE Scheduler SHALL 동기화 결과(추가/수정/삭제된 페이지 수, 소요 시간)를 로그로 출력한다
4. IF 자동 인덱싱 중 오류가 발생한 경우, THEN THE Scheduler SHALL 오류를 로그에 기록하고 다음 예정된 실행 시점에 재시도한다

### 요구사항 8: API 엔드포인트 확장

**사용자 스토리:** 개발자로서, 고도화된 기능(Incremental Sync, Reranking, Context Routing)을 API를 통해 제어하고 모니터링하고 싶다.

#### 인수 조건

1. THE RAG_System SHALL Incremental Sync를 수동으로 트리거하는 API 엔드포인트를 제공한다
2. THE RAG_System SHALL 마지막 동기화 상태(시간, 변경된 페이지 수)를 조회하는 API 엔드포인트를 제공한다
3. THE RAG_System SHALL 쿼리 요청 시 리랭킹 사용 여부를 선택할 수 있는 파라미터를 제공한다
4. THE RAG_System SHALL 모든 API 응답을 `{"status": "success/error", "message": "...", ...}` 형식으로 통일한다
5. IF API 요청 처리 중 예외가 발생한 경우, THEN THE RAG_System SHALL 적절한 HTTP 상태 코드와 한글 에러 메시지를 반환한다
