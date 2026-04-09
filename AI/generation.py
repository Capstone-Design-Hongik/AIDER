# generation.py
import os
import json
import re
from openai import OpenAI
from typing import List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict
from core import UserData

load_dotenv()

if "HF_TOKEN" not in os.environ:
    print("[Warning] HF_TOKEN 환경 변수가 없습니다. .env 파일을 확인하세요.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN", "dummy_key"),
    timeout=90.0,
)

MODEL_NAME = "openai/gpt-oss-20b:groq"


# ── 유틸 함수 ────────────────────────────────────────────────────────────

def get_price_context(trade_date_str: str, stock_prices: List[Any]) -> str:
    """매매일 기준 앞 10일 ~ 뒤 5일 주가 흐름 반환"""
    try:
        target_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
        window_start = target_date - timedelta(days=10)
        window_end = target_date + timedelta(days=5)

        relevant = []
        for p in stock_prices:
            date_str = p.date if hasattr(p, "date") else p.get("date", "")
            price = p.closePrice if hasattr(p, "closePrice") else p.get("closePrice", 0)
            
            try:
                p_date = datetime.strptime(date_str, "%Y-%m-%d")
                if window_start <= p_date <= window_end:
                    marker = " ◀ 매매일" if p_date.date() == target_date.date() else ""
                    relevant.append(f"  {date_str}: {price:,.0f}원{marker}")
            except:
                continue

        return "\n".join(relevant) if relevant else "  (해당 날짜 주변 주가 데이터 없음)"

    except Exception as e:
        print(f"[Error] get_price_context: {e}")
        return "  (날짜 형식 오류)"


def clean_json_text(text: str) -> str:
    """LLM 응답에서 순수 JSON만 추출"""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return text[start : end + 1]
    return text


# ── 동적 RAG 쿼리 생성 ──────────────────────────────────────────────────

def make_search_queries(user_data: UserData) -> List[str]:
    """매매 패턴을 분석해서 RAG 검색 쿼리를 동적으로 생성"""
    queries = ["핵심 매매 기법과 투자 원칙 매수 타점 진입 전략"]

    stock_buy_dates: dict = defaultdict(list)
    stock_sell_dates: dict = defaultdict(list)

    for trade in user_data.trades:
        name = trade.stockName
        date = datetime.strptime(trade.date, "%Y-%m-%d")
        if trade.tradeType == "buy":
            stock_buy_dates[name].append(date)
        else:
            stock_sell_dates[name].append(date)

    # 패턴 1: 물타기
    if any(len(dates) >= 2 for dates in stock_buy_dates.values()):
        queries.append("물타기 추가 매수 위험성 손실 확대 대처법")

    # 패턴 2: 매도 존재 → 손절/익절 전략
    if any(stock_sell_dates.values()):
        queries.append("손절 기준 익절 타점 매도 전략 리스크 관리")

    # 패턴 3: 단기/장기 매매 분석
    has_short_term = False
    has_long_term = False
    for name in stock_buy_dates:
        buys = sorted(stock_buy_dates[name])
        sells = sorted(stock_sell_dates.get(name, []))
        for buy_date in buys:
            for sell_date in sells:
                gap = (sell_date - buy_date).days
                if 0 <= gap <= 5:
                    has_short_term = True
                if gap >= 30:
                    has_long_term = True

    if has_short_term:
        queries.append("단기 매매 스윙 트레이딩 변동성 주의사항")
    if has_long_term:
        queries.append("장기 보유 홀딩 전략 추세 추종 원칙")

    print(f"[Generation] 생성된 검색 쿼리 {len(queries)}개")
    return queries


# ── 프롬프트 생성 ────────────────────────────────────────────────────────

def make_rag_prompt(video_context: str, user_data: UserData) -> str:
    """RAG 프롬프트 구성"""
    print("\n[Generation] 종목별 매매 분석 프롬프트 구성 중...")

    stocks: dict = defaultdict(lambda: {"trades": [], "stockCode": ""})
    for trade in user_data.trades:
        name = trade.stockName
        stocks[name]["stockCode"] = trade.stockCode
        stocks[name]["trades"].append({
            "date": trade.date,
            "type": "매수" if trade.tradeType == "buy" else "매도",
            "price": trade.price,
            "quantity": trade.quantity,
        })

    stocks_analysis_text = ""
    for idx, (stock_name, stock_data) in enumerate(stocks.items(), 1):
        stocks_analysis_text += f"\n{'='*50}\n"
        stocks_analysis_text += f"[종목 {idx}] {stock_name} (코드: {stock_data['stockCode']})\n"
        stocks_analysis_text += f"{'='*50}\n\n"
        stocks_analysis_text += "📊 매매 내역 전체:\n"

        for i, trade in enumerate(stock_data["trades"], 1):
            price_ctx = get_price_context(trade["date"], user_data.stockPrices)
            stocks_analysis_text += f"""
  ({i}) {trade["date"]} - {trade["type"]}
      - 거래가격: {trade["price"]:,.0f}원
      - 거래수량: {trade["quantity"]}주

  📈 당시 주가 흐름:
{price_ctx}
"""

    PROMPT_TEMPLATE = """
당신은 주식 초보자를 위한 **친절하고 예리한 투자 멘토 AI**입니다.

**[역할]**
사용자의 매매 기록을 **종목별로 하나씩 묶어서** 분석하고,
영상의 투자 전략(Context)을 바탕으로 구체적인 조언을 제공하세요.

**[영상 전략 내용 (Context)]**
{context}

**[사용자의 종목별 매매 기록]**
{stocks_context}

**[점수 산정 기준]**
90-100점: 완벽한 전략 실행
75-89점:  대체로 우수, 소폭 개선 필요
60-74점:  핵심은 이해했으나 실행 미흡
40-59점:  전략과 괴리 있음
0-39점:   무계획적 매매

**[평가 요소]**
- 매수 타점의 적절성
- 기술적 지표 활용
- 추세 파악 능력
- 리스크 관리
- 영상 전략 준수도

**[필수 출력 규칙]**
반드시 다음 JSON 포맷으로만 출력하세요:

{{
    "analysis": [
        {{
            "trade_id": 1,
            "stock_name": "삼성전자",
            "type": "매수 2회",
            "advice": "첫 번째 매수(10/06)는 72,000원, 두 번째 매수(12/05)는 70,000원으로 진입했습니다. 두 번째 매수가 더 저가에 진입한 점은 긍정적입니다."
        }}
    ],
    "total_score": 75,
    "overall_feedback": "전체 매매 분석에 대한 종합 의견"
}}
"""

    return PROMPT_TEMPLATE.format(
        context=video_context or "영상 전략 정보가 없습니다.",
        stocks_context=stocks_analysis_text,
    )


# ── LLM 호출 ─────────────────────────────────────────────────────────────

def generate_answer(video_context: str, user_data: UserData) -> dict:
    """LLM으로 투자 조언 생성"""
    rag_prompt = make_rag_prompt(video_context, user_data)

    print(f"[Generation] LLM 호출 시작 (모델: {MODEL_NAME})")

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": rag_prompt}],
            temperature=0.1,
            max_tokens=2048,
        )

        if not completion.choices:
            return {"error": "No response from LLM"}

        raw_content = completion.choices[0].message.content.strip()
        clean_content = clean_json_text(raw_content)

        try:
            result = json.loads(clean_content)
            print("[Generation] ✅ LLM 응답 파싱 성공")
            return result
        except json.JSONDecodeError as je:
            print(f"[Error] JSON 파싱 실패: {je}")
            return {
                "error": "JSON 파싱 실패",
                "raw_text": raw_content[:300],
            }

    except Exception as e:
        print(f"[Error] LLM 호출 실패: {e}")
        return {"error": str(e)}
