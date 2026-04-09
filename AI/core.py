# core.py
import json
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from transcript import extract_video_id, transcript
from add_youtube import add_youtube_to_db
from chroma_client import search
from generation import generate_answer, make_search_queries

# ── 데이터 모델 ──────────────────────────────────────────────────────────

class TradeRecord(BaseModel):
    """매매 기록"""
    date: str           # "YYYY-MM-DD"
    stockName: str      # "삼성전자"
    stockCode: str      # "005930"
    tradeType: str      # "buy" | "sell"
    price: float        # 매매가격
    quantity: int       # 수량


class StockPriceRecord(BaseModel):
    """주식 일별 주가 정보 (최대 60일)"""
    date: str           # "YYYY-MM-DD"
    closePrice: float   # 종가


class UserData(BaseModel):
    """사용자 데이터 (프론트엔드 형식)"""
    trades: List[TradeRecord]
    stockPrices: List[StockPriceRecord]  # camelCase
    strategy: Optional[str] = None       # "external" 등
    externalUrl: Optional[str] = None    # YouTube URL


class AnalysisRequest(BaseModel):
    """분석 요청"""
    externalUrl: Optional[str] = None
    user_data: UserData


class AnalysisResponse(BaseModel):
    """분석 응답"""
    video_id: str
    cached: bool  # 캐시에서 로드되었는지
    analysis: Optional[dict] = None
    error: Optional[str] = None


# ── 핵심 로직 ────────────────────────────────────────────────────────────

async def handle_test_video(url: str) -> dict:
    """자막 추출 테스트"""
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "유효하지 않은 유튜브 URL"}
    
    transcript_text = transcript(video_id)
    if not transcript_text:
        return {"error": "자막을 추출할 수 없습니다"}
    
    return {
        "video_id": video_id,
        "transcript_length": len(transcript_text),
        "preview": transcript_text[:200]
    }


async def handle_analyze(request: AnalysisRequest) -> AnalysisResponse:
    """
    메인 분석 파이프라인
    
    1. URL에서 video_id 추출
    2. 캐시 확인 (이미 분석된 영상인지)
    3. 캐시 미스 시: 자막 추출 → 청킹 → 임베딩 → DB 저장
    4. RAG 검색 (동적 쿼리)
    5. LLM 답변 생성
    """
    
    print("\n" + "="*60)
    print("🎬 분석 시작")
    print("="*60)
    
    # Step 1: Video URL 결정
    # externalUrl이 있으면 사용, 없으면 user_data.externalUrl 사용
    video_url = request.externalUrl or request.user_data.externalUrl
    if not video_url:
        return AnalysisResponse(
            video_id="unknown",
            cached=False,
            error="YouTube URL이 필요합니다"
        )
    
    print(f"\n[Step 1] URL 검증 및 Video ID 추출...")
    video_id = extract_video_id(video_url)
    if not video_id:
        return AnalysisResponse(
            video_id="unknown",
            cached=False,
            error="유효하지 않은 유튜브 URL입니다"
        )
    
    print(f"  ✅ Video ID: {video_id}")
    
    # Step 2: 캐시 확인
    print("\n[Step 2] 캐시 확인...")
    from chroma_client import video_exists
    cached = video_exists(video_id)
    
    if not cached:
        # Step 3: 자막 추출 → DB 저장
        print("\n[Step 3] 자막 추출 및 저장...")
        transcript_text = transcript(video_id)
        if not transcript_text:
            return AnalysisResponse(
                video_id=video_id,
                cached=False,
                error="자막을 추출할 수 없습니다"
            )
        
        # DB에 저장
        added = add_youtube_to_db(transcript_text, video_id)
        print(f"  ✅ {added}개 청크 저장")
    
    # Step 4: 동적 쿼리 생성
    print("\n[Step 4] 동적 쿼리 생성...")
    queries = make_search_queries(request.user_data)
    
    # Step 5: RAG 검색
    print("\n[Step 5] RAG 검색...")
    all_docs = []
    for query in queries:
        docs = search(query, k=2, video_id=video_id)
        all_docs.extend(docs)
    
    # 중복 제거
    unique_docs = {doc.page_content: doc for doc in all_docs}
    all_docs = list(unique_docs.values())[:4]  # 상위 4개
    
    video_context = "\n\n---\n\n".join([
        f"[{i+1}] {doc.page_content[:200]}..."
        for i, doc in enumerate(all_docs)
    ])
    
    print(f"  ✅ {len(all_docs)}개 문서 검색")
    
    # Step 6: LLM 생성
    print("\n[Step 6] LLM 분석...")
    try:
        analysis = generate_answer(video_context, request.user_data)
        print(f"  ✅ 분석 완료")
        
        return AnalysisResponse(
            video_id=video_id,
            cached=cached,
            analysis=analysis
        )
    except Exception as e:
        print(f"  ❌ LLM 오류: {e}")
        return AnalysisResponse(
            video_id=video_id,
            cached=cached,
            error=str(e)
        )
