# 로컬에서 돌릴 때 사용
import socket
import uvicorn
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from transcript import transcript, extract_video_id
from vector_db.add_youtube import add_youtube_to_db
from vector_db.chroma_client import search
from generation import generate_answer, make_search_queries

app = FastAPI(
    title="투자 전략 AI 멘토 API",
    description="졸업 프로젝트: 사용자 매매 기록과 유튜브 영상을 결합한 투자 조언 생성"
)

# [로컬] 프론트 개발서버 포트를 여기에 추가 (Vite: 5173, CRA: 3000, Next.js: 3000 등)
LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- [1. 요청 데이터 구조] ---

class TradeItem(BaseModel):
    stockName: str
    stockCode: str
    tradeType: str
    date: str
    price: float
    quantity: int


class StockPriceItem(BaseModel):
    date: str
    closePrice: float


class AnalysisRequest(BaseModel):
    trades: List[TradeItem]
    stockPrices: List[StockPriceItem]
    strategy: str = "external"
    externalUrl: Optional[str] = None


# --- [로컬] 서버 시작 시 접속 주소 출력 ---

@app.on_event("startup")
async def print_local_url():
    """
    서버 시작할 때 LAN IP를 출력
    팀원(프론트/백 담당)이 어느 주소로 요청을 보내야 하는지 터미널에 표시
    """
    try:
        # 실제 LAN IP 가져오기 (127.0.0.1 말고)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    port = 8000
    print("\n" + "="*55)
    print("  🚀 AI 서버 시작!")
    print(f"  로컬 접속:  http://localhost:{port}")
    print(f"  팀원 접속:  http://{local_ip}:{port}  ← 형한테 이 주소 알려주세요")
    print(f"  API 문서:   http://localhost:{port}/docs")
    print("="*55 + "\n")


# --- [API 엔드포인트] ---

@app.get("/")
def read_root():
    return {"status": "Running", "message": "졸업 프로젝트 API 서버가 정상 작동 중입니다."}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/test-video")
async def test_video_id(url: str):
    """유튜브 URL 테스트용 엔드포인트"""
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 유튜브 URL입니다.")

        transcript_text = transcript(video_id)

        if not transcript_text:
            return {
                "success": False,
                "video_id": video_id,
                "message": "자막을 가져올 수 없습니다.",
                "transcript_length": 0
            }

        return {
            "success": True,
            "video_id": video_id,
            "transcript_length": len(transcript_text),
            "preview": transcript_text[:200] + "..."
        }

    except Exception as e:
        print(f"[Error] 테스트 중 오류: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")


@app.post("/api/analyze")
async def analyze_video(request: AnalysisRequest):
    print(f"\n[API Log] 분석 요청 도착 (Strategy: {request.strategy})")
    print(f"[API Log] 매매 기록 수: {len(request.trades)}개")
    print(f"[API Log] 주가 데이터 수: {len(request.stockPrices)}개")

    video_context = ""

    try:
        if request.strategy == "external":
            if not request.externalUrl:
                raise HTTPException(status_code=400, detail="externalUrl이 필요합니다.")

            video_id = extract_video_id(request.externalUrl)
            if not video_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"유효하지 않은 유튜브 URL입니다. URL: {request.externalUrl}"
                )

            print(f"[API Log] 추출된 Video ID: {video_id}")

            # ── 1. 자막 추출 ─────────────────────────────
            transcript_text = transcript(video_id)
            if not transcript_text:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": "자막을 가져올 수 없습니다.",
                        "video_id": video_id,
                        "url": request.externalUrl,
                        "possible_causes": [
                            "1. 해당 영상에 자막이 없을 수 있습니다.",
                            "2. 영상이 비공개이거나 삭제되었을 수 있습니다.",
                            "3. 자막이 비활성화되어 있을 수 있습니다.",
                            "4. 일시적인 네트워크 문제일 수 있습니다."
                        ],
                        "suggestion": "유튜브에서 해당 영상의 자막 설정을 확인해주세요."
                    }
                )

            print(f"[API Log] 자막 추출 성공! 길이: {len(transcript_text)}자")

            # ── 2. ChromaDB 저장 (같은 영상이면 자동 스킵) ─
            try:
                added = add_youtube_to_db(transcript_text, video_id=video_id)
                if added > 0:
                    print(f"[API Log] 신규 영상 임베딩 완료! {added}청크 추가됨")
                else:
                    print(f"[API Log] 캐시 히트: '{video_id}' 는 이미 DB에 있습니다.")
            except Exception as db_error:
                print(f"[Error] ChromaDB 저장 실패: {db_error}")
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=500,
                    detail=f"데이터베이스 저장 실패: {str(db_error)}"
                )

            # ── 3. 동적 쿼리로 RAG 검색 ──────────────────
            queries = make_search_queries(request)
            category = f"youtube_{video_id}"

            all_chunks = []
            seen_contents = set()
            for q in queries:
                results = search(q, k=4, category=category)
                for doc in results:
                    if doc.page_content not in seen_contents:
                        all_chunks.append(doc)
                        seen_contents.add(doc.page_content)

            video_context = "\n\n".join([doc.page_content for doc in all_chunks[:10]])
            print(f"[API Log] RAG 검색 완료! 유니크 청크: {len(all_chunks)}개 | Context 길이: {len(video_context)}자")

        else:
            video_context = "일반적인 기술적 분석 관점에서 조언합니다."
            print("[API Log] 기본 전략 모드로 진행합니다.")

        # ── 4. LLM 답변 생성 ─────────────────────────────
        print("[API Log] LLM 답변 생성 시작...")
        final_answer = generate_answer(video_context, request)

        print("[API Log] 분석 완료!")
        return final_answer

    except HTTPException as he:
        raise he

    except Exception as e:
        print(f"[Error] 예상치 못한 오류 발생: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"서버 내부 오류: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("main_local:app", host="0.0.0.0", port=8000, reload=True)