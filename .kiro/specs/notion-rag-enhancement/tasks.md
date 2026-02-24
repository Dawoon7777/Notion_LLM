# 구현 계획: Notion RAG 시스템 고도화

## 개요

분산된 코드 구조를 `src/` 패키지 중심으로 통합하고, Incremental Sync, 병렬 임베딩, 리랭킹, Context Routing을 구현하여 RAG 시스템을 고도화한다. 각 태스크는 이전 태스크의 결과물 위에 점진적으로 구축된다.

## 태스크

- [ ] 1. 프로젝트 구조 표준화 및 ConfigManager 구현
  - [ ] 1.1 `src/`, `src/core/`, `src/api/`, `src/utils/` 디렉토리에 `__init__.py` 생성하여 Python 패키지 구조 완성
    - 각 `__init__.py`에 모듈 임포트 경로 설정
    - _Requirements: 1.1, 1.4_

  - [ ] 1.2 `src/core/config.py`에 ConfigManager 구현
    - `load_config()` 함수: 환경 변수 로드 및 필수 값(NOTION_TOKEN, OLLAMA_BASE_URL) 검증
    - 누락 시 `ValueError` + 한글 에러 메시지 (변수명 포함)
    - `OLLAMA_NUM_CTX`(기본: 32768), `OLLAMA_KEEP_ALIVE`(기본: -1), `OLLAMA_TIMEOUT`(기본: 120) 등 기본값 설정
    - `EMBEDDING_CONCURRENCY`, `EMBEDDING_MAX_RETRIES`, `SEARCH_TOP_K`, `RERANK_TOP_N`, `SYNC_INTERVAL_MINUTES`, `SYNC_STATE_PATH` 환경 변수 지원
    - `get_notion_client()` 싱글톤 함수 구현
    - _Requirements: 1.3, 1.5, 4.3, 5.5, 7.2_

  - [ ]* 1.3 ConfigManager 속성 기반 테스트 작성
    - **Property 1: 필수 환경 변수 누락 시 ValueError 발생**
    - **Validates: Requirements 1.5**

  - [ ]* 1.4 ConfigManager 속성 기반 테스트 작성
    - **Property 7: 환경 변수 설정 Round-Trip**
    - **Validates: Requirements 4.3, 5.5, 7.2**

  - [ ] 1.5 루트 `main.py`, `api.py`, `scheduler.py`를 `src` 모듈 호출 래퍼로 리팩토링
    - 기존 비즈니스 로직 제거, `src.core` 및 `src.api` 모듈 임포트로 대체
    - 루트 `config.py` 제거 (또는 `src.core.config` 임포트 래퍼로 변환)
    - _Requirements: 1.2, 1.3_

  - [ ] 1.6 `.env.example` 파일에 신규 환경 변수 추가
    - 모든 설정 가능한 환경 변수와 기본값 주석 포함
    - _Requirements: 4.3, 5.5, 7.2_

- [ ] 2. 체크포인트 - 프로젝트 구조 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의

- [ ] 3. IncrementalSyncEngine 구현
  - [ ] 3.1 `src/core/incremental_sync.py`에 IncrementalSyncEngine 클래스 구현
    - `SyncResult` 데이터클래스 정의 (added, modified, deleted, elapsed_seconds)
    - `load_state()`: sync_state.json 로드, 파일 없거나 손상 시 빈 dict 반환
    - `save_state()`: 동기화 상태를 sync_state.json에 저장
    - `detect_changes(current, saved)`: 변경 사항 감지 (added, modified, deleted 반환)
    - `sync()`: 증분 동기화 실행 (상태 파일 없으면 전체 재인덱싱)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 3.2 `src/core/notion_extractor.py`에 `get_pages_with_timestamps()` 메서드 추가
    - 모든 페이지의 `{page_id: last_edited_time}` 매핑 반환
    - 기존 `search_all_pages()`, `get_page_content()` 유지
    - _Requirements: 2.1, 2.2_

  - [ ]* 3.3 IncrementalSyncEngine 속성 기반 테스트 작성
    - **Property 2: 동기화 상태 Round-Trip**
    - **Validates: Requirements 2.1**

  - [ ]* 3.4 IncrementalSyncEngine 속성 기반 테스트 작성
    - **Property 3: 변경 감지 정확성**
    - **Validates: Requirements 2.2, 2.4, 2.5**

  - [ ]* 3.5 IncrementalSyncEngine 속성 기반 테스트 작성
    - **Property 4: 손상된 상태 파일 처리**
    - **Validates: Requirements 2.6**

- [ ] 4. EmbeddingProcessor 구현
  - [ ] 4.1 `src/core/embedding_processor.py` 생성
    - `EmbeddingResult` 데이터클래스 정의
    - `EmbeddingProcessor` 클래스: asyncio + aiohttp 기반 병렬 임베딩
    - `embed_texts()`: Semaphore로 동시 요청 수 제한, 병렬 처리
    - `embed_single()`: 단일 텍스트 임베딩, 최대 3회 재시도 (지수 백오프)
    - `embed_query_sync()`: 동기식 단일 쿼리 임베딩
    - 처리 완료 시 처리/실패 청크 수, 소요 시간 로그 출력
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.2 EmbeddingProcessor 속성 기반 테스트 작성
    - **Property 5: 임베딩 처리 결과 무결성**
    - **Validates: Requirements 3.3, 3.5**

  - [ ]* 4.3 EmbeddingProcessor 속성 기반 테스트 작성
    - **Property 6: 재시도 로직 동작**
    - **Validates: Requirements 3.4, 4.4**

- [ ] 5. VectorStoreManager 구현
  - [ ] 5.1 `src/core/vector_store.py` 생성
    - `VectorStoreManager` 클래스: ChromaDB 관리
    - `add_chunks()`: 청크와 임베딩을 ChromaDB에 저장 (page_id, title, chunk_index, last_edited_time 메타데이터)
    - `delete_page()`: 페이지의 모든 청크 삭제, 삭제된 청크 수 반환
    - `search()`: 벡터 유사도 검색, distance 포함
    - `get_collection_stats()`: 컬렉션 통계 반환
    - _Requirements: 2.3, 2.4, 2.5_

  - [ ]* 5.2 VectorStoreManager 단위 테스트 작성
    - 청크 추가/삭제/검색 동작 검증
    - 빈 컬렉션 통계 조회
    - _Requirements: 2.3, 2.4, 2.5_

- [ ] 6. 체크포인트 - 핵심 인프라 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의

- [ ] 7. Reranker 구현
  - [ ] 7.1 `src/core/reranker.py` 생성
    - `RankedDocument` 데이터클래스 정의 (content, title, page_id, relevance_score)
    - `Reranker` 클래스: sentence-transformers CrossEncoder 기반
    - `rerank()`: 문서를 relevance_score 기준 내림차순 정렬, 상위 N개 반환
    - 리랭커 실패 시 원래 검색 결과 사용 (graceful degradation)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 7.2 Reranker 속성 기반 테스트 작성
    - **Property 8: 리랭킹 결과 정렬 및 Score 존재**
    - **Validates: Requirements 5.1, 5.3**

  - [ ]* 7.3 Reranker 속성 기반 테스트 작성
    - **Property 9: 리랭킹 결과 수 제한**
    - **Validates: Requirements 5.2**

- [ ] 8. ContextRouter 구현
  - [ ] 8.1 `src/core/context_router.py` 생성
    - `QuestionCategory` Enum 정의 (INTERNAL_DOC, LATEST_INFO, GENERAL_KNOWLEDGE)
    - `RoutingDecision` 데이터클래스 정의 (category, use_notion, use_web, notion_weight, web_weight)
    - `ContextRouter` 클래스: LLM 기반 질문 의도 분류
    - `classify()`: Ollama LLM을 사용하여 질문 분류 및 라우팅 결정 반환
    - LLM 분류 실패 시 기본값 `INTERNAL_DOC`으로 폴백
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ]* 8.2 ContextRouter 속성 기반 테스트 작성
    - **Property 10: Context Routing 카테고리별 가중치 일관성**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ] 9. QAEngine 구현
  - [ ] 9.1 `src/core/qa_engine.py` 생성
    - `AnswerResult` 데이터클래스 정의 (answer, sources, source_type, category)
    - `QAEngine` 클래스: VectorStore + Reranker + ContextRouter + WebSearcher 통합
    - `answer()`: Context Routing → 검색 → 리랭킹 → LLM 답변 파이프라인
    - `use_reranking` 파라미터로 리랭킹 사용 여부 선택 가능
    - Ollama API 호출 시 `num_ctx`, `keep_alive`, 타임아웃 설정 적용
    - 답변에 사용된 정보 출처(source_type) 포함
    - _Requirements: 4.1, 4.2, 4.5, 5.4, 6.2, 6.3, 6.4, 6.5, 8.3_

  - [ ]* 9.2 QAEngine 속성 기반 테스트 작성
    - **Property 11: 답변 결과 출처 유효성**
    - **Validates: Requirements 6.5**

- [ ] 10. 체크포인트 - 핵심 비즈니스 로직 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의

- [ ] 11. FastAPI 서버 확장 및 스케줄러 통합
  - [ ] 11.1 `src/api/server.py` 확장
    - 기존 엔드포인트 유지 및 `src.core` 모듈 사용으로 리팩토링
    - `POST /sync`: Incremental Sync 수동 트리거 엔드포인트 추가
    - `GET /sync/status`: 마지막 동기화 상태 조회 엔드포인트 추가
    - `POST /query`에 `use_reranking` 파라미터 추가
    - 모든 응답을 `{"status": "success/error", "message": "...", ...}` 형식으로 통일
    - 예외 발생 시 적절한 HTTP 상태 코드 + 한글 에러 메시지 반환
    - Pydantic 모델 정의 (QueryRequest, QueryResponse, SyncResponse, SyncStatusResponse)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 11.2 FastAPI 엔드포인트 속성 기반 테스트 작성
    - **Property 12: API 응답 형식 통일**
    - **Validates: Requirements 8.4**

  - [ ] 11.3 `src/core/scheduler.py` 리팩토링 및 Incremental Sync 통합
    - APScheduler를 사용하여 설정된 주기에 따라 IncrementalSyncEngine 자동 실행
    - 실행 주기를 `SYNC_INTERVAL_MINUTES` 환경 변수로 설정
    - 동기화 결과(추가/수정/삭제 페이지 수, 소요 시간) 로그 출력
    - 오류 발생 시 에러 로그 기록, 다음 실행 시점에 재시도
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 12. 테스트 인프라 및 통합 테스트
  - [ ] 12.1 `tests/conftest.py` 생성
    - 공통 fixture 정의: 모킹된 Notion 클라이언트, Ollama 응답, ChromaDB 인스턴스
    - 임시 파일/디렉토리 fixture
    - 환경 변수 fixture
    - _Requirements: 전체_

  - [ ]* 12.2 통합 테스트 작성 (`tests/test_api.py`)
    - FastAPI TestClient를 사용한 엔드포인트 통합 테스트
    - POST /sync, GET /sync/status 동작 검증
    - POST /query의 use_reranking 파라미터 동작 검증
    - 에러 응답 형식 검증
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 13. 최종 체크포인트 - 전체 시스템 검증
  - 모든 테스트 통과 확인, 질문이 있으면 사용자에게 문의

## 참고 사항

- `*` 표시된 태스크는 선택 사항이며 빠른 MVP를 위해 건너뛸 수 있음
- 각 태스크는 특정 요구사항을 참조하여 추적 가능
- 체크포인트에서 점진적 검증 수행
- 속성 기반 테스트는 설계 문서의 정확성 속성을 검증
- 단위 테스트는 구체적인 예시와 엣지 케이스를 검증
