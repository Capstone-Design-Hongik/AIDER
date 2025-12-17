# generation.py
import os
import json
from openai import OpenAI
from typing import List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# 환경 변수 체크
if "HF_TOKEN" not in os.environ:
    print("[Warning] HF_TOKEN 환경 변수가 없습니다.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN", "dummy_key"),
    timeout=60.0  # 60초로 단축 (Railway 타임아웃 전에 실패하도록)
)

MODEL_NAME = "openai/gpt-oss-20b:groq"

def get_price_context(trade_date_str: str, stock_prices: List[Any]) -> str:
    """
    매매일(trade_date)을 기준으로 앞뒤 5일치 주가 데이터만 뽑아서 문자열로 만듭니다.
    """
    try:
        target_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
        
        relevant_prices = []
        for p in stock_prices:
            p_date_str = p.date if hasattr(p, 'date') else p['date']
            p_price = p.closePrice if hasattr(p, 'closePrice') else p['closePrice']
            
            p_date = datetime.strptime(p_date_str, "%Y-%m-%d")
            
            # 매매일 기준 과거 10일 ~ 미래 5일 데이터만 가져오기
            if (target_date - timedelta(days=10)) <= p_date <= (target_date + timedelta(days=5)):
                relevant_prices.append(f"  {p_date_str}: {p_price:,.0f}원")
        
        if not relevant_prices:
            return "  (해당 날짜 주변의 주가 데이터가 없습니다)"
            
        return "\n".join(relevant_prices)
        
    except Exception as e:
        print(f"[Error] 날짜 처리 중 오류: {e}")
        return "  (날짜 형식 오류로 데이터 추출 실패)"

def make_rag_prompt(video_context: str, user_data: Any) -> str:
    print("\n[Generation] 종목별 매매 분석 프롬프트 구성 중...")
    
    # 종목별로 매매 기록 그룹화
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
    
    # 종목별 분석 텍스트 생성
    stocks_analysis_text = ""
    
    for idx, (stock_name, stock_data) in enumerate(stocks.items(), 1):
        stocks_analysis_text += f"\n{'='*50}\n"
        stocks_analysis_text += f"[종목 {idx}] {stock_name} (코드: {stock_data['stockCode']})\n"
        stocks_analysis_text += f"{'='*50}\n\n"
        
        # 해당 종목의 모든 매매 기록
        stocks_analysis_text += "📊 매매 내역:\n"
        for i, trade in enumerate(stock_data["trades"], 1):
            price_context = get_price_context(trade["date"], user_data.stockPrices)
            
            stocks_analysis_text += f"""
  [{i}] {trade["date"]} - {trade["type"]}
      - 거래가격: {trade["price"]:,.0f}원
      - 거래수량: {trade["quantity"]}주
      
  📈 당시 주가 흐름:
{price_context}

"""
        
        stocks_analysis_text += f"\n{'-'*50}\n"

    PROMPT_TEMPLATE = """
당신은 주식 초보자를 위한 **친절하고 예리한 투자 멘토 AI**입니다.

**[역할]**
사용자가 거래한 **각 종목별로** 모든 매매 내역을 분석하고, 실질적인 조언을 제공하세요.
유튜브 영상의 투자 전략(Context)을 바탕으로 구체적이고 실천 가능한 개선점을 제시합니다.

**[영상 전략 내용 (Context)]**
{context}

**[사용자의 종목별 매매 기록]**
{stocks_context}

**[조언 작성 지침]**
1. **종목별 통합 조언**: 각 종목의 모든 매매 내역을 종합하여 하나의 조언으로 작성
2. **구체적이고 실천 가능**: "다음에는 이렇게 하세요" 형태로 명확한 액션 아이템 제시
3. **영상 전략 반영**: 영상에서 강조한 매매 원칙(눌림목, 이동평균, 지지선 등)을 구체적으로 언급
4. **긍정적 톤**: 잘한 점은 인정하고, 개선점은 건설적으로 제안
5. **2-4문장 길이**: 너무 길지 않게, 핵심만 담아서 작성

**[점수 산정 기준 (total_score)]**
점수는 0~100점 사이로, 영상의 투자 전략 대비 사용자 매매의 적합도를 평가합니다.

- **90-100점**: 영상 전략을 완벽하게 이해하고 실전에 적용. 매수/매도 타이밍이 매우 적절
- **75-89점**: 영상 전략을 대체로 잘 따름. 일부 개선 여지가 있으나 전반적으로 우수
- **60-74점**: 영상 전략의 핵심은 이해했으나 실행에 아쉬운 점이 있음. 추격 매수 또는 고점 진입 등
- **40-59점**: 영상 전략과 다소 괴리가 있음. 기본적인 원칙(이동평균, 지지선 등) 미준수
- **0-39점**: 영상 전략을 거의 따르지 않음. 감정적 매매 또는 무계획적 진입

**점수 산정 시 고려 사항:**
- 매수 타점의 적절성 (눌림목, 지지선 확인 등)
- 영상에서 강조한 기술적 지표 활용 여부
- 추세 파악 능력 (상승/하락 추세 구분)
- 리스크 관리 (고점 추격 회피, 손절 등)
- 주가 데이터가 부족한 경우에도 가능한 범위 내에서 평가

**advice 작성 예시:**
- "이동평균선(20일) 돌파를 확인한 후 거래량이 평소의 1.5배 이상 증가할 때 진입하세요. 현재 추격 매수 경향이 있으니, 조정 구간에서 지지선을 확인하는 습관을 들이면 더 안정적입니다."
- "데이터가 부족하여 정확한 분석이 어렵습니다. 매매 전후 최소 10일치 주가 데이터를 확인하고, 지지/저항선을 파악한 후 진입하세요."
- "상승 추세는 잘 포착했습니다. 다만 진입 시점을 전일 종가 대비 -2~3% 하락한 눌림목에서 잡으면 리스크를 줄일 수 있습니다."

**[출력 형식 (JSON)]**
반드시 아래 JSON 구조를 정확히 따르세요. total_score는 analysis 배열 밖에 위치해야 합니다.

{{
    "analysis": [
        {{
            "trade_id": 1,
            "stock_name": "종목명",
            "type": "해당 종목의 주요 매매 유형 (예: 매수 2회)",
            "advice": "이 종목의 매매 내역을 종합 분석한 구체적인 조언. 잘한 점을 인정하고, 영상 전략을 바탕으로 개선점을 2-4문장으로 명확하게 제시."
        }},
        {{
            "trade_id": 2,
            "stock_name": "다른 종목명",
            "type": "매수 1회",
            "advice": "..."
        }}
    ],
    "total_score": 75
}}

**JSON 형식 주의사항:**
- analysis는 배열(array)입니다
- total_score는 analysis 배열과 같은 레벨에 있어야 합니다 (배열 안에 들어가면 안 됨)
- total_score의 값은 숫자(number)여야 합니다 (문자열 X)

**올바른 예시:**
{{
    "analysis": [...],
    "total_score": 65
}}

**잘못된 예시 (하지 마세요):**
{{
    "analysis": [...],
    "total_score": "65"  ← 문자열 X
}}
또는
[
    {{"analysis": [...]}},
    "total_score": 65  ← 배열 구조 X
]

**점수 예시:**
- 95점: "영상의 눌림목 매수 전략을 완벽히 실행. 20일 이동평균 돌파 후 조정 시 진입"
- 80점: "추세 파악은 우수하나 진입 타점이 약간 이름. 이동평균 확인 후 진입하면 더 좋음"
- 65점: "상승세는 잘 포착했으나 추격 매수 경향. 영상의 지지선 확인 원칙 미적용"
- 45점: "고점에서 매수하여 리스크 큼. 영상의 기본 원칙(이동평균, 추세) 재학습 필요"

**중요**: 
- advice는 사용자가 바로 다음 투자에 적용할 수 있는 구체적인 조언이어야 합니다
- 영상의 투자 원칙(이동평균, 눌림목, 지지선 등)을 반드시 언급하세요
- 데이터가 부족한 경우에도 일반적인 조언을 제공하세요
- total_score는 영상 전략 준수도를 객관적으로 반영해야 합니다
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
            max_tokens=1500,  # 2048 → 1500으로 감소 (더 빠른 응답)
            response_format={"type": "json_object"}
        )
        
        if completion.choices:
            content = completion.choices[0].message.content.strip()
            try:
                return json.loads(content)
            except:
                # JSON 파싱 실패시 텍스트라도 반환
                return {"error": "JSON 파싱 실패", "raw_text": content}
        else:
            return {"error": "No response"}

    except Exception as e:
        print(f"[Error] LLM 호출 실패: {e}")
        return {"error": str(e)}