import asyncio
from typing import Dict

from models import UserData, AgentDecision, RAGOutput, ScoreBreakdown
from tools import (
    UserAnalysisTool, TranscriptAnalysisTool,
    VectorSearchTool, RefinedSearchTool, ValidationTool,
    _chat, _extract_json,
)
from config import LLMConfig, RAG_K_DEFAULT


class AgentManager:

    def __init__(self, vector_db):
        self.vector_db = vector_db
        self.tools = {
            "user_analysis":       UserAnalysisTool(),
            "transcript_analysis": TranscriptAnalysisTool(),
            "vector_search":       VectorSearchTool(vector_db),
            "refined_search":      RefinedSearchTool(vector_db),
            "validation":          ValidationTool(),
        }
        self.max_iterations = 5

    async def run(self, user_data: UserData) -> RAGOutput:
        print("\n" + "=" * 70)
        print("🚀 Agentic RAG 파이프라인 시작")
        print("=" * 70)

        state: Dict = {
            "user_analysis":       None,
            "transcript_analysis": None,
            "search_results":      [],
            "decisions":           [],
            "coverage_score":      0.0,
            "last_query":          "",
            "validated":           None,
        }

        # ── Step 1: 병렬 분석 ─────────────────────────────────
        print("\n" + "─" * 70)
        print("Step 1️⃣  병렬 분석 (사용자 분석 + 자막 분석)")
        print("─" * 70)

        state["user_analysis"], state["transcript_analysis"] = await asyncio.gather(
            asyncio.create_task(self.tools["user_analysis"].execute(user_data)),
            asyncio.create_task(self.tools["transcript_analysis"].execute(user_data.externalUrl)),
        )

        # ── Step 2: Agent 의사결정 루프 ───────────────────────
        print("\n" + "─" * 70)
        print("Step 2️⃣  Agent 의사결정 루프 (최대 5회)")
        print("─" * 70)

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n┌─ 반복 {iteration}/{self.max_iterations} | 검색 {len(state['search_results'])}건")

            decision = await self._decide(state, iteration)
            print(f"│  📍 {decision.next_action} — {decision.reasoning}")
            state["decisions"].append(decision)

            if decision.next_action == "vector_search":
                query = await self._build_query(state["transcript_analysis"], iteration)
                state["last_query"] = query
                results, coverage = await self.tools["vector_search"].execute(
                    query=query,
                    k=RAG_K_DEFAULT + (iteration - 1) * 2,
                )
                state["search_results"].extend(results)
                state["coverage_score"] = coverage
                print(f"│  ✅ {len(results)}건 / 커버리지 {coverage:.2%}")

            elif decision.next_action == "refined_search":
                results, refined_q = await self.tools["refined_search"].execute(
                    original_query=state["last_query"],
                    coverage_score=state["coverage_score"],
                    user_analysis=state["user_analysis"],
                )
                if results:
                    state["search_results"].extend(results)
                    state["last_query"] = refined_q
                print(f"│  ✅ 재검색 {len(results)}건")

            elif decision.next_action == "validation":
                val = await self.tools["validation"].execute(
                    search_results=state["search_results"],
                    user_analysis=state["user_analysis"],
                    query_used=state["last_query"],
                )
                state["validated"] = val
                if val["is_valid"]:
                    print(f"└─ ✅ 검증 통과 → 루프 종료")
                    break

            elif decision.next_action == "stop":
                print(f"└─ ✅ stop → 루프 종료")
                break

            print(f"└─")

        # ── Step 3: total_score 산정 ───────────────────────────
        print("\n" + "─" * 70)
        print("Step 3️⃣  total_score 산정")
        print("─" * 70)
        total_score = await self._calculate_total_score(state, user_data)
        print(f"  ✅ total_score: {total_score.total:.1f}점 ({total_score.grade})")

        # ── Step 4: 최종 조언 생성 ────────────────────────────
        print("\n" + "─" * 70)
        print("Step 4️⃣  최종 조언 생성")
        print("─" * 70)
        final_advice = await self._generate_advice(state, user_data, total_score)
        print(f"  ✅ {len(final_advice)}자")

        print("\n" + "=" * 70)
        print("✅ 파이프라인 완료")
        print("=" * 70)

        return RAGOutput(
            analysis_result     =state["user_analysis"],
            transcript_analysis =state["transcript_analysis"],
            search_results      =state["search_results"],
            agent_decisions     =state["decisions"],
            final_advice        =final_advice,
            total_score         =total_score,
        )

    # ── 의사결정 (규칙 기반) ───────────────────────────────────────

    async def _decide(self, state: Dict, _iteration: int) -> AgentDecision:
        count = len(state["search_results"])
        if count < 3:
            return AgentDecision(
                next_action="vector_search",
                reasoning=f"검색 결과 {count}건 → YouTube 전략 기반 검색",
                confidence=0.9, parameters={},
            )
        if state["validated"] is None:
            return AgentDecision(
                next_action="validation",
                reasoning=f"결과 {count}건 → 사용자 패턴 매칭 검증",
                confidence=0.9, parameters={},
            )
        return AgentDecision(
            next_action="stop",
            reasoning="검색 + 검증 완료",
            confidence=0.95, parameters={},
        )

    async def _build_query(self, transcript_analysis, iteration: int) -> str:
        strategy_name = transcript_analysis.structure.get("strategy_name", "투자 전략")
        keywords      = ", ".join(transcript_analysis.keywords[:8])
        sections      = ", ".join(s.section_name for s in transcript_analysis.sections[:4])

        if iteration == 1:
            prompt = (
                f"YouTube 투자 영상의 핵심 내용을 검색하는 쿼리를 한국어 2문장으로 작성하세요.\n"
                f"전략명: {strategy_name}\n키워드: {keywords}\n섹션: {sections}\n\n쿼리:"
            )
        else:
            top = transcript_analysis.sections[0] if transcript_analysis.sections else None
            detail = f"'{top.section_name}': {top.summary}" if top else sections
            prompt = (
                f"YouTube 영상 특정 섹션의 구체적인 조언을 찾는 쿼리를 한국어 2문장으로 작성하세요.\n"
                f"{detail}\n\n쿼리:"
            )

        query = _chat(LLMConfig.AGENT_MODEL, prompt, max_tokens=150)
        print(f"│  🔍 쿼리: {query}")
        return query

    # ── total_score 산정 ───────────────────────────────────────────

    async def _calculate_total_score(self, state: Dict, user_data: UserData) -> ScoreBreakdown:
        """
        5개 항목 각 20점 만점, 합계 100점.

        등급 기준:
          90~100: 완벽한 전략 실행
          75~89 : 대체로 우수
          60~74 : 핵심은 이해했으나 개선 필요
          40~59 : 전략과 괴리
          0~39  : 무계획적 매매
        """
        insights = state["user_analysis"].additional_insights
        trades_str = "\n".join(
            f"{t.date} | {t.tradeType.upper()} | {t.quantity}주 @ {t.price:,.0f}원"
            for t in user_data.trades
        )
        prices_str = "\n".join(
            f"{p.date}: {p.closePrice:,.0f}원" for p in user_data.stockPrices
        )
        strategy_name = state["transcript_analysis"].structure.get("strategy_name", "")
        strategy_summary = "\n".join(
            f"- {s.section_name}: {s.summary}"
            for s in state["transcript_analysis"].sections[:5]
        )

        prompt = f"""
아래 투자자의 매매 기록을 YouTube 전략과 비교하여 5개 항목을 각 20점 만점으로 채점하세요.

[YouTube 전략: {strategy_name}]
{strategy_summary}

[매매 기록]
{trades_str}

[종가 데이터]
{prices_str}

[감지된 패턴] {', '.join(state['user_analysis'].patterns)}
[평균 매수가] {insights.get('avg_buy_price', 0):,.0f}원
[현재가] {insights.get('latest_price', 0):,.0f}원
[수익률] {insights.get('pnl_pct', 0):+.2f}%

채점 기준 (각 0~20점):
1. entry_timing: 매수 타점 적절성 — 눌림목/지지선에서 매수했는가
2. indicator_usage: 기술적 지표 활용 — 이동평균 등 지표 기반 매매인가
3. trend_awareness: 추세 파악 능력 — 상승/하락 추세를 인식하고 대응했는가
4. risk_management: 리스크 관리 — 손절 기준이 있는가, 과도한 추가 매수는 없는가
5. strategy_adherence: 영상 전략 준수도 — YouTube 전략을 얼마나 따랐는가

JSON만 출력:
{{
  "entry_timing": 0.0,
  "indicator_usage": 0.0,
  "trend_awareness": 0.0,
  "risk_management": 0.0,
  "strategy_adherence": 0.0,
  "reasoning": {{
    "entry_timing": "근거",
    "indicator_usage": "근거",
    "trend_awareness": "근거",
    "risk_management": "근거",
    "strategy_adherence": "근거"
  }}
}}
"""
        try:
            text = _chat(LLMConfig.ANALYSIS_MODEL, prompt, max_tokens=600)
            data = _extract_json(text)

            e = float(data.get("entry_timing", 0))
            i = float(data.get("indicator_usage", 0))
            t = float(data.get("trend_awareness", 0))
            r = float(data.get("risk_management", 0))
            s = float(data.get("strategy_adherence", 0))
            total = round(e + i + t + r + s, 1)

            if total >= 90:   grade = "완벽한 전략 실행"
            elif total >= 75: grade = "대체로 우수"
            elif total >= 60: grade = "핵심은 이해했으나 개선 필요"
            elif total >= 40: grade = "전략과 괴리"
            else:             grade = "무계획적 매매"

            return ScoreBreakdown(
                entry_timing=e, indicator_usage=i, trend_awareness=t,
                risk_management=r, strategy_adherence=s,
                total=total, grade=grade,
            )
        except Exception as e:
            print(f"  ⚠️  점수 산정 실패: {e} → 기본값 반환")
            return ScoreBreakdown(
                entry_timing=0, indicator_usage=0, trend_awareness=0,
                risk_management=0, strategy_adherence=0,
                total=0, grade="산정 실패",
            )

    # ── 차트 지표 계산 ─────────────────────────────────────────────

    def _calc_chart(self, user_data: UserData) -> Dict:
        """60일 종가로 이동평균·지지/저항·추세 계산"""
        prices = [p.closePrice for p in user_data.stockPrices]
        dates  = [p.date       for p in user_data.stockPrices]
        if not prices:
            return {}

        def ma(n):
            return round(sum(prices[-n:]) / min(n, len(prices)), 0)

        current    = prices[-1]
        ma5        = ma(5)
        ma20       = ma(20)
        ma60       = ma(60)
        recent20   = prices[-20:] if len(prices) >= 20 else prices
        support    = round(min(recent20), 0)
        resistance = round(max(recent20), 0)

        # 단기 추세: 최근 5일 평균 vs 직전 5일 평균
        if len(prices) >= 10:
            r5, p5 = sum(prices[-5:]) / 5, sum(prices[-10:-5]) / 5
            trend = "단기 상승" if r5 > p5 * 1.01 else "단기 하락" if r5 < p5 * 0.99 else "횡보"
        else:
            trend = "데이터 부족"

        cross = (
            "골든크로스 상태 (5MA > 20MA)" if ma5 > ma20
            else "데드크로스 상태 (5MA < 20MA)"
        )
        ma20_signal = "20MA 위" if current > ma20 else "20MA 아래"
        change_60d  = round((current - prices[0]) / prices[0] * 100, 2) if prices[0] else 0

        return {
            "current": current, "ma5": ma5, "ma20": ma20, "ma60": ma60,
            "support": support, "resistance": resistance,
            "trend": trend, "cross": cross, "ma20_signal": ma20_signal,
            "change_60d": change_60d,
            "period": f"{dates[0]} ~ {dates[-1]}",
        }

    # ── 최종 조언 생성 ─────────────────────────────────────────────

    async def _generate_advice(self, state: Dict, user_data: UserData, score: ScoreBreakdown) -> str:
        stock_name = user_data.trades[0].stockName if user_data.trades else "종목"
        insights   = state["user_analysis"].additional_insights
        chart      = self._calc_chart(user_data)

        trades_str = "\n".join(
            f"- {t.date} {t.tradeType.upper()} {t.quantity}주 @ {t.price:,.0f}원"
            for t in user_data.trades
        )
        search_str = "\n".join(
            f"[{i+1}] {r.content[:250]}"
            for i, r in enumerate(state["search_results"][:5])
        ) if state["search_results"] else "검색 결과 없음"

        prompt = f"""
당신은 기술적 분석 기반의 투자 분석가입니다.
아래 차트 데이터와 YouTube 전략을 바탕으로 {stock_name}의 향후 전망과 대응 전략을 작성하세요.
과거 매매 평가가 아닌, 지금부터 어떻게 해야 하는지를 중심으로 쓰세요.

[매매 내역]
{trades_str}
- 평균 매수가: {insights.get('avg_buy_price', 0):,.0f}원 / 현재가: {insights.get('latest_price', 0):,.0f}원 / 수익률: {insights.get('pnl_pct', 0):+.2f}%

[차트 지표 ({chart.get('period', '')})]
- 현재가: {chart.get('current', 0):,.0f}원
- 5MA: {chart.get('ma5', 0):,.0f}원 / 20MA: {chart.get('ma20', 0):,.0f}원 / 60MA: {chart.get('ma60', 0):,.0f}원
- 현재가 위치: {chart.get('ma20_signal', '')} / {chart.get('cross', '')}
- 단기 추세: {chart.get('trend', '')}
- 20일 지지선: {chart.get('support', 0):,.0f}원 / 저항선: {chart.get('resistance', 0):,.0f}원
- 60일 등락률: {chart.get('change_60d', 0):+.2f}%

[YouTube 전략 조언]
{search_str}

[total_score: {score.total:.1f}점 / {score.grade}]
매수 타점 {score.entry_timing:.0f} / 지표활용 {score.indicator_usage:.0f} / 추세파악 {score.trend_awareness:.0f} / 리스크관리 {score.risk_management:.0f} / 전략준수 {score.strategy_adherence:.0f} (각 20점 만점)

작성 규칙:
- 마크다운 볼드(**), 이탤릭(*) 일절 사용 금지
- 인사말, 축하 표현 금지
- 딱딱하고 간결한 어조

signal 판단 기준:
- buy  : 지지선 근처 눌림목이거나 골든크로스 진입 시점, 추가 매수 여지 있음
- sell : 저항선 돌파 실패, 데드크로스 또는 손절 기준 이탈, 즉시 매도 필요
- hold : 추세 불명확하거나 관망이 유리한 횡보 구간

아래 JSON 형식으로만 출력하세요:
{{
  "signal": "buy 또는 sell 또는 hold",
  "evaluation": "해당 매매의 차트 기반 평가",
  "advice": "지금부터의 대응 전략, 진입·청산 가격 포함"
}}
"""
        return _chat(LLMConfig.FINAL_ADVICE_MODEL, prompt, max_tokens=2000)