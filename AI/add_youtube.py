from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chroma_client import add_documents, video_exists

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)

def add_youtube_to_db(transcript_text: str, video_id: str) -> int:
    category = f"youtube_{video_id}"
    if video_exists(video_id):
        print(f"[AddYouTube] 캐시 히트: '{video_id}'는 이미 DB에 있습니다.")
        return 0

    chunks: List[str] = _splitter.split_text(transcript_text)
    print(f"[AddYouTube] 자막 {len(transcript_text):,}자 → {len(chunks)}청크 분할 완료")

    docs = [
        Document(
            page_content=chunk,
            metadata={"video_id": video_id, "category": category},
        )
        for chunk in chunks
    ]

    added_count = add_documents(docs, video_id)
    return added_count
