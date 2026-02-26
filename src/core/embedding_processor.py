"""
병렬 임베딩 처리 모듈

asyncio + aiohttp를 사용하여 여러 텍스트 청크를 병렬로 임베딩합니다.
"""

import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EmbeddingResult:
    """임베딩 처리 결과"""
    embeddings: List[List[float]]  # 성공한 임베딩 벡터
    failed_indices: List[int]      # 실패한 청크 인덱스
    total_count: int
    success_count: int
    elapsed_seconds: float


class EmbeddingProcessor:
    """
    병렬 임베딩 처리기
    
    asyncio와 aiohttp를 사용하여 여러 텍스트를 병렬로 임베딩합니다.
    """
    
    def __init__(self, base_url: str, model: str = "bge-m3",
                 concurrency: int = 8, max_retries: int = 3):
        """
        Args:
            base_url: Ollama 서버 URL
            model: 임베딩 모델 이름
            concurrency: 동시 요청 수 제한
            max_retries: 최대 재시도 횟수
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(concurrency)
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """
        여러 텍스트를 병렬로 임베딩
        
        Args:
            texts: 임베딩할 텍스트 목록
        
        Returns:
            EmbeddingResult: 임베딩 결과
        """
        start_time = time.time()
        total_count = len(texts)
        
        print(f"🔄 임베딩 시작: {total_count}개 청크 (동시성: {self.concurrency})")
        
        # 병렬 임베딩 실행
        tasks = [self._embed_with_semaphore(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 분리
        embeddings = []
        failed_indices = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception) or result is None:
                failed_indices.append(i)
                print(f"⚠️ 청크 {i} 임베딩 실패")
            else:
                embeddings.append(result)
        
        success_count = len(embeddings)
        elapsed = time.time() - start_time
        
        print(f"✅ 임베딩 완료: 성공 {success_count}/{total_count}, "
              f"실패 {len(failed_indices)}, 소요 시간 {elapsed:.2f}초")
        
        return EmbeddingResult(
            embeddings=embeddings,
            failed_indices=failed_indices,
            total_count=total_count,
            success_count=success_count,
            elapsed_seconds=elapsed
        )
    
    async def _embed_with_semaphore(self, index: int, text: str) -> Optional[List[float]]:
        """
        Semaphore를 사용하여 동시 요청 수 제한
        
        Args:
            index: 청크 인덱스
            text: 임베딩할 텍스트
        
        Returns:
            Optional[List[float]]: 임베딩 벡터 또는 None
        """
        async with self.semaphore:
            return await self.embed_single(text)
    
    async def embed_single(self, text: str) -> Optional[List[float]]:
        """
        단일 텍스트 임베딩 (재시도 로직 포함)
        
        Args:
            text: 임베딩할 텍스트
        
        Returns:
            Optional[List[float]]: 임베딩 벡터 또는 None
        """
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{self.base_url}/api/embeddings"
                    payload = {
                        "model": self.model,
                        "prompt": text
                    }
                    
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("embedding")
                        else:
                            error_text = await response.text()
                            print(f"⚠️ Ollama API 오류 (시도 {attempt + 1}/{self.max_retries}): "
                                  f"상태 {response.status}, {error_text[:100]}")
            
            except asyncio.TimeoutError:
                print(f"⚠️ 타임아웃 (시도 {attempt + 1}/{self.max_retries})")
            except Exception as e:
                print(f"⚠️ 임베딩 오류 (시도 {attempt + 1}/{self.max_retries}): {e}")
            
            # 재시도 전 대기 (지수 백오프)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt  # 1초, 2초, 4초
                await asyncio.sleep(wait_time)
        
        return None
    
    def embed_query_sync(self, text: str) -> List[float]:
        """
        동기식 단일 쿼리 임베딩 (검색 시 사용)
        
        Args:
            text: 임베딩할 텍스트
        
        Returns:
            List[float]: 임베딩 벡터
        
        Raises:
            Exception: 임베딩 실패 시
        """
        import requests
        
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding")
            
            except requests.exceptions.Timeout:
                print(f"⚠️ 타임아웃 (시도 {attempt + 1}/{self.max_retries})")
            except Exception as e:
                print(f"⚠️ 임베딩 오류 (시도 {attempt + 1}/{self.max_retries}): {e}")
            
            # 재시도 전 대기
            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)
        
        raise Exception("❌ 임베딩 생성 실패: 최대 재시도 횟수 초과")
