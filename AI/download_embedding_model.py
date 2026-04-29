# 임베딩 모델 관리
import os
import sys
from config import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_PATH, EMBEDDING_DIM


class EmbeddingModelManager:
    """BAAI/bge-m3 임베딩 모델 다운로드 및 관리"""

    @staticmethod
    def download_model():
        """모델 로드 (로컬 캐시 우선, 없으면 HuggingFace 다운로드)"""
        # ✅ lazy import: 이 함수가 실제로 호출될 때만 torch/sentence_transformers 로드
        print(f"📥 sentence_transformers 로드 중... (시간 걸릴 수 있음)", flush=True)
        from sentence_transformers import SentenceTransformer
        print(f"✅ sentence_transformers 로드 완료", flush=True)

        print(f"📥 임베딩 모델 로드 중: {EMBEDDING_MODEL_NAME}", flush=True)
        print(f"📍 저장 경로: {EMBEDDING_MODEL_PATH}", flush=True)

        if os.path.exists(EMBEDDING_MODEL_PATH):
            print("✅ 로컬 모델 발견 → 로드 중...", flush=True)
            model = SentenceTransformer(EMBEDDING_MODEL_PATH)
        else:
            print("🌐 HuggingFace에서 다운로드 중... (~500MB, 수 분 소요)", flush=True)
            model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            os.makedirs(os.path.dirname(EMBEDDING_MODEL_PATH), exist_ok=True)
            model.save(EMBEDDING_MODEL_PATH)
            print(f"✅ 모델 저장 완료: {EMBEDDING_MODEL_PATH}", flush=True)

        actual_dim = model.get_sentence_embedding_dimension()
        if actual_dim != EMBEDDING_DIM:
            print(f"⚠️  실제 차원: {actual_dim} (config.EMBEDDING_DIM={EMBEDDING_DIM})", flush=True)

        print(f"✅ 모델 로드 완료 ({actual_dim}차원)", flush=True)
        return model

    @staticmethod
    def check_model_exists() -> bool:
        exists = os.path.exists(EMBEDDING_MODEL_PATH)
        print(f"{'✅ 설치됨' if exists else '⬜ 미설치'}: {EMBEDDING_MODEL_PATH}")
        return exists

    @staticmethod
    def get_model_size() -> str:
        if not os.path.exists(EMBEDDING_MODEL_PATH):
            return "미설치"
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(EMBEDDING_MODEL_PATH)
            for f in files
        )
        return f"{total / (1024 * 1024):.2f} MB"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "download"
    if cmd == "status":
        EmbeddingModelManager.check_model_exists()
        print(f"크기: {EmbeddingModelManager.get_model_size()}")
    else:
        EmbeddingModelManager.download_model()