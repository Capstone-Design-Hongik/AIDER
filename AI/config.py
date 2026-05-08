import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
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

# Embedding (OpenAI API — 메모리 0, 한국어 우수)
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
EMBEDDING_DIM        = 512  # 256/512/1024/1536 가능. 512가 비용·성능 균형

# RAG
RAG_K_DEFAULT              = 5
SEARCH_SCORE_THRESHOLD     = 0.5
SEARCH_CONFIDENCE_THRESHOLD = 0.70

# YouTube Proxy — YOUTUBE_PROXY 환경변수 (YouTube 요청에만 적용)
# 형식: http://user:pass@host:port
# Railway Variables 또는 .env 파일에 설정 (HTTPS_PROXY 사용 금지 — 시스템 전체에 영향)