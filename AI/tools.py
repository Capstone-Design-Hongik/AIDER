import os
import re
import json
import time
from typing import Dict, List, Any, Optional

from openai import OpenAI
from models import (
    UserData, UserAnalysisResult,
    TranscriptAnalysisResult, TranscriptSection,
)
from transcript import TranscriptManager
from config import LLMConfig, SEARCH_CONFIDENCE_THRESHOLD

_openai_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _chat(model: str, prompt: str, max_tokens: int = 1500) -> str:
    print(f"\n  💬 LLM 호출: {model} / {len(prompt):,}자")
    resp = _get_client().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    result = resp.choices[0].message.content.strip()
    print(f"     응답 {len(result):,}자 / 토큰 {resp.usage.total_tokens}")
    return result


def _extract_json(text: str) -> Dict:
    """LLM 응답에서 JSON 추출 — 중첩 구조 대응"""
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i+1])

    raise ValueError(f"JSON을 찾을 수 없습니다. 응답:\n{text[:200]}")


class BaseTool:
    def __init__(self, name: str):
        self.name = name

    async def execute(self, **kwargs) -> Any:
        raise NotImplementedError


# ── Tool 1: 사용자 분석 (LLM 자유 판단) ───────────────────

class UserAnalysisTool(BaseTool):
    """매매 기록을 LLM이 자유롭게 분석 — 패턴 종류·개수 제한 없음"""

    def __init__(self):
        super().__init__("user_analysis")

    async def execute(self, user_data: UserData) -> UserAnalysisResult:
        trades = user_data.trades
        prices = user_data.stockPrices
        stock_name = trades[0].stockName if trades else "알 수 없음"
        stock_code = trades[0].stockCode if trades else ""

        print(f"\n{'='*60}")
        print(f"👤 [Tool 1] 사용자 분석 (LLM 자유 판단)")
        print(f"{'='*60}")

        buys = [t for t in trades if t.tradeType.lower() == "buy"]
        sells = [t for t in trades if t.tradeType.lower() == "sell"]
        avg_buy = (
            sum(t.price * t.quantity for t in buys) / sum(t.quantity for t in buys)
            if buys else 0
        )
        latest_price = prices[-1].closePrice if prices else avg_buy
        pnl_pct = ((latest_price - avg_buy) / avg_buy * 100) if avg_buy else 0

        trades_str = "\n".join(
            f"{i}. {t.date} | {t.tradeType.upper()} | {t.quantity}주 @ {t.price:,.0f}원"
            for i, t in enumerate(trades, 1)
        )
        prices_str = "\n".join(f"{p.date}: {p.closePrice:,.0f}원" for p in prices)

        prompt = f"""
주식 투자 행동 분석 전문가로서 아래 매매 기록을 분석하세요.

[종목] {stock_name} ({stock_code})
[평균 매수가] {avg_buy:,.0f}원 / [현재가] {latest_price:,.0f}원 / [수익률] {pnl_pct:+.2f}%

[매매 기록]
{trades_str}

[종가 데이터]
{prices_str}

분석 지침:
- patterns: 실제 관찰되는 패턴만, 개수 제한 없음, 명칭 자유 (없으면 빈 배열)
- pattern_strength: 각 패턴 강도 0.0~1.0
- risk_level: "높음" | "중간" | "낮음"
- priority_patterns: 가장 중요한 패턴 순
- learning_stage: "초보" | "중급" | "고급"
- additional_insights.summary: 한 줄 핵심 요약

JSON만 출력:
{{
  "patterns": [],
  "pattern_strength": {{}},
  "risk_level": "",
  "priority_patterns": [],
  "confidence": 0.9,
  "learning_stage": "",
  "additional_insights": {{
    "summary": "",
    "avg_buy_price": {avg_buy:.0f},
    "latest_price": {latest_price:.0f},
    "pnl_pct": {pnl_pct:.2f},
    "buy_count": {len(buys)},
    "sell_count": {len(sells)}
  }}
}}
"""
        text = _chat(LLMConfig.ANALYSIS_MODEL, prompt, max_tokens=800)
        print(f"\n  [RAW 응답]\n{text}\n")   # ← 이 줄 추가
        data = _extract_json(text)

        # 수치는 Python 계산값으로 덮어쓰기 (정확도 보장)
        data.setdefault("additional_insights", {})
        data["additional_insights"].update({
            "avg_buy_price": round(avg_buy, 0),
            "latest_price":  round(latest_price, 0),
            "pnl_pct":       round(pnl_pct, 2),
            "buy_count":     len(buys),
            "sell_count":    len(sells),
        })

        result = UserAnalysisResult(**data)
        print(f"  ✅ 패턴: {', '.join(result.patterns)}")
        print(f"     위험도: {result.risk_level} / 수익률: {pnl_pct:+.2f}%")
        return result


# ── Tool 2: YouTube 자막 분석 ──────────────────────────────

class TranscriptAnalysisTool(BaseTool):
    DIRECT_THRESHOLD = 8_000
    CHUNK_SIZE       = 4_000
    CHUNK_OVERLAP    = 200

    def __init__(self, vector_db=None):
        super().__init__("transcript_analysis")
        # vector_db parameter preserved for compatibility, but interaction logic removed

    async def execute(self, youtube_url: str) -> TranscriptAnalysisResult:
        t0 = time.time()
        print(f"\n{'='*60}")
        print(f"📺 [Tool 2] 자막 분석")
        print(f"{'='*60}")

        video_id = TranscriptManager.extract_video_id(youtube_url)

        transcript = TranscriptManager.transcript(video_id)
        if not transcript:
            raise ValueError(f"자막 추출 실패: {video_id}")

        char_count = len(transcript)
        print(f"  ✅ {char_count:,}자 추출")

        if char_count <= self.DIRECT_THRESHOLD:
            extracted = await self._extract_direct(transcript)
        else:
            extracted = await self._extract_by_chunks(transcript)

        print(f"  ✅ 압축 완료: {len(extracted):,}자 ({len(extracted)/char_count:.1%})")
        result = await self._sectionize(extracted, video_id, char_count)
        result.processing_time = round(time.time() - t0, 2)
        print(f"  ✅ 섹션 {len(result.sections)}개 / {result.processing_time}s")
        return result

    async def _extract_direct(self, transcript: str) -> str:
        return _chat(LLMConfig.ANALYSIS_MODEL, f"""
투자 YouTube 자막에서 핵심 내용만 30~50%로 압축하세요.
✅ 포함: 투자 전략, 매매 원칙, 리스크 관리, 구체적 조언
❌ 제외: 인사, 광고, 잡담

[자막]
{transcript}

[핵심 내용]
""", max_tokens=4000)

    async def _extract_by_chunks(self, transcript: str) -> str:
        chunks = self._split_into_chunks(transcript)
        print(f"     청크 {len(chunks)}개")
        summaries = []
        for i, chunk in enumerate(chunks):
            print(f"     {i+1}/{len(chunks)}...", end=" ", flush=True)
            s = _chat(LLMConfig.ANALYSIS_MODEL, f"""
투자 YouTube 자막 {i+1}/{len(chunks)}. 핵심 내용만 추출. 없으면 "핵심 내용 없음".
[자막]
{chunk}
[핵심 내용]
""", max_tokens=1000)
            if s and s != "핵심 내용 없음":
                summaries.append(s)
            print("✅")
        return _chat(LLMConfig.ANALYSIS_MODEL, f"""
투자 YouTube 분할 요약을 하나로 통합하세요. 중복 제거, 구체적 원칙 우선.
[분할 요약]
{chr(10).join(summaries)}
[최종]
""", max_tokens=3000)

    def _split_into_chunks(self, text: str) -> List[str]:
        chunks, start = [], 0
        while start < len(text):
            end = min(start + self.CHUNK_SIZE, len(text))
            if end < len(text):
                for sep in ["\n", ". ", "? ", "! "]:
                    pos = text.rfind(sep, max(0, end - 200), end + 200)
                    if pos != -1:
                        end = pos + len(sep)
                        break
            chunks.append(text[start:end])
            start = end - self.CHUNK_OVERLAP
        return chunks

    async def _sectionize(self, extracted: str, video_id: str, original_len: int) -> TranscriptAnalysisResult:
        text = _chat(LLMConfig.ANALYSIS_MODEL, f"""
투자 YouTube 핵심 내용을 섹션으로 분석하세요.

[내용]
{extracted}

분석 지침:
- strategy_name: 이 영상에서 다루는 매매 기법의 '고유 명칭'이나 '구체적인 제목'을 추출하세요. (예: "3일선 반등 스윙 전략", "하락장 탈출 매매법")
- 주의: "투자 전략", "매매 원칙" 같은 추상적이고 일반적인 명칭은 일절 금지합니다. 영상에서 강조하는 핵심 키워드를 포함해 구체적으로 지으세요.

JSON만 출력:
{{
  "strategy_name": "구체적인 전략명",
  "sections": [
    {{
      "section_name": "섹션명",
      "content": "내용",
      "summary": "한 문장",
      "key_points": ["핵심1", "핵심2"],
      "emotion": "경고",
      "target_audience": ["초보 투자자"]
    }}
  ],
  "keywords": ["키워드1", "키워드2"],
  "confidence": 0.9
}}
""", max_tokens=3000)
  "keywords": ["키워드1", "키워드2"],
  "confidence": 0.9
}}
""", max_tokens=3000)
        result = _extract_json(text)
        return TranscriptAnalysisResult(
            sections=[TranscriptSection(**s) for s in result.get("sections", [])],
            keywords=result.get("keywords", []),
            structure={
                "video_id":          video_id,
                "original_length":   original_len,
                "strategy_name":     result.get("strategy_name", "일반 투자 조언"),
            },
            confidence=result.get("confidence", 0.9),
            processing_time=0.0,
        )


# ── Tool 3~5 ───────────────────────────────────────────────

class VectorSearchTool(BaseTool):
    def __init__(self, vector_db):
        super().__init__("vector_search")
        self.vector_db = vector_db

    async def execute(self, query: str, k: int = 5, metadata_filter=None):
        print(f"\n  🔍 벡터 검색 k={k}")
        results, coverage = self.vector_db.search(query=query, k=k, metadata_filter=metadata_filter)
        print(f"     결과 {len(results)}건 / 커버리지 {coverage:.2%}")
        return results, coverage


class RefinedSearchTool(BaseTool):
    def __init__(self, vector_db):
        super().__init__("refined_search")
        self.vector_db = vector_db

    async def execute(self, original_query: str, coverage_score: float, user_analysis: UserAnalysisResult):
        if coverage_score >= SEARCH_CONFIDENCE_THRESHOLD:
            return [], "커버리지 충분"
        prompt = (
            f"원래 쿼리: {original_query}\n"
            f"패턴: {', '.join(user_analysis.patterns)} / 위험도: {user_analysis.risk_level}\n\n"
            "더 정확한 검색 쿼리 한 문장:"
        )
        refined = _chat(LLMConfig.AGENT_MODEL, prompt, max_tokens=100)
        results, _ = self.vector_db.search(query=refined, k=5)
        return results, refined


class InternalStrategyTool(BaseTool):
    """YouTube 없이 bollinger/trend 전략 원칙을 TranscriptAnalysisResult로 반환"""

    _CONFIGS = {
        "bollinger": {
            "strategy_name": "볼린저밴드 전략",
            "keywords": ["볼린저밴드", "상단밴드", "하단밴드", "중간선", "20MA", "밴드폭", "스퀴즈", "돌파"],
            "sections": [
                {
                    "section_name": "볼린저밴드 매수 신호",
                    "content": "하단밴드 터치 후 반등, 밴드 스퀴즈 이후 상단 돌파",
                    "summary": "하단밴드 지지 확인 후 중간선(20MA) 돌파 시 매수",
                    "key_points": [
                        "하단밴드 터치 후 양봉 반등 확인",
                        "밴드폭 축소(스퀴즈) 이후 돌파 시 추세 시작",
                        "중간선(20MA)이 지지선 역할 확인",
                    ],
                    "emotion": "기회",
                    "target_audience": ["중급 투자자"],
                },
                {
                    "section_name": "볼린저밴드 매도 신호",
                    "content": "상단밴드 터치 후 음봉, 중간선 하향 이탈",
                    "summary": "상단밴드 도달 후 되돌림 또는 중간선 이탈 시 매도",
                    "key_points": [
                        "상단밴드 터치 후 음봉 발생 시 단기 고점 신호",
                        "중간선(20MA) 하향 이탈 시 하락 추세 전환",
                        "밴드 확장 후 수축 전환은 추세 종료 신호",
                    ],
                    "emotion": "경고",
                    "target_audience": ["중급 투자자"],
                },
                {
                    "section_name": "볼린저밴드 리스크 관리",
                    "content": "하단밴드 하향 이탈 시 손절, 상단밴드 과열 구간 비중 축소",
                    "summary": "하단밴드 아래 종가 이탈 시 즉시 손절",
                    "key_points": [
                        "하단밴드 종가 이탈 시 즉시 손절",
                        "상단밴드 연속 터치는 강한 추세이므로 추격 매도 금지",
                    ],
                    "emotion": "위험",
                    "target_audience": ["모든 투자자"],
                },
            ],
        },
        "trend": {
            "strategy_name": "추세추종 전략",
            "keywords": ["추세", "이동평균", "골든크로스", "데드크로스", "20MA", "60MA", "추세선", "고점갱신"],
            "sections": [
                {
                    "section_name": "추세 진입 신호",
                    "content": "골든크로스 발생, 20MA 상향 돌파 후 지지 확인",
                    "summary": "단기·중기 이동평균 정배열 확인 후 눌림목에서 매수",
                    "key_points": [
                        "5MA가 20MA를 상향 돌파(골든크로스)할 때 매수",
                        "20MA 우상향이면서 현재가 20MA 위에서 지지 확인",
                        "고점·저점 연속 상승이면 상승 추세 유효",
                    ],
                    "emotion": "기회",
                    "target_audience": ["중급 투자자"],
                },
                {
                    "section_name": "추세 청산 신호",
                    "content": "데드크로스, 20MA 하향 이탈 후 저항선 전환",
                    "summary": "데드크로스 발생 또는 20MA 하향 이탈 시 매도",
                    "key_points": [
                        "5MA가 20MA 아래 이탈(데드크로스)하면 매도",
                        "20MA 우하향 전환 시 추세 종료",
                        "직전 저점 하향 돌파 시 하락 추세 전환",
                    ],
                    "emotion": "경고",
                    "target_audience": ["중급 투자자"],
                },
                {
                    "section_name": "추세추종 리스크 관리",
                    "content": "횡보 구간 진입 금지, 분할 매수로 리스크 분산",
                    "summary": "횡보 구간 관망 후 추세 확인 시 분할 매수",
                    "key_points": [
                        "20MA 기울기 평탄한 횡보 구간 진입 금지",
                        "추세 확인 후 3분할 매수로 진입 단가 분산",
                        "60MA 하향 이탈은 중기 추세 전환으로 전량 매도 고려",
                    ],
                    "emotion": "위험",
                    "target_audience": ["모든 투자자"],
                },
            ],
        },
    }

    def __init__(self):
        super().__init__("internal_strategy")

    async def execute(self, strategy: str) -> TranscriptAnalysisResult:
        cfg = self._CONFIGS.get(strategy, self._CONFIGS["trend"])
        print(f"\n  ✅ 내부 전략 로드: {cfg['strategy_name']}")
        return TranscriptAnalysisResult(
            sections=[TranscriptSection(**s) for s in cfg["sections"]],
            keywords=cfg["keywords"],
            structure={
                "video_id":       f"internal_{strategy}",
                "original_length": 0,
                "strategy_name":  cfg["strategy_name"],
            },
            confidence=0.95,
            processing_time=0.0,
        )


class ValidationTool(BaseTool):
    def __init__(self):
        super().__init__("validation")

    async def execute(self, search_results, user_analysis: UserAnalysisResult, query_used: str) -> Dict[str, Any]:
        preview = "\n".join(f"[{i+1}] {r.content[:150]}" for i, r in enumerate(search_results[:5]))
        print(f"\n  ✔️  검증: {len(search_results)}건")
        try:
            text = _chat(LLMConfig.ANALYSIS_MODEL, f"""
YouTube 전략 검색 결과가 사용자 매매 패턴과 관련 있는지 검증하세요.
[패턴] {', '.join(user_analysis.patterns)} / [위험도] {user_analysis.risk_level}
[검색 결과]
{preview}

JSON만 출력:
{{"is_valid": true, "confidence": 0.9, "issues": [], "recommendations": []}}
""", max_tokens=300)
            result = _extract_json(text)
            print(f"     유효={result['is_valid']} / {result['confidence']:.2%}")
            return result
        except Exception as e:
            print(f"     검증 실패: {e}")
            return {"is_valid": True, "confidence": 0.8, "issues": [], "recommendations": []}