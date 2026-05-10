import asyncio
from typing import Dict

from models import UserData, AgentDecision, RAGOutput, ScoreBreakdown
from tools import (
    UserAnalysisTool, TranscriptAnalysisTool, InternalStrategyTool,
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
            "internal_strategy":   InternalStrategyTool(),
            "vector_search":       VectorSearchTool(vector_db),
            "refined_search":      RefinedSearchTool(vector_db),
            "validation":          ValidationTool(),
        }
        self.max_iterations = 5

    async def run(self, user_data: UserData) -> RAGOutput:
        print("\n" + "=" * 70)
        print("Agentic RAG 파이프라인 시작")
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
        strategy = user_data.strategy
        if strategy == "external":
            print("Step 1️⃣  병렬 분석 (사용자 분석 + YouTube 자막 분석)")
            strategy_task = asyncio.create_task(
                self.tools["transcript_analysis"].execute(user_data.externalUrl)
            )
        else:
            print(f"Step 1️⃣  병렬 분석 (사용자 분석 + 내부 전략: {strategy})")
            strategy_task = asyncio.create_task(
                self.tools["internal_strategy"].execute(strategy)
            )
        print("─" * 70)

        state["user_analysis"], state["transcript_analysis"] = await asyncio.gather(
            asyncio.create_task(self.tools["user_analysis"].execute(user_data)),
            strategy_task,
        )

        if state["user_analysis"] is None:
            raise ValueError("사용자 분석 실패")
        if state["transcript_analysis"] is None:
            raise ValueError("전략 분석 실패")

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

        if not state["search_results"]:
            print("⚠️  벡터 검색 결과 없음 → 전략 분석만으로 조언 생성")

        # ── Step 3+4: total_score 산정 + 최종 조언 생성 (병렬) ──
        print("\n" + "─" * 70)
        print("Step 3️⃣+4️⃣  total_score 산정 + 최종 조언 생성 (병렬)")
        print("─" * 70)
        total_score, final_advice = await asyncio.gather(
            self._calculate_total_score(state, user_data),
            self._generate_advice(state, user_data),
        )
        print(
            f"  ✅ scores: youtube={total_score.youtube_strategy:.0f} / "
            f"trend={total_score.trend_awareness:.0f} / "
            f"entry={total_score.entry_timing:.0f}"
        )
        print(f"  ✅ 조언: {len(final_advice)}자")

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

    async def _decide(self, state: Dict, iteration: int) -> AgentDecision:
        count = len(state["search_results"])
        
        # [긴급수정] 1회차 검색 후에도 결과가 0건이면, 더 이상 무의미한 검색 반복 대신 종료
        if iteration > 1 and count == 0:
            return AgentDecision(
                next_action="stop",
                reasoning="DB에서 관련 이론적 배경을 찾지 못했습니다. 분석된 자막 내용을 바탕으로 진행합니다.",
                confidence=1.0, parameters={},
            )

        if count < 3:
            return AgentDecision(
                next_action="vector_search",
                reasoning=f"검색 결과 {count}건 → 전략의 이론적 배경 및 일반 원칙 검색",
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

        # [긴급수정] '영상의 내용'을 묻지 않고, '전략의 기반 이론/상식'을 찾도록 쿼리 유도
        if iteration == 1:
            prompt = (
                f"투자 전략 '{strategy_name}' 및 핵심 키워드({keywords})와 관련된 "
                f"보편적인 기술적 분석 이론, 매수/매도 원칙, 또는 리스크 관리 지침을 "
                f"벡터 DB에서 검색하기 위한 핵심 키워드 중심의 쿼리를 한국어 1문장으로 작성하세요.\n"
                f"주의: 특정 영상의 내용을 묻지 말고, 해당 전략의 '이론적 근거'를 찾으세요."
            )
        else:
            prompt = (
                f"전략명 '{strategy_name}'의 핵심 섹션({sections})과 관련된 "
                f"일반적인 투자 주의사항이나 차트 해석 원칙을 찾는 쿼리를 한국어 1문장으로 작성하세요."
            )

        query = _chat(LLMConfig.AGENT_MODEL, prompt, max_tokens=150)
        print(f"│  🔍 쿼리: {query}")
        return query

    # ── total_score 산정 ───────────────────────────────────────────

    async def _calculate_total_score(self, state: Dict, user_data: UserData) -> ScoreBreakdown:
        """3개 항목 각 0~100점 독립 평가."""
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
아래 투자자의 매매 기록을 YouTube 전략과 비교하여 3개 항목을 각 0~100점으로 독립 채점하세요.
세 항목은 서로 독립이며, 각각 100점 만점입니다.

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

채점 기준 (각 0~100점):
1. youtube_strategy: YouTube 전략 준수도 — 위 전략 원칙을 매매에 얼마나 충실히 따랐는가
2. trend_awareness: 추세 파악 능력 — 상승/하락 추세를 인식하고 적절히 대응했는가
3. entry_timing: 매수 타점 적절성 — 눌림목, 지지선, 적절한 가격대에 매수했는가

JSON만 출력:
{{
  "youtube_strategy": 0,
  "trend_awareness": 0,
  "entry_timing": 0,
  "reasoning": {{
    "youtube_strategy": "근거",
    "trend_awareness": "근거",
    "entry_timing": "근거"
  }}
}}
"""
        try:
            text = _chat(LLMConfig.ANALYSIS_MODEL, prompt, max_tokens=600)
            data = _extract_json(text)

            return ScoreBreakdown(
                youtube_strategy=float(data.get("youtube_strategy", 0)),
                trend_awareness=float(data.get("trend_awareness", 0)),
                entry_timing=float(data.get("entry_timing", 0)),
            )
        except Exception as e:
            print(f"  ⚠️  점수 산정 실패: {e} → 기본값 반환")
            return ScoreBreakdown(
                youtube_strategy=0, trend_awareness=0, entry_timing=0,
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

    async def _generate_advice(self, state: Dict, user_data: UserData) -> str:
        insights   = state["user_analysis"].additional_insights
        chart      = self._calc_chart(user_data)

        trades_str = "\n".join(
            f"- {t.date} {t.tradeType.upper()} {t.quantity}주 @ {t.price:,.0f}원"
            for t in user_data.trades
        )

        # 전략 원칙: external은 YouTube 자막 직접 요약, 내부 전략은 섹션 원칙
        ta = state["transcript_analysis"]
        strategy_name = ta.structure.get("strategy_name", "투자 전략")
        transcript_str = "\n".join(
            f"- [{s.section_name}] {s.summary} | 핵심: {', '.join(s.key_points[:2])}"
            for s in ta.sections
        )

        # DB 검색 결과: 전략 보완용 이론적 배경
        search_str = "\n".join(
            f"[{i+1}] {r.content[:200]}"
            for i, r in enumerate(state["search_results"][:3])
        ) if state["search_results"] else ""

        prompt = f"""
당신은 {strategy_name} 전략을 전문으로 하는 투자 분석가입니다.
조언의 최종 목적은 "이 사용자의 매매 기록"에 맞춘 맞춤형 대응 전략 제시입니다.

[중요 지침]
1. 유튜브 자막 분석 내용(transcript_str)을 1순위 근거로 삼으세요.
2. 벡터 DB 검색 결과(search_str)는 해당 전략을 보완하는 '이론적 배경'으로만 활용하세요.
3. 만약 검색 결과가 자막과 충돌한다면 유튜브 자막의 최신 전략을 우선시하세요.

━━━ 가장 중요: 사용자 매매 기록 (조언의 핵심 대상) ━━━
[매매 내역]
{trades_str}
- 평균 매수가: {insights.get('avg_buy_price', 0):,.0f}원 / 현재가: {insights.get('latest_price', 0):,.0f}원 / 수익률: {insights.get('pnl_pct', 0):+.2f}%

━━━ 해석의 렌즈 1: {strategy_name} 전략 원칙 (최우선) ━━━
{transcript_str}

━━━ 해석의 렌즈 2: 보조 이론 및 원칙 (VectorDB 검색 결과) ━━━
{search_str if search_str else "관련 보조 이론 없음"}

━━━ 보조 데이터: 차트 지표 ━━━

[차트 ({chart.get('period', '')})]
- 현재가: {chart.get('current', 0):,.0f}원
- 5MA: {chart.get('ma5', 0):,.0f}원 / 20MA: {chart.get('ma20', 0):,.0f}원 / 60MA: {chart.get('ma60', 0):,.0f}원
- 현재가 위치: {chart.get('ma20_signal', '')} / {chart.get('cross', '')}
- 단기 추세: {chart.get('trend', '')}
- 20일 지지선: {chart.get('support', 0):,.0f}원 / 저항선: {chart.get('resistance', 0):,.0f}원
- 60일 등락률: {chart.get('change_60d', 0):+.2f}%

작성 규칙:
- evaluation과 advice 모두 위 전략 원칙에 근거해 서술할 것
- 마크다운 볼드(**), 이탤릭(*), 이모지 일절 사용 금지
- 모든 가격은 원 단위 정수로 명시, "근처/약/정도" 같은 모호한 표현 지양
- evaluation은 분석가 어조로 객관적·간결하게 (기존 톤 유지)
- 출력은 반드시 한글과 아라비아 숫자, 일반 문장부호로만 작성할 것. 한자(漢字), 중국어 간체/번체, 일본어 가나 등 비한글 문자는 일절 사용 금지 (예: "支持線" → "지지선", "抵抗線" → "저항선", "高點" → "고점")

advice 작성 필수 요건:
[톤 & 스타일]
- 친근하고 다정한 챗봇 어조 (예: "~네요", "~시는 게 좋아 보여요", "~을 추천드려요")
- 사용자를 직접 대하듯 2인칭 표현 사용 가능 (예: "지금 보유하신 종목은~")
- 단정적 명령조("~하라", "~할 것") 대신 권유·제안조("~해보시는 건 어떨까요", "~을 고려해보세요")
- 친절함 ≠ 모호함: 가격, 수량, 전략 인용 등 핵심 정보는 그대로 구체적으로 유지

[분량 & 구조]
- 최소 5문장, 400자 이상으로 작성
- 첫 문장은 반드시 "{strategy_name} 전략에 따르면 ~~" 또는
  "[섹션명] 원칙에 의하면 ~~" 형식으로 시작하여 어떤 전략 섹션을 적용하는지 명시
- 위 [전략 원칙] 목록 중 현재 상황에 해당하는 핵심 원칙을 1개 이상 직접 인용할 것
  (예: 전략 원칙상 "상단밴드 도달 후 되돌림 시 매도"에 해당해서 ...)
- 사용자의 매매 기록을 반드시 직접 언급할 것:
  · 평균 매수가, 현재 수익률(±%), 보유 수량을 본문에 구체적인 숫자로 인용
  · 최근 매수/매도 시점의 가격 대비 현재가가 어떤 의미인지 해석
  · 일반론이 아닌 "이 사용자의 포지션"에 맞춘 조언이어야 함
- 다음 5가지 요소를 아래 순서대로 한 문단 안에 자연스럽게 통합:
  (1) 적용 전략 원칙 인용 및 근거
  (2) 사용자 매매 기록 해석 - 평균 매수가 {insights.get('avg_buy_price', 0):,.0f}원, 수익률 {insights.get('pnl_pct', 0):+.2f}% 등 실제 수치를 언급하며 현재 포지션의 상태를 평가
  (3) 현재 차트 수치(MA, 지지/저항, 추세 등)를 전략 원칙 및 사용자 포지션과 연결한 해석
  (4) 사용자 포지션 기준 구체적 행동 지침 - 보유 수량 비중 + 가격대를 함께 제시
      (예: "평균 매수가 220,000원 대비 현재 +2.7% 수익 구간이라, 226,000원에 도달하면 보유 수량의 50%를 분할 매도하시고, 230,000원에서 잔여 50%를 청산하시는 걸 추천드려요")
  (5) 시나리오 분기 - 돌파 시 / 이탈 시 각각의 대응 가격과 행동을 사용자 포지션 기준으로 명시

[연결성·일관성]
- 두서없이 나열하지 말고, 위 (1)→(2)→(3)→(4)→(5) 순서대로 논리적 흐름을 유지할 것
- 문장과 문장은 접속 표현("그래서", "이 때문에", "따라서", "한편", "다만")으로 자연스럽게 이어줄 것
- 같은 내용을 반복하지 말고, 앞 문장에서 제시한 근거가 뒷 문장의 행동 지침으로 이어지도록 구성할 것
- 도입(원칙 인용) → 해석(차트 연결) → 결론(행동·시나리오)의 일관된 흐름을 유지

━━━ signal 판단 (가장 중요: 사후 수익률 검증용) ━━━
이 signal은 백엔드에서 '향후 주가 움직임'과 대조하여 당신의 분석 정확도를 측정하는 척도가 됩니다.
단순히 현재 상태를 말하는 것이 아니라, "지금 이 시점의 결정이 며칠 뒤 수익으로 이어질 것인가"를 예측하세요.

판단 가이드라인:
- buy  : [전략 원칙 충족] + [강한 추세 확인]. 
         단순히 낮다고 사는 게 아니라, 하락 멈춤 신호(이동평균선 지지, 거래량 동반 반등, RSI 과매도 탈출 등)가 명확할 때만 낼 것.
         예측 실패 시(주가 하락 시) 낮은 점수를 받으므로 극도로 신중할 것.

- sell : [전략 원칙상 청산] + [하락 반전 징후].
         단순히 높다고 파는 게 아니라, 고점 징후(상단 밴드 터치 후 음봉, MACD 데드크로스, 주요 지지선 이탈)가 확실할 때만 낼 것.
         삼성전자처럼 우상향 추세가 강한 종목은 '단기 고점'만으로 sell을 주면 예측 실패(X)가 뜰 확률이 높으니, 
         추세 붕괴가 확인되기 전까지는 sell을 자제할 것.

- hold : [신호 불분명] 또는 [추세 지속 중].
         상승 중이라서 팔기 아깝거나, 하락 중인데 바닥이 안 보일 때, 
         혹은 전략 원칙과 차트 신호가 1개라도 충돌하면 반드시 hold를 선택하여 예측 실패 리스크를 최소화할 것.

주의: 
- 당신이 'sell'을 주었는데 주가가 오르면 백엔드 평가는 'X'가 됩니다. 
- 추세가 살아있는데(예: 5MA/20MA 정배열 및 우상향) 단순히 '가격이 높다'는 이유만으로 sell을 주지 마세요.
- 확신이 없을 때는 hold를 선택하는 것이 가장 안전한 전략입니다.

아래 JSON 형식으로만 출력하세요 (advice는 단일 문자열, 위 4요소를 자연스러운 문단으로 통합):
{{
  "signal": "buy 또는 sell 또는 hold",
  "evaluation": "전략 원칙 기준으로 현재 매매 상황 평가",
  "advice": "전략 원칙 인용 + 차트 해석 + 구체적 진입·청산 가격과 수량 + 돌파/이탈 시나리오별 대응을 포함한 400자 이상의 상세 대응 전략"
}}
"""
        return _chat(LLMConfig.FINAL_ADVICE_MODEL, prompt, max_tokens=3000)