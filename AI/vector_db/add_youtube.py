# vector_db/add_youtube.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from vector_db.chroma_client import get_vectorstore, video_exists

CHUNK_SIZE = 1000   # [수정] 500 → 1000
CHUNK_OVERLAP = 150  # [수정] 100 → 150


def add_youtube_to_db(full_text: str, video_id: str, category_prefix: str = "youtube") -> int:
    """
    YouTube 자막 텍스트를 청킹하여 ChromaDB에 저장

    Args:
        full_text      : YouTube 자막 전체 텍스트
        video_id       : YouTube video_id (중복 방지 및 카테고리 구분에 사용)
        category_prefix: 카테고리 접두어 (기본값: "youtube")

    Returns:
        저장된 청크 수 (이미 저장된 경우 0)
    """
    # ── 0. 중복 저장 방지 ─────────────────────────────
    # [수정] video_id 기반 카테고리로 동일 영상 재임베딩 방지
    category = f"{category_prefix}_{video_id}"
    if video_exists(video_id):
        print(f"[YouTube] '{video_id}' 는 이미 DB에 있습니다. 저장 스킵.")
        return 0

    print(f"\n[YouTube] 텍스트 청킹 시작... (video_id: {video_id})")

    # ── 1. 텍스트 길이 검증 ───────────────────────────
    if len(full_text) < 50:
        print("[Warning] 텍스트가 너무 짧습니다.")
        return 0

    # ── 2. 청킹 ──────────────────────────────────────
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )
    texts = text_splitter.split_text(full_text)
    docs = [
        Document(
            page_content=t,
            metadata={
                "category": category,    # [수정] "youtube_VIDEO_ID" 형태로 저장
                "video_id": video_id,    # [수정] video_id 별도 저장
            },
        )
        for t in texts
        if len(t.strip()) >= 20
    ]

    print(f"  - 전체 텍스트 길이 : {len(full_text)}자")
    print(f"  - Chunk Size       : {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print(f"  - 생성된 청크 수   : {len(docs)}개")

    # ── 3. DB 저장 ────────────────────────────────────
    vs = get_vectorstore()
    vs.add_documents(docs)

    total = vs._collection.count()
    print(f"[YouTube] ✅ 저장 완료! | 추가: {len(docs)}청크 | DB 전체: {total}청크")
    return len(docs)