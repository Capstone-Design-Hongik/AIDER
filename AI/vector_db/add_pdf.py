# vector_db/add_pdf.py
import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from vector_db.chroma_client import get_vectorstore

CHUNK_SIZE = 1000   # [수정] 500 → 1000 (금융 텍스트는 맥락이 길어야 함)
CHUNK_OVERLAP = 150  # [수정] 100 → 150


def add_pdf_to_db(pdf_path: str, category: str = "stock") -> int:
    """
    PDF 파일을 청킹하여 ChromaDB에 저장

    Args:
        pdf_path : PDF 파일 경로
        category : 메타데이터 카테고리 (예: "stock", "economy", "report")

    Returns:
        저장된 청크 수
    """
    # ── 1. 파일 존재 확인 ─────────────────────────────
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"[Error] PDF 파일을 찾을 수 없습니다: {pdf_path}")

    file_name = os.path.basename(pdf_path)
    print(f"\n[PDF] '{file_name}' 로드 중...")

    # ── 2. PDF 로드 ───────────────────────────────────
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    print(f"  - 총 페이지 수: {len(pages)}페이지")

    if not pages:
        print("[Warning] PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.")
        return 0

    # ── 3. 청킹 ──────────────────────────────────────
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )
    docs = []
    for page in pages:
        chunks = text_splitter.split_text(page.page_content)
        page_num = page.metadata.get("page", 0) + 1  # 0-indexed → 1-indexed
        for chunk in chunks:
            if len(chunk.strip()) < 20:
                continue
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "category": category,  # (예: "stock", "economy", "report")
                    "source": file_name,   # 출처 파일명 추가
                    "page": page_num,      # 페이지 번호 추가
                },
            ))

    print(f"  - 생성된 청크 수: {len(docs)}개")

    if not docs:
        print("[Warning] 추출된 청크가 없습니다.")
        return 0

    # ── 4. DB 저장 ────────────────────────────────────
    vs = get_vectorstore()
    print(f"[PDF] '{file_name}' 임베딩 및 저장 중...")
    vs.add_documents(docs)

    total = vs._collection.count()
    print(f"[PDF] ✅ 저장 완료! | 추가: {len(docs)}청크 | DB 전체: {total}청크")
    return len(docs)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Example: python -m vector_db.add_pdf ./data/Hangook_bank.pdf stock")
        sys.exit(1)

    pdf_path = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else "stock"

    print(f"[실행] PDF: {pdf_path} | 카테고리: {category}")
    count = add_pdf_to_db(pdf_path, category=category)
    print(f"[완료] {count}개 청크 저장됨")