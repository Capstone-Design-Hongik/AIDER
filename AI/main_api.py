import uvicorn
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import traceback

# 모듈 임포트
from transcript import transcript, extract_video_id
from vector_store import create_vector_db, search_strategy, reset_db
from generation import generate_answer

app = FastAPI(
    title="투자 전략 AI 멘토 API",
    description="졸업 프로젝트: 사용자 매매 기록과 유튜브 영상을 결합한 투자 조언 생성"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# --- [API 엔드포인트] ---

@app.get("/")
def read_root():
    return {"status": "Running", "message": "졸업 프로젝트 API 서버가 정상 작동 중입니다."}

@app.get("/health")
def health_check():
    """서버 상태 확인"""
    return {"status": "healthy"}

@app.post("/api/test-video")
async def test_video_id(url: str):
    """유튜브 URL 테스트용 엔드포인트"""
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 유튜브 URL입니다.")
        
        print(f"[Test] Video ID: {video_id}")
        
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
            
            print(f"[API Log] 요청 URL: {request.externalUrl}")
            
            video_id = extract_video_id(request.externalUrl)
            if not video_id:
                raise HTTPException(
                    status_code=400, 
                    detail=f"유효하지 않은 유튜브 URL입니다. URL: {request.externalUrl}"
                )
                
            print(f"[API Log] 추출된 Video ID: {video_id}")

            transcript_text = transcript(video_id)
            
            if not transcript_text:
                error_detail = {
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
                raise HTTPException(status_code=404, detail=error_detail)
            
            print(f"[API Log] 자막 추출 성공! 길이: {len(transcript_text)}자")
                
            # RAG: DB 생성 및 전략 검색
            print("[API Log] ChromaDB 생성 시작 (EphemeralClient)...")
            
            try:
                create_vector_db(transcript_text)
                print("[API Log] ChromaDB 생성 성공!")
            except Exception as db_error:
                print(f"[Error] ChromaDB 생성 실패: {db_error}")
                print(traceback.format_exc())
                raise HTTPException(
                    status_code=500,
                    detail=f"데이터베이스 생성 실패: {str(db_error)}"
                )
            
            query = "이 동영상에서 주장하는 핵심 매매 기법과 투자 원칙, 매수 타점은?"
            retrieval_result = search_strategy(query, k=5)
            
            video_context = "\n\n".join([doc.page_content for doc in retrieval_result])
            print(f"[API Log] RAG 검색 완료! Context 길이: {len(video_context)}자")
            
        else:
            video_context = "일반적인 기술적 분석 관점에서 조언합니다."
            print("[API Log] 기본 전략 모드로 진행합니다.")

        # LLM 답변 생성
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
    uvicorn.run("main_api:app", host="0.0.0.0", port=8000, reload=True)