import os
import shutil
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 전역 변수로 vectorstore 저장 (메모리 기반)
_vectorstore = None

def get_embeddings():
    model_name = "jhgan/ko-sroberta-multitask"
    model_kwargs = {'device': 'cpu'} 
    encode_kwargs = {'normalize_embeddings': True}
    
    print(f"[Debug] 임베딩 모델 로드 경로: {model_name}")
    
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

def create_vector_db(full_text):
    global _vectorstore
    
    print("\n[Chunking] Recursive Character Text Splitter !")

    embeddings = get_embeddings()

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
        length_function=len
    )

    if len(full_text) < 50:
        print("[Warning] 텍스트가 너무 짧습니다.")
        docs = []
    else:
        texts = text_splitter.split_text(full_text)
        from langchain_core.documents import Document
        docs = [Document(page_content=t) for t in texts]
    
    print(f"  - 전체 텍스트 길이: {len(full_text)}자")
    print(f"  - (Chunk Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP})")
    print(f"  - 생성된 청크(Chunk) 개수: {len(docs)}개")
    
    # 메모리 기반 ChromaDB 생성 (persist_directory 제거)
    _vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="investment_strategies"
    )
    
    print(f"[ChromaDB 저장] 메모리에 데이터 저장 완료!")
    return _vectorstore

def search_strategy(query, k=3):
    global _vectorstore
    
    print(f"\n[Search] 검색 질의: '{query}'")
    
    if _vectorstore is None:
        raise ValueError("[Error] VectorStore가 초기화되지 않았습니다. create_vector_db()를 먼저 호출하세요.")
    
    # 메모리에서 직접 검색
    results = _vectorstore.similarity_search(query, k=k)
    
    print(f"[Search] 검색 결과({len(results)}건):")
    for i, res in enumerate(results):
        print(f"  {i+1}. {res.page_content[:100]}... (생략)")
        print("-" * 30)
    
    return results

def reset_db():
    global _vectorstore
    _vectorstore = None
    print("[Info] 메모리 DB 초기화 완료")