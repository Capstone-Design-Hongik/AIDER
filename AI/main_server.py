# main_server.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core import AnalysisRequest, handle_test_video, handle_analyze, AnalysisResponse

app = FastAPI(
    title="투자 전략 AI 멘토 API",
    description="졸업 프로젝트: 사용자 매매 기록 + 유튜브 영상 → 투자 조언 생성",
    version="1.0.0"
)

# 배포용 CORS 설정 (실제 배포 시 프론트엔드 도메인으로 교체)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "*"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "mode": "server",
        "message": "투자 전략 AI 멘토 서버"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 (배포 환경에서 중요)"""
    return {"status": "healthy"}


@app.post("/api/test-video", response_model=dict)
async def test_video_id(url: str):
    """
    YouTube URL에서 자막 추출 가능 여부 테스트
    
    파라미터:
    - url: YouTube 영상 URL
    
    반환:
    - video_id: 추출된 영상 ID
    - transcript_length: 자막 글자 수
    - preview: 자막 미리보기 (처음 200자)
    """
    try:
        return await handle_test_video(url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_video(request: AnalysisRequest):
    """
    메인 분석 API
    
    요청 바디:
    {
        "externalUrl": "https://www.youtube.com/watch?v=...",
        "user_data": {
            "trades": [...],
            "stockPrices": [...]
        }
    }
    """
    return await handle_analyze(request)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main_server:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
