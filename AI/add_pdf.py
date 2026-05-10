from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional
from datetime import datetime
import os

# ── 전략 지식 문서 ──────────────────────────────────────────
# 볼린저밴드 · 추세추종 핵심 원칙만 추출한 시드 데이터
# 출처: learningspoons.com, brunch.co.kr, ebc.com/kr, upbitcare.com
_STRATEGY_DOCS = [
    # ── 볼린저밴드 ──────────────────────────────────────────
    {
        "content": (
            "볼린저밴드 매수 신호: 주가가 하단 밴드에 닿거나 하향 돌파할 때 평균 회귀 매수 신호. "
            "장기 횡보 중 밴드폭이 좁아지는 스퀴즈 이후 하단 이탈하면 진입 고려. "
            "중간선(20일 이동평균) 아래에서 하단 밴드 접근 시 롱 포지션 검토. "
            "평균 회귀 원리: 극단적 가격이 중앙값(20MA)으로 복귀하는 성질 활용."
        ),
        "metadata": {"strategy": "bollinger", "topic": "entry", "source": "learningspoons.com"},
    },
    {
        "content": (
            "볼린저밴드 매도·청산 신호: 주가가 상단 밴드에 닿거나 돌파할 때 과열 매도 신호. "
            "상단밴드 이탈 후 음봉 발생 및 밴드 안으로 재진입 시 청산. "
            "중간선(20MA) 도달 시 부분 이익실현. "
            "밴드폭 확장 후 수축 전환은 추세 종료 신호로 해석."
        ),
        "metadata": {"strategy": "bollinger", "topic": "exit", "source": "brunch.co.kr"},
    },
    {
        "content": (
            "볼린저밴드 손절 및 리스크 관리: 하단밴드 종가 이탈 시 즉시 손절. "
            "일반적으로 2~3% 손실에서 자동 청산 설정 권장. "
            "상단밴드 연속 터치는 강한 상승 추세이므로 추격 매도 금지. "
            "후행성 지표이므로 거래량·추세선 등 보조 지표와 병행 필수. "
            "신뢰도 95% 수준이나 절대 신호로 맹신 금지."
        ),
        "metadata": {"strategy": "bollinger", "topic": "risk", "source": "blog.okfngroup.com"},
    },
    {
        "content": (
            "볼린저밴드 스퀴즈 전략: 밴드폭이 극도로 좁아지는 스퀴즈 구간은 변동성 폭발의 전조. "
            "스퀴즈 후 상단 돌파하면 상승 추세 시작 신호, 하단 돌파하면 하락 추세 시작 신호. "
            "돌파 방향 확인 전에 섣불리 진입하면 손실 위험. "
            "볼린저밴드 %b 지표로 현재 위치(하단=0, 상단=1) 수치화 가능."
        ),
        "metadata": {"strategy": "bollinger", "topic": "squeeze", "source": "namu.wiki"},
    },
    # ── 추세추종 ────────────────────────────────────────────
    {
        "content": (
            "추세추종 매수 진입 신호: 단기 이동평균(5일·20일)이 장기 이동평균(60일·120일)을 상향 돌파하는 "
            "골든크로스 발생 시 상승 추세 시작 신호. "
            "상승 추세 중 20MA 근처 눌림목에서 분할 매수 진입. "
            "고점·저점이 연속 상승하는 패턴(높은 고점·높은 저점) 확인 후 추가 매수. "
            "추세의 힘을 인정하고 강세 구간에 올라타는 것이 핵심 원칙."
        ),
        "metadata": {"strategy": "trend", "topic": "entry", "source": "ebc.com/kr"},
    },
    {
        "content": (
            "추세추종 매도·청산 신호: 단기 이동평균이 장기 이동평균을 하향 돌파하는 데드크로스 발생 시 매도. "
            "연속 고점·저점 상승 패턴이 무너질 때 청산. "
            "거래량 급감과 동시에 횡보 전환 시 추세 종료 신호. "
            "20MA 우하향 전환 시 중기 추세 종료, 60MA 하향 이탈 시 전량 매도 고려."
        ),
        "metadata": {"strategy": "trend", "topic": "exit", "source": "upbitcare.com"},
    },
    {
        "content": (
            "추세추종 손절 및 리스크 관리: 2~3% 손실에서 자동 청산 설정 권장. "
            "제시 리버모어 원칙: 최대 10% 손절을 한도로 설정. "
            "추세가 무너질 때 과감히 청산하는 심리적 훈련 필수. "
            "20MA 기울기가 평탄한 횡보 구간에서는 진입 금지. "
            "전체 자산의 일부만 추세매매에 활용하여 위험 분산. "
            "거래량으로 추세 신뢰도 추가 확인."
        ),
        "metadata": {"strategy": "trend", "topic": "risk", "source": "ko.wikipedia.org"},
    },
    {
        "content": (
            "추세추종 이동평균 활용 원칙: 이동평균선은 후행 지표로 미래 예측 불가, 발생한 추세만 확정. "
            "기간이 길수록 신호 신뢰도 높음(장기선 우선). "
            "5MA > 20MA > 60MA 정배열이면 강한 상승 추세. "
            "반대로 5MA < 20MA < 60MA 역배열이면 강한 하락 추세. "
            "시스템적·규칙 기반으로 일관되게 운영해야 장기 수익 확보 가능."
        ),
        "metadata": {"strategy": "trend", "topic": "ma_principle", "source": "ebc.com/kr"},
    },
    # ── 기술적 지표 (RSI, MACD) ──────────────────────────────
    {
        "content": (
            "RSI (상대강도지수) 활용 원칙: 주가의 상승 압력과 하락 압력 간의 상대적 강도를 나타내는 지표. "
            "RSI 70 이상은 과매수 구간으로 매도 신호, 30 이하는 과매도 구간으로 매수 신호를 의미함. "
            "주가는 상승하나 RSI는 하락하는 다이버전스 발생 시 추세 전환의 강력한 예고 신호로 해석."
        ),
        "metadata": {"strategy": "technical", "topic": "rsi", "source": "investopedia.com"},
    },
    {
        "content": (
            "MACD (이동평균 수렴확산지수) 활용 원칙: 단기/장기 이동평균선의 차이를 이용해 추세 강도를 측정. "
            "MACD 선이 시그널 선을 상향 돌파(골든크로스) 시 매수, 하향 돌파(데드크로스) 시 매도 신호. "
            "MACD 값이 0선 위에서 상승하면 강세장, 0선 아래에서 하락하면 약세장으로 판단함."
        ),
        "metadata": {"strategy": "technical", "topic": "macd", "source": "investopedia.com"},
    },
    # ── 한국 시장 특성 ──────────────────────────────────────
    {
        "content": (
            "한국 주식 시장(KRX)의 특징: 코스피(KOSPI)는 대형 우량주 중심으로 대외 경제 상황 및 환율에 민감하며, "
            "코스닥(KOSDAQ)은 IT/바이오 등 성장주 중심으로 테마주 열풍에 따른 변동성이 매우 큼. "
            "지정학적 리스크와 불투명한 지배구조로 인한 '코리아 디스카운트' 현상이 존재하며, "
            "외국인과 기관의 수급 동향이 주가 결정의 핵심 요소이므로 수급 확인이 필수적임."
        ),
        "metadata": {"strategy": "market", "topic": "korea", "source": "krx.co.kr"},
    },
    # ── 리스크 관리 ─────────────────────────────────────────
    {
        "content": (
            "범용 리스크 관리 체크리스트: 1. 손절매(Stop-loss) 원칙을 세우고 기계적으로 이행할 것(예: -10% 손절). "
            "2. 분할 매수를 통해 진입 가격을 분산하고 단일 종목에 자산의 30% 이상 투자 금지. "
            "3. 6개월 이내 사용해야 할 생활비가 아닌 여유 자금으로만 투자하여 심리적 안정을 유지할 것. "
            "4. 공포에 의한 투매나 탐욕에 의한 추격 매수를 경계하고 원칙에 기반하여 행동할 것."
        ),
        "metadata": {"strategy": "risk", "topic": "checklist", "source": "general_principles"},
    },
    # ── 투자 격언 ──────────────────────────────────────────
    {
        "content": (
            "투자 거장들의 핵심 격언: 워런 버핏은 '제1원칙: 절대로 돈을 잃지 마라'고 강조하며 원금 보존의 중요성을 역설함. "
            "피터 린치는 '공부하지 않고 투자하는 것은 패를 보지 않고 포커를 치는 것과 같다'며 철저한 분석을 권장함. "
            "제시 리버모어는 '주식 시장에는 새로운 것이 없으며 과거의 패턴이 반복된다'는 점을 명심하라 조언함."
        ),
        "metadata": {"strategy": "philosophy", "topic": "maxims", "source": "famous_investors"},
    },
]

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
            import PyPDF2
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

    def seed_strategy_knowledge(self) -> int:
        """볼린저밴드·추세추종 핵심 원칙을 벡터DB에 직접 삽입"""
        documents = [
            Document(
                page_content=d["content"],
                metadata={
                    **d["metadata"],
                    "source": "strategy_knowledge",
                    "type":   "strategy_text",
                    "added_at": datetime.now().isoformat(),
                },
            )
            for d in _STRATEGY_DOCS
        ]
        count = self.vector_db.add_documents(documents=documents, doc_type="text")
        print(f"✅ 전략 지식 {count}개 문서 추가 완료")
        return count


# ── CLI ───────────────────────────────────────────────────────
# python add_pdf.py --seed-strategy
# python add_pdf.py --seed-strategy --db-path ./chroma_db

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if "--seed-strategy" not in args:
        print("사용법: python add_pdf.py --seed-strategy [--db-path <경로>]")
        sys.exit(0)

    db_path = args[args.index("--db-path") + 1] if "--db-path" in args else "./chroma_db"

    print(f"DB 경로: {db_path}")
    print("임베딩 모델 로드 중...")

    from download_embedding_model import EmbeddingModelManager
    from chromadb_manager import ChromaDBManager

    embedding_model = EmbeddingModelManager.download_model()
    vector_db = ChromaDBManager(db_path=db_path, embedding_model=embedding_model)
    manager = PDFManager(vector_db)

    count = manager.seed_strategy_knowledge()
    print(f"\n완료: {count}개 문서 삽입됨")
