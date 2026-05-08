# OpenAI 임베딩 래퍼 — SentenceTransformer 호환 인터페이스
import os
import sys
from typing import List, Union
from config import EMBEDDING_MODEL_NAME, EMBEDDING_DIM


class OpenAIEmbedder:
    """OpenAI Embeddings API 래퍼.
    ChromaDBManager가 기대하는 인터페이스(.encode, .get_sentence_embedding_dimension) 제공.
    """

    def __init__(self, model: str = EMBEDDING_MODEL_NAME, dimensions: int = EMBEDDING_DIM):
        self.model = model
        self.dimensions = dimensions
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client

    def encode(self, text: Union[str, List[str]]) -> List[float]:
        """단일 문자열 → 1D 임베딩 벡터(list[float]). 리스트 입력 → 2D(list[list[float]])."""
        is_single = isinstance(text, str)
        inputs = [text] if is_single else list(text)
        # 빈 문자열 방어
        inputs = [t if t and t.strip() else " " for t in inputs]

        resp = self._get_client().embeddings.create(
            model=self.model,
            input=inputs,
            dimensions=self.dimensions,
        )
        vectors = [d.embedding for d in resp.data]
        return vectors[0] if is_single else vectors

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimensions


class EmbeddingModelManager:
    """OpenAI 임베딩 사용 — 다운로드 불필요, 즉시 사용 가능."""

    @staticmethod
    def download_model() -> OpenAIEmbedder:
        print(f"📥 임베딩 모델 초기화: {EMBEDDING_MODEL_NAME} ({EMBEDDING_DIM}차원, OpenAI API)", flush=True)
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY 환경변수가 필요합니다")
        embedder = OpenAIEmbedder()
        print(f"✅ 임베딩 준비 완료 (메모리 사용량 0, 네트워크 호출 방식)", flush=True)
        return embedder

    @staticmethod
    def check_model_exists() -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    @staticmethod
    def get_model_size() -> str:
        return "0 MB (API)"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "download"
    if cmd == "status":
        ok = EmbeddingModelManager.check_model_exists()
        print(f"{'✅ 사용 가능' if ok else '❌ OPENAI_API_KEY 누락'}: {EMBEDDING_MODEL_NAME}")
        print(f"크기: {EmbeddingModelManager.get_model_size()}")
    else:
        EmbeddingModelManager.download_model()
