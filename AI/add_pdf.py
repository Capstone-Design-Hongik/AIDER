from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional
from datetime import datetime
import os

# ── 전략 지식 문서 ──────────────────────────────────────────
_STRATEGY_DOCS = [
    # ── 볼린저밴드 ──────────────────────────────────────────
    {
        "content": (
            "볼린저밴드 매수 신호: 주가가 하단 밴드에 닿거나 하향 돌파할 때 평균 회귀 매수 신호. "
            "장기 횡보 중 밴드폭이 좁아지는 스퀴즈 이후 하단 이탈하면 진입 고려. "
            "중간선(20일 이동평균) 아래에서 하단 밴드 접근 시 롱 포지션 검토."
        ),
        "metadata": {"strategy": "bollinger", "topic": "entry", "source": "learningspoons.com"},
    },
    {
        "content": (
            "볼린저밴드 매도·청산 신호: 주가가 상단 밴드에 닿거나 돌파할 때 과열 매도 신호. "
            "상단밴드 이탈 후 음봉 발생 및 밴드 안으로 재진입 시 청산. "
            "중간선(20MA) 도달 시 부분 이익실현."
        ),
        "metadata": {"strategy": "bollinger", "topic": "exit", "source": "brunch.co.kr"},
    },
    {
        "content": (
            "볼린저밴드 손절 및 리스크 관리: 하단밴드 종가 이탈 시 즉시 손절. "
            "일반적으로 2~3% 손실에서 자동 청산 설정 권장. "
            "상단밴드 연속 터치는 강한 상승 추세이므로 추격 매도 금지."
        ),
        "metadata": {"strategy": "bollinger", "topic": "risk", "source": "blog.okfngroup.com"},
    },
    # ── 추세추종 ────────────────────────────────────────────
    {
        "content": (
            "추세추종 매수 진입 신호: 단기 이동평균(5일·20일)이 장기 이동평균(60일·120일)을 상향 돌파하는 "
            "골든크로스 발생 시 상승 추세 시작 신호. 20MA 근처 눌림목에서 분할 매수 진입."
        ),
        "metadata": {"strategy": "trend", "topic": "entry", "source": "ebc.com/kr"},
    },
    {
        "content": (
            "추세추종 매도·청산 신호: 단기 이동평균이 장기 이동평균을 하향 돌파하는 데드크로스 발생 시 매도. "
            "연속 고점·저점 상승 패턴이 무너질 때 청산. 20MA 우하향 전환 시 중기 추세 종료."
        ),
        "metadata": {"strategy": "trend", "topic": "exit", "source": "upbitcare.com"},
    },
    # ── 거시 경제 (Macro) ──
    {
        "content": (
            "금리 인상 및 인플레이션의 영향: 중앙은행의 금리 인상은 기업의 이자 비용을 높이고 미래 가치 할인율을 높여 "
            "특히 기술주/성장주에 하방 압력을 가함. 고금리 환경에서는 안전 자산 선호도가 높아짐."
        ),
        "metadata": {"strategy": "macro", "topic": "interest_rate", "source": "investing.com"},
    },
    {
        "content": (
            "환율과 주가의 상관관계: 원/달러 환율 상승 시 일반적으로 국내 증시는 하락하는 경향이 있음. "
            "이는 외국인 투자자의 환차손 우려에 따른 자금 이탈 때문이며 외국인 수급 악화의 영향이 큼."
        ),
        "metadata": {"strategy": "macro", "topic": "exchange_rate", "source": "mk.co.kr"},
    },
    # ── 투자 심리 (Psychology) ──
    {
        "content": (
            "투자자 심리(FOMO 및 패닉셀) 대응: FOMO는 소외될 것에 대한 두려움으로 급등주를 추격 매수하는 심리임. "
            "패닉셀은 공포에 휩싸여 저점에서 투매하는 현상으로, 기계적인 손절가(Stop-loss) 대응이 필수적임."
        ),
        "metadata": {"strategy": "psychology", "topic": "fomo_panic", "source": "tistory.com"},
    },
    # ── 리스크 관리 및 격언 ──
    {
        "content": (
            "범용 리스크 관리 체크리스트: 1. 기계적 손절매 원칙 이행. 2. 분할 매수 및 종목 비중 제한(30% 이내). "
            "3. 여유 자금 투자 원칙 준수. 4. 감정적 뇌동매매(FOMO, 투매) 경계."
        ),
        "metadata": {"strategy": "risk", "topic": "checklist", "source": "general_principles"},
    },
    {
        "content": (
            "투자 거장들의 핵심 격언: 워런 버핏 '제1원칙: 돈을 잃지 마라'. 피터 린치 '공부 없는 투자는 도박이다'. "
            "제시 리버모어 '시장은 반복된다'. 앙드레 코스톨라니 '생각은 깊게, 행동은 민첩하게'."
        ),
        "metadata": {"strategy": "philosophy", "topic": "maxims", "source": "famous_investors"},
    },
]

class PDFManager:
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 80
    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP)
    async def add_pdf_file(self, pdf_path: str, title: Optional[str] = None, category: Optional[str] = None) -> int:
        try:
            text = self._extract_text_from_pdf(pdf_path)
            chunks = self.splitter.split_text(text)
            documents = [Document(page_content=c, metadata={"source": "pdf", "file_name": os.path.basename(pdf_path), "added_at": datetime.now().isoformat(), "type": "pdf_text"}) for c in chunks]
            return self.vector_db.add_documents(documents=documents, doc_type="pdf")
        except Exception as e: raise
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages: text += page.extract_text() + "\n"
        return text
    def seed_strategy_knowledge(self) -> int:
        documents = [Document(page_content=d["content"], metadata={**d["metadata"], "source": "strategy_knowledge", "type": "strategy_text", "added_at": datetime.now().isoformat()}) for d in _STRATEGY_DOCS]
        return self.vector_db.add_documents(documents=documents, doc_type="text")

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    args = sys.argv[1:]
    if "--seed-strategy" not in args:
        print("사용법: python add_pdf.py --seed-strategy")
        sys.exit(0)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    from download_embedding_model import EmbeddingModelManager
    from postgres_manager import PostgresVectorManager
    embedding_model = EmbeddingModelManager.download_model()
    vector_db = PostgresVectorManager(db_url=db_url, embedding_model=embedding_model)
    manager = PDFManager(vector_db)
    count = manager.seed_strategy_knowledge()
    print(f"완료: {count}개 문서 삽입됨")
