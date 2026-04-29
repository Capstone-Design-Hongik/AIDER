import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")   # 더 이상 사용 안 함 (보존만)
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")


class LLMConfig:
    """
    비용 절감 전략:
    - Agent 의사결정 / 분석 → gpt-4o-mini  (저렴, 빠름)
    - 최종 조언 생성       → gpt-4o        (품질 중요한 한 곳만)
    """

    # 저비용 모델 (Agent 의사결정, 사용자 분석, 자막 분석)
    CHEAP_MODEL = "gpt-4o-mini"        # $0.15 / 1M input tokens

    # 품질 모델 (최종 조언만 사용)
    QUALITY_MODEL = "gpt-4o"           # $2.50 / 1M input tokens

    # 하위 호환 alias
    AGENT_MODEL        = CHEAP_MODEL
    ANALYSIS_MODEL     = CHEAP_MODEL
    FINAL_ADVICE_MODEL = QUALITY_MODEL


# Vector DB
VECTOR_DB_PATH = "./chroma_db"

# Embedding (BAAI/bge-m3 로컬)
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_MODEL_PATH = "./models/bge-m3"
EMBEDDING_DIM        = 1024

# RAG
RAG_K_DEFAULT              = 5
RAG_K_MAX                  = 10
SEARCH_SCORE_THRESHOLD     = 0.5
SEARCH_CONFIDENCE_THRESHOLD = 0.70