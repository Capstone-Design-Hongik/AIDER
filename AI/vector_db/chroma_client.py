# vector_db/chroma_client.py
import os
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "stock_documents"

# [로컬] download_model.py로 받은 모델 경로
LOCAL_MODEL_PATH = "./local_model"
HF_MODEL_NAME = "BAAI/bge-m3"

_embeddings = None
_vectorstore = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """임베딩 모델 싱글톤 반환 — 로컬 모델 우선, 없으면 HuggingFace Hub"""
    global _embeddings
    if _embeddings is not None:
        print("[Debug] 기존 임베딩 모델 재사용")
        return _embeddings

    # [로컬] ./local_model 폴더가 있으면 오프라인 사용
    if os.path.isdir(LOCAL_MODEL_PATH):
        model_name = LOCAL_MODEL_PATH
        print(f"[Debug] 로컬 모델 사용: {LOCAL_MODEL_PATH}")
    else:
        model_name = HF_MODEL_NAME
        print(f"[Debug] 로컬 모델 없음 → HuggingFace Hub에서 로드: {HF_MODEL_NAME}")

    _embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return _embeddings


def get_vectorstore() -> Chroma:
    """PersistentClient 기반 Chroma vectorstore 싱글톤 반환"""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    print(f"[VectorDB] PersistentClient 연결 중... (경로: {CHROMA_PATH})")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    _vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        client=client,
    )
    total = _vectorstore._collection.count()
    print(f"[VectorDB] ✅ 연결 완료! 현재 저장된 청크 수: {total}개")
    return _vectorstore


def get_chunk_count() -> int:
    return get_vectorstore()._collection.count()


def reset_memory():
    """메모리 상의 싱글톤만 초기화 (디스크 DB는 유지)"""
    global _embeddings, _vectorstore
    _embeddings = None
    _vectorstore = None
    print("[Info] 메모리 초기화 완료 (디스크 DB는 유지됨)")


def video_exists(video_id: str) -> bool:
    """특정 video_id의 자막이 이미 DB에 저장되어 있는지 확인"""
    vs = get_vectorstore()
    try:
        category = f"youtube_{video_id}"
        results = vs._collection.get(where={"category": category}, limit=1)
        exists = len(results["ids"]) > 0
        if exists:
            print(f"[VectorDB] video_id '{video_id}' 는 이미 DB에 저장되어 있습니다. 임베딩 스킵.")
        return exists
    except Exception as e:
        print(f"[Warning] video_exists 확인 실패: {e}")
        return False


def search(query: str, k: int = 3, category: str = None) -> list:
    """유사도 검색 (공통 검색 함수)"""
    vs = get_vectorstore()
    print(f"\n[Search] 질의: '{query}' | category={category or '전체'}")

    filter_dict = {"category": category} if category else None
    results = vs.similarity_search(query, k=k, filter=filter_dict)

    print(f"[Search] 검색 결과 {len(results)}건:")
    for i, res in enumerate(results):
        preview = res.page_content[:80].replace("\n", " ")
        cat = res.metadata.get("category", "N/A")
        print(f"  [{i+1}] [{cat}] {preview}...")

    return results