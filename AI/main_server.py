import asyncio
import os
import sys
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from models import UserData, Trade, StockPrice
from config import VECTOR_DB_PATH

load_dotenv()

# ── 유틸 함수 ──────────────────────────────────────────────

async def _save_transcript_to_db(vector_db, transcript_result, user_data):
    """YouTube 자막을 섹션별로 DB에 저장 (백그라운드에서 실행됨)"""
    from datetime import datetime
    from langchain_core.documents import Document

    strategy_name = transcript_result.structure.get("strategy_name", "일반 투자 조언")
    video_id      = transcript_result.structure.get("video_id", "unknown")

    # 동일 video_id가 이미 저장돼 있으면 중복 저장 스킵
    try:
        existing = vector_db.collection.get(
            where={"video_id": {"$eq": video_id}},
            limit=1,
        )
        if existing and existing.get("ids"):
            print(
                f"\n[BG] ⏭️  동일 영상 '{video_id}' 이미 존재 → DB 저장 생략 (전략: {strategy_name})",
                file=sys.stderr,
            )
            return
    except Exception as e:
        print(f"\n[BG] ⚠️ 중복 체크 실패, 저장 진행: {e}", file=sys.stderr)

    documents = []

    # 전체 요약
    full_content = " ".join(
        f"{sec.section_name}: {sec.summary}" for sec in transcript_result.sections
    )
    documents.append(
        Document(
            page_content=full_content,
            metadata={
                "source":        "youtube_transcript",
                "video_id":      video_id,
                "strategy_name": strategy_name,
                "type":          "transcript_summary",
                "added_at":      datetime.now().isoformat(),
            },
        )
    )

    # 섹션별 저장
    for sec in transcript_result.sections:
        content = f"{sec.section_name}\n{sec.summary}\n" + "\n".join(
            f"- {pt}" for pt in sec.key_points
        )
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source":          "youtube_section",
                    "video_id":        video_id,
                    "strategy_name":   strategy_name,
                    "section_name":    sec.section_name,
                    "emotion":         sec.emotion,
                    "target_audience": ",".join(sec.target_audience),
                    "type":            "transcript_section",
                    "added_at":        datetime.now().isoformat(),
                },
            )
        )

    count = vector_db.add_documents(documents=documents, doc_type="youtube")
    print(f"\n[BG] ✅ YouTube 자막 DB 저장 완료: {count}개 문서 (전략: {strategy_name})",
          file=sys.stderr)


def _bg_save_transcript(vector_db, transcript_result, user_data):
    """BackgroundTasks용 동기 래퍼 — asyncio.run으로 비동기 함수 실행"""
    import asyncio
    print("\n[BG] YouTube 자막 DB 저장 시작...", file=sys.stderr)
    try:
        asyncio.run(_save_transcript_to_db(vector_db, transcript_result, user_data))
    except Exception as e:
        print(f"\n[BG] ❌ YouTube 자막 DB 저장 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


# ── FastAPI 앱 ─────────────────────────────────────────────
app = FastAPI(
    title="Agentic RAG Investment Advisor",
    description="단일 종목 YouTube 기반 AI 투자 조언 시스템",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 싱글톤 — 타입은 런타임에 결정 (lazy import)
vector_db     = None
agent_manager = None
pdf_manager   = None
is_ready      = False


def _do_heavy_imports():
    """이벤트 루프 블로킹 방지 — 스레드 풀에서 무거운 import 실행"""
    from chromadb_manager import ChromaDBManager
    from download_embedding_model import EmbeddingModelManager
    from agent import AgentManager
    from add_pdf import PDFManager
    return ChromaDBManager, EmbeddingModelManager, AgentManager, PDFManager


async def _init_in_background():
    global vector_db, agent_manager, pdf_manager, is_ready

    print("\n" + "=" * 60, file=sys.stderr)
    print("🚀 FastAPI 서버 초기화 시작 (백그라운드)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    _missing = [k for k in ["OPENAI_API_KEY"] if not os.getenv(k)]
    if _missing:
        print(f"❌ 필수 환경변수 누락: {', '.join(_missing)}", file=sys.stderr)
        return

    db_path = os.getenv("VECTOR_DB_PATH", VECTOR_DB_PATH)
    print(f"\n[초기화-1] DB 경로: {db_path}", file=sys.stderr)

    try:
        loop = asyncio.get_running_loop()

        print("\n[초기화-2] 📦 무거운 패키지 로드 중...", file=sys.stderr)
        ChromaDBManager, EmbeddingModelManager, AgentManager, PDFManager = \
            await loop.run_in_executor(None, _do_heavy_imports)
        print("  ✅ 패키지 로드 완료", file=sys.stderr)

        print("\n[초기화-3] 📥 임베딩 모델 로드 중...", file=sys.stderr)
        embedding_model = await loop.run_in_executor(None, EmbeddingModelManager.download_model)
        print("  ✅ 임베딩 모델 로드 완료", file=sys.stderr)

        print("\n[초기화-4] 🗄️  ChromaDB 초기화 중...", file=sys.stderr)
        vector_db = ChromaDBManager(db_path=db_path, embedding_model=embedding_model)
        print("  ✅ ChromaDB 초기화 완료", file=sys.stderr)

        print("\n[초기화-5] 🤖 Agent Manager 생성 중...", file=sys.stderr)
        agent_manager = AgentManager(vector_db)
        print("  ✅ Agent Manager 생성 완료", file=sys.stderr)

        print("\n[초기화-6] 📄 PDF Manager 생성 중...", file=sys.stderr)
        pdf_manager = PDFManager(vector_db)
        print("  ✅ PDF Manager 생성 완료", file=sys.stderr)

        print("\n[초기화-7] 🌱 전략 지식 시드 확인...", file=sys.stderr)
        if vector_db.count_documents() == 0:
            count = pdf_manager.seed_strategy_knowledge()
            print(f"  ✅ 전략 지식 {count}개 문서 자동 적재 완료", file=sys.stderr)
        else:
            print(f"  ⏭️  DB에 문서 있음 ({vector_db.count_documents()}개) → 시드 생략", file=sys.stderr)

        is_ready = True
        print("\n" + "=" * 60, file=sys.stderr)
        print("✅ 서버 준비 완료!", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

    except Exception as e:
        print(f"\n❌ 초기화 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_init_in_background())


@app.on_event("shutdown")
async def shutdown():
    print("\n🛑 서버 종료", file=sys.stderr)


# ── 헬스 체크 ──────────────────────────────────────────────

@app.get("/health")
async def health():
    if not is_ready:
        return {"status": "initializing"}
    return {
        "status": "healthy",
        "database": vector_db.get_stats() if vector_db else None,
    }


# ── 핵심 분석 엔드포인트 ────────────────────────────────────

@app.post("/analyze")
@app.post("/api/analyze")
async def analyze(data: dict, background_tasks: BackgroundTasks):
    """
    흐름:
      1. Agent 실행 (분석 + 검색 + 조언 생성)
      2. 응답 즉시 백엔드에 반환  ← 여기서 끊음
      3. YouTube 자막 DB 저장     ← 백그라운드에서 처리
    """
    print("\n" + "=" * 60, file=sys.stderr)
    print("[API] POST /analyze", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if not agent_manager:
        raise HTTPException(status_code=503, detail="시스템 초기화 중입니다.")

    try:
        # 1. UserData 파싱
        print("\n[분석-1] UserData 파싱 중...", file=sys.stderr)
        user_data = UserData(
            trades      =[Trade(**t)      for t in data.get("trades", [])],
            stockPrices =[StockPrice(**p) for p in data.get("stockPrices", [])],
            strategy    =data.get("strategy", "external"),
            externalUrl =data.get("externalUrl", ""),
        )
        print(f"  ✅ 매매 {len(user_data.trades)}건 / 종가 {len(user_data.stockPrices)}일",
              file=sys.stderr)

        # 2. Agent 실행
        print("\n[분석-2] Agent 실행 중...", file=sys.stderr)
        result = await agent_manager.run(user_data)
        print(f"  ✅ Agent 완료 (반복: {len(result.agent_decisions)}회)", file=sys.stderr)

        # 3. 응답 JSON 구성 — final_advice는 {"evaluation":..,"advice":..} JSON 문자열
        from tools import _extract_json
        try:
            advice_data = _extract_json(result.final_advice)
            evaluation  = advice_data.get("evaluation", result.final_advice)
            advice      = advice_data.get("advice",     result.final_advice)
            signal      = advice_data.get("signal",     "hold")
            if signal not in ("buy", "sell", "hold"):
                signal = "hold"
        except Exception:
            evaluation = result.final_advice
            advice     = result.final_advice
            signal     = "hold"

        response = {
            "code":        user_data.trades[0].stockCode if user_data.trades else "",
            "type":        user_data.trades[0].tradeType if user_data.trades else "",
            "signal":      signal,
            "evaluation":  evaluation,
            "advice":      advice,
            "total_score": result.total_score.total,
        }

        # 4. YouTube 자막 DB 저장 → 백그라운드 등록 (external 전략일 때만)
        if result.transcript_analysis and vector_db and user_data.strategy == "external":
            background_tasks.add_task(
                _bg_save_transcript,
                vector_db,
                result.transcript_analysis,
                user_data,
            )
            print("\n[분석-3] YouTube 자막 DB 저장 → 백그라운드 등록", file=sys.stderr)

        # 5. 응답 즉시 반환
        print("\n[분석-4] ✅ 백엔드로 응답 반환", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        return response

    except Exception as e:
        print(f"\n❌ 분석 실패: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=400, detail=str(e))


# ── PDF 추가 ───────────────────────────────────────────────

@app.post("/add-pdf")
async def add_pdf(file: UploadFile = File(...)):
    print(f"\n[API] POST /add-pdf: {file.filename}", file=sys.stderr)
    if not pdf_manager:
        raise HTTPException(status_code=503, detail="시스템 초기화 중입니다.")

    temp_path = f"/tmp/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        count = await pdf_manager.add_pdf_file(pdf_path=temp_path, title=file.filename)
        print(f"  ✅ PDF 추가 완료: {count}개 문서", file=sys.stderr)
        return {"success": True, "added_count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ── DB 관리 ────────────────────────────────────────────────

@app.get("/db-stats")
async def db_stats():
    if not vector_db:
        raise HTTPException(status_code=503, detail="시스템 초기화 중입니다.")
    return vector_db.get_stats()


@app.delete("/clear-db")
async def clear_db():
    if not vector_db:
        raise HTTPException(status_code=503, detail="시스템 초기화 중입니다.")
    vector_db.clear()
    return {"success": True, "message": "DB 초기화 완료"}


# ── 로컬 실행 ──────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"\n[서버] 포트 {port}에서 시작 중...\n", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")