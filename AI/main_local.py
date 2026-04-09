# main_local.py
import socket
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core import AnalysisRequest, handle_test_video, handle_analyze, AnalysisResponse

app = FastAPI(
    title="투자 전략 AI 멘토 API (로컬)",
    description="졸업 프로젝트: 사용자 매매 기록 + 유튜브 영상 → 투자 조언 생성",
    version="1.0.0"
)

# 로컬 개발용 CORS 설정
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


@app.on_event("startup")
async def print_local_url():
    """서버 시작 시 접속 URL 출력"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    port = 8000
    print("\n" + "=" * 60)
    print("  🚀 AI 투자 조언 서버 시작!")
    print("=" * 60)
    print(f"  로컬 접속:  http://localhost:{port}")
    print(f"  팀원 접속:  http://{local_ip}:{port}")
    print(f"  API 문서:   http://localhost:{port}/docs")
    print(f"  Swagger:    http://localhost:{port}/redoc")
    print("=" * 60 + "\n")


@app.get("/")
async def read_root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "mode": "local",
        "message": "투자 전략 AI 멘토 서버"
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
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
            "stockPrices": [...],
            "strategy": "external",
            "externalUrl": "https://..."
        }
    }
    """
    return await handle_analyze(request)


if __name__ == "__main__":
    uvicorn.run(
        "main_local:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes="venv/*"
    )
