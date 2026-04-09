# vector_db/chroma_client.py
import os
from typing import List, Optional
from langchain_core.documents import Document
import chromadb
from chromadb import PersistentClient

# ── 설정 ────────────────────────────────────────────────────────────────
LOCAL_MODEL_DIR = "./local_model"       # download_model.py 로 내려받은 경로
REMOTE_MODEL_ID = "BAAI/bge-m3"         # 대체 모델 (Jina → BGE-M3로 변경)

# MRL은 폐기했으므로 고정 차원 사용
EMBEDDING_DIM = 1024                    # BGE-M3 기본 차원

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "youtube_strategy"

# ── 임베딩 모델 로드 (싱글톤) ────────────────────────────────────────────
_embed_model = None

def _get_embed_model():
    """BGE-M3 모델을 싱글톤으로 로드"""
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    from sentence_transformers import SentenceTransformer

    model_path = LOCAL_MODEL_DIR if os.path.isdir(LOCAL_MODEL_DIR) else REMOTE_MODEL_ID
    print(f"[ChromaClient] 임베딩 모델 로드: {model_path}")

    _embed_model = SentenceTransformer(
        model_path,
        trust_remote_code=True,
    )
    print(f"[ChromaClient] ✅ 모델 로드 완료 (차원: {EMBEDDING_DIM})")
    return _embed_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    텍스트 목록을 임베딩으로 변환
    
    Args:
        texts: 변환할 텍스트 리스트
    
    Returns:
        List[List[float]]: 임베딩 벡터 리스트
    """
    model = _get_embed_model()
    print(f"[ChromaClient] {len(texts)}개 텍스트 임베딩 중...")
    embeddings = model.encode(texts, convert_to_tensor=False)
    
    # numpy array를 list로 변환
    if hasattr(embeddings, 'tolist'):
        embeddings = embeddings.tolist()
    
    print(f"[ChromaClient] ✅ 임베딩 완료")
    return embeddings


# ── ChromaDB 클라이언트 ──────────────────────────────────────────────────
_chroma_client: Optional[PersistentClient] = None
_collection = None


def get_chroma_client() -> PersistentClient:
    """ChromaDB 클라이언트 싱글톤"""
    global _chroma_client
    if _chroma_client is None:
        print(f"[ChromaClient] ChromaDB 초기화: {CHROMA_PATH}")
        _chroma_client = PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def get_collection():
    """YouTube 자막 컬렉션 가져오기"""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "YouTube 투자 전략 영상 자막 저장소"},
        )
    return _collection


def video_exists(video_id: str) -> bool:
    """특정 video_id의 데이터가 DB에 존재하는지 확인"""
    collection = get_collection()
    try:
        result = collection.get(
            where={"video_id": video_id},
            limit=1
        )
        exists = bool(result and result.get('ids'))
        if exists:
            print(f"[ChromaClient] 캐시 히트: {video_id} ✅")
        return exists
    except Exception as e:
        print(f"[ChromaClient] 캐시 확인 실패: {e}")
        return False


def add_documents(documents: List[Document], video_id: str) -> int:
    """
    문서를 ChromaDB에 추가
    
    Args:
        documents: LangChain Document 리스트
        video_id: YouTube 영상 ID
    
    Returns:
        추가된 문서 수
    """
    if not documents:
        print("[ChromaClient] 추가할 문서가 없습니다.")
        return 0

    collection = get_collection()
    
    # 텍스트 추출
    texts = [doc.page_content for doc in documents]
    
    # 임베딩 생성
    embeddings = embed_texts(texts)
    
    # ID와 메타데이터 생성
    ids = [f"{video_id}_{i}" for i in range(len(documents))]
    metadatas = [
        {
            "video_id": video_id,
            **doc.metadata
        }
        for doc in documents
    ]
    
    # ChromaDB에 추가
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    
    print(f"[ChromaClient] ✅ {len(documents)}개 문서 저장 완료")
    return len(documents)


def search(query: str, k: int = 4, video_id: Optional[str] = None) -> List[Document]:
    """
    쿼리 기반 벡터 검색
    
    Args:
        query: 검색 쿼리 텍스트
        k: 반환할 결과 수
        video_id: 특정 영상으로만 검색 (None이면 전체)
    
    Returns:
        List[Document]: 유사한 문서 리스트
    """
    collection = get_collection()
    
    # 쿼리 임베딩
    query_embedding = embed_texts([query])[0]
    
    # where 필터
    where_filter = {"video_id": video_id} if video_id else None
    
    # 검색
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where_filter
    )
    
    # 결과를 Document로 변환
    documents = []
    if results['ids'] and len(results['ids']) > 0:
        for i, doc_id in enumerate(results['ids'][0]):
            doc = Document(
                page_content=results['documents'][0][i],
                metadata=results['metadatas'][0][i] if results['metadatas'] else {}
            )
            documents.append(doc)
    
    print(f"[ChromaClient] 검색 완료: {len(documents)}개 결과")
    return documents


def get_stats() -> dict:
    """DB 통계"""
    collection = get_collection()
    count = collection.count()
    return {
        "collection": COLLECTION_NAME,
        "total_documents": count,
        "embedding_dim": EMBEDDING_DIM
    }
