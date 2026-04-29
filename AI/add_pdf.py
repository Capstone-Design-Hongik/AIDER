import PyPDF2
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional
from datetime import datetime
import os

class PDFManager:
    """PDF를 벡터DB에 추가 (독립적으로 실행 가능)"""
    
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 80
    
    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def add_pdf_file(
        self,
        pdf_path: str,
        title: Optional[str] = None,
        category: Optional[str] = None
    ) -> int:
        """PDF 파일을 벡터DB에 추가"""
        
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF 파일 없음: {pdf_path}")
            
            print(f"\n📄 PDF 처리 중: {pdf_path}")
            
            # 1. PDF 텍스트 추출
            text = self._extract_text_from_pdf(pdf_path)
            print(f"✅ 텍스트 추출 완료 ({len(text)} 글자)")
            
            # 2. 청킹
            chunks = self.splitter.split_text(text)
            print(f"✅ 청킹 완료 ({len(chunks)} 청크)")
            
            # 3. 문서 생성
            file_name = os.path.basename(pdf_path)
            documents = []
            
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": "pdf",
                        "file_name": file_name,
                        "file_path": pdf_path,
                        "title": title or file_name,
                        "category": category or "general",
                        "chunk_id": i,
                        "chunk_total": len(chunks),
                        "added_at": datetime.now().isoformat(),
                        "type": "pdf_text"
                    }
                )
                documents.append(doc)
            
            # 4. 벡터DB에 추가
            added_count = self.vector_db.add_documents(
                documents=documents,
                doc_type="pdf"
            )
            
            print(f"✅ {added_count}개 문서 추가 완료")
            
            return added_count
        
        except Exception as e:
            print(f"❌ PDF 처리 실패: {e}")
            raise
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF에서 텍스트 추출"""
        
        try:
            text = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                print(f"  📖 PDF 페이지 수: {num_pages}")
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                    
                    # 페이지 구분 마크 추가
                    text += f"\n[Page {page_num + 1}]\n"
            
            return text
        
        except Exception as e:
            print(f"❌ PDF 텍스트 추출 실패: {e}")
            raise
    
    async def add_multiple_pdfs(
        self,
        pdf_directory: str,
        category: Optional[str] = None
    ) -> int:
        """디렉토리의 모든 PDF를 추가"""
        
        try:
            if not os.path.isdir(pdf_directory):
                raise NotADirectoryError(f"디렉토리 없음: {pdf_directory}")
            
            print(f"\n📂 PDF 디렉토리 처리 중: {pdf_directory}")
            
            pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
            print(f"  📄 발견된 PDF 파일: {len(pdf_files)}개")
            
            total_added = 0
            
            for pdf_file in pdf_files:
                pdf_path = os.path.join(pdf_directory, pdf_file)
                try:
                    added = await self.add_pdf_file(
                        pdf_path=pdf_path,
                        title=pdf_file,
                        category=category
                    )
                    total_added += added
                except Exception as e:
                    print(f"  ⚠️  {pdf_file} 처리 중 오류: {e}")
                    continue
            
            print(f"✅ 총 {total_added}개 문서 추가 완료")
            
            return total_added
        
        except Exception as e:
            print(f"❌ PDF 디렉토리 처리 실패: {e}")
            raise