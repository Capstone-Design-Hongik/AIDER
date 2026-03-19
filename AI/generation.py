# generation.py
import os
import json
import re
from openai import OpenAI
from typing import List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

if "HF_TOKEN" not in os.environ:
    print("[Warning] HF_TOKEN 환경 변수가 없습니다.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN", "dummy_key"),
    timeout=90.0
)

MODEL_NAME = "openai/gpt-oss-20b:groq"


def get_price_context(trade_date_str: str, stock_prices: List[Any]) -> str:
    """매매일(trade_date)을 기준으로 앞뒤 주가 데이터를 문자열로 반환"""
    try:
        target_date = datetime.strptime(trade_date_str, "%Y-%m-%d")

        relevant_prices = []
        for p in stock_prices:
            p_date_str = p.date if hasattr(p, 'date') else p.get('date')
            p_price = p.closePrice if hasattr(p, 'closePrice') else p.get('closePrice')
            p_date = datetime.strptime(p_date_str, "%Y-%m-%d")

            if (target_date - timedelta(days=10)) <= p_date <= (target_date + timedelta(days=5)):
                relevant_prices.append(f"  {p_date_str}: {p_price:,.0f}원")

        if not relevant_prices:
            return "  (해당 날짜 주변의 주가 데이터가 없습니다)"

        return "\n".join(relevant_prices)

    except Exception as e:
        print(f"[Error] 날짜 처리 중 오류: {e}")
        return "  (날짜 형식 오류로 데이터 추출 실패)"


def clean_json_text(text: str) -> str:
    """LLM 응답에서 순수 JSON 부분만 추출"""
    try:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()

        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1:
            return text[start_idx: end_idx + 1]

        return text
    except Exception:
        return text


def make_search_queries(user_data: Any) -> List[str]:
    """
    [신규] 사용자의 매매 패턴을 분석해서 동적으로 RAG 검색 쿼리를 생성

    패턴 감지:
    - 기본: 항상 핵심 매매 기법 쿼리 포함
    - 물타기: 같은 종목 매수 2회 이상
    - 손절: 매도 기록이 있는 경우
    - 단기 매매: 매수 후 5일 이내 매도
    """
    queries = []

    # 기본 쿼리 (항상 포함)
    queries.append("핵심 매매 기법과 투자 원칙 매수 타점 진입 전략")

    # 종목별 매수 횟수 집계
    stock_buy_dates: dict = defaultdict(list)
    stock_sell_dates: dict = defaultdict(list)

    for trade in user_data.trades:
        name = trade.stockName
        date = datetime.strptime(trade.date, "%Y-%m-%d")
        if trade.tradeType == 'buy':
            stock_buy_dates[name].append(date)
        else:
            stock_sell_dates[name].append(date)

    # 패턴 1: 물타기 감지 (같은 종목 매수 2회 이상)
    has_averaging_down = any(len(dates) >= 2 for dates in stock_buy_dates.values())
    if has_averaging_down:
        queries.append("물타기 추가 매수 위험성 손실 확대 대처법")

    # 패턴 2: 매도 기록 존재 → 손절 / 익절 전략
    has_sells = any(len(dates) > 0 for dates in stock_sell_dates.values())
    if has_sells:
        queries.append("손절 기준 익절 타점 매도 전략 리스크 관리")

    # 패턴 3: 단기 매매 감지 (매수 후 5일 이내 매도)
    has_short_term = False
    for name in stock_buy_dates:
        buys = sorted(stock_buy_dates[name])
        sells = sorted(stock_sell_dates.get(name, []))
        for buy_date in buys:
            for sell_date in sells:
                if 0 <= (sell_date - buy_date).days <= 5:
                    has_short_term = True
                    break

    if has_short_term:
        queries.append("단기 매매 스윙 트레이딩 변동성 주의사항")

    print(f"[Generation] 생성된 검색 쿼리 {len(queries)}개: {queries}")
    return queries


def make_rag_prompt(video_context: str, user_data: Any) -> str:
    print("\n[Generation] 종목별 매매 분석 프롬프트 구성 중...")

    stocks = defaultdict(lambda: {"trades": [], "stockCode": ""})

    for trade in user_data.trades:
        stock_name = trade.stockName
        stocks[stock_name]["stockCode"] = trade.stockCode
        stocks[stock_name]["trades"].append({
            "date": trade.date,
            "type": "매수" if trade.tradeType == 'buy' else "매도",
            "price": trade.price,
            "quantity": trade.quantity
        })

    stocks_analysis_text = ""

    for idx, (stock_name, stock_data) in enumerate(stocks.items(), 1):
        stocks_analysis_text += f"\n{'='*50}\n"
        stocks_analysis_text += f"[종목 {idx}] {stock_name} (코드: {stock_data['stockCode']})\n"
        stocks_analysis_text += f"{'='*50}\n\n"

        stocks_analysis_text += "📊 이 종목의 매매 내역 전체:\n"
        for i, trade in enumerate(stock_data["trades"], 1):
            price_context = get_price_context(trade["date"], user_data.stockPrices)

            stocks_analysis_text += f"""
  ({i}) {trade["date"]} - {trade["type"]}
      - 거래가격: {trade["price"]:,.0f}원
      - 거래수량: {trade["quantity"]}주
      
  📈 당시 주가 흐름:
{price_context}
"""
        stocks_analysis_text += f"\n{'-'*50}\n"

    PROMPT_TEMPLATE = """
당신은 주식 초보자를 위한 **친절하고 예리한 투자 멘토 AI**입니다.

**[역할]**
사용자의 매매 기록을 **종목별로 하나씩 묶어서** 분석하고, 영상의 투자 전략(Context)을 바탕으로 조언을 제공하세요.

**[영상 전략 내용 (Context)]**
{context}

**[사용자의 종목별 매매 기록]**
{stocks_context}

**[분석 및 점수(total_score) 산정 기준]**
[점수 산정 기준]
90-100점: 완벽한 전략 실행
75-89점: 대체로 우수
60-74점: 핵심은 이해했으나 개선 필요
40-59점: 전략과 괴리
0-39점: 무계획적 매매
[평가 요소]
매수 타점의 적절성 (눌림목, 지지선)
기술적 지표 활용 (이동평균 등)
추세 파악 능력
리스크 관리
영상 전략 준수도

**[⚠️ 필수 출력 규칙 - 매우 중요]**
1. **반드시 JSON 형식만 출력하세요.**
2. **"종목당 1개의 분석 항목"만 생성하세요.**
   - 예를 들어, '삼성전자'를 3번 매매했더라도 `analysis` 리스트에는 '삼성전자' 항목이 **딱 1개**만 있어야 합니다.
   - 그 1개의 항목 안에서 모든 매매(1차, 2차 등)를 종합하여 조언을 작성하세요.
3. `type` 필드에는 "매수 2회, 매도 1회" 처럼 전체 횟수를 요약해 적으세요.
4. `advice` 필드에는 첫 번째 매매와 두 번째 매매 등의 차이점을 비교하며 구체적인 개선점을 **하나의 긴 문단**으로 작성하세요.
5. 돈은 단위(원)으로만 표기하고, 쉼표(,)를 사용하여 가독성을 높이세요. 10.4만원 대신 "104,000원" 처럼요.

**[출력 JSON 포맷 예시]**
{{
    "analysis": [
        {{
            "trade_id": 1,
            "stock_name": "삼성전자",
            "type": "매수 2회",
            "advice": "첫 번째 매수(10/06)는 20일선 위에서 잘 진입했으나, 두 번째 매수(12/05)는 하락 추세에서 성급하게 물타기를 했습니다. 영상에서 강조한 '눌림목'은 상승 추세 중 조정 구간을 의미하므로, 하락 반전 시에는 진입을 자제해야 합니다. 다음부터는..."
        }}
    ],
    "total_score": 75
}}
"""

    final_prompt = PROMPT_TEMPLATE.format(
        context=video_context,
        stocks_context=stocks_analysis_text
    )
    return final_prompt


def generate_answer(video_context: str, user_data: Any) -> dict:
    rag_prompt = make_rag_prompt(video_context, user_data)

    print(f"[Generation] LLM 호출 시작!")

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": rag_prompt}],
            temperature=0.1,
            max_tokens=2048
        )

        if completion.choices:
            raw_content = completion.choices[0].message.content.strip()

            clean_content = clean_json_text(raw_content)

            try:
                return json.loads(clean_content)
            except json.JSONDecodeError as je:
                print(f"[Error] JSON 파싱 실패: {je}")
                return {
                    "error": "JSON 파싱 실패",
                    "raw_text": raw_content,
                    "advice": "AI 답변 형식이 올바르지 않습니다."
                }
        else:
            return {"error": "No response"}

    except Exception as e:
        print(f"[Error] LLM 호출 실패: {e}")
        return {"error": str(e)}