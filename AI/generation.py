# generation.py
import os
import json
import re  # 정규표현식 모듈 추가
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
    timeout=90.0
)

# 모델명은 유지하거나, 필요시 더 안정적인 모델로 변경 가능
MODEL_NAME = "openai/gpt-oss-20b:groq" 

def get_price_context(trade_date_str: str, stock_prices: List[Any]) -> str:
    """
    매매일(trade_date)을 기준으로 앞뒤 5일치 주가 데이터만 뽑아서 문자열로 만듭니다.
    """
    try:
        target_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
        
        relevant_prices = []
        for p in stock_prices:
            # Pydantic 모델과 Dict 양쪽 대응
            p_date_str = p.date if hasattr(p, 'date') else p.get('date')
            p_price = p.closePrice if hasattr(p, 'closePrice') else p.get('closePrice')
            
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

def clean_json_text(text: str) -> str:
    """
    LLM이 마크다운 코드 블록(```json ... ```)이나 잡다한 텍스트를 포함했을 때
    순수 JSON 부분만 추출하는 함수
    """
    try:
        # 1. 마크다운 코드 블록 제거
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        
        # 2. 앞뒤 공백 제거
        text = text.strip()
        
        # 3. 중괄호 {} 로 시작하고 끝나는지 확인하여 그 부분만 추출
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            return text[start_idx : end_idx + 1]
        
        return text
    except Exception:
        return text

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

**[total_score 산정 기준]**
1. **점수 범위 및 의미**:
   - 90-100점: 완벽한 전략 실행 (영상 내용 완벽 적용)
   - 75-89점: 대체로 우수 (약간의 아쉬움)
   - 60-74점: 핵심은 이해했으나 개선 필요 (타점 오류 등)
   - 40-59점: 전략과 괴리 (영상 내용 미반영)
   - 0-39점: 무계획적 뇌동 매매
2. **평가 요소**:
   - 매수 타점의 적절성 (눌림목, 지지선 확인 여부)
   - 기술적 지표 활용 (이동평균선 등 영상 언급 지표)
   - 추세 파악 능력 (상승/하락 추세 구분)
   - 리스크 관리 및 영상 전략 준수도

**[필수 요청 사항]**
1. **반드시 JSON 형식만 출력하세요.**
2. **마크다운(```json)이나 다른 설명 텍스트를 절대 포함하지 마세요.**
3. 아래 포맷을 정확히 따르세요.

**[출력 JSON 포맷]**
{{
    "analysis": [
        {{
            "trade_id": 1,
            "stock_name": "종목명",
            "type": "매수 2회, 매도 1회 등 요약",
            "advice": "영상 내용에 기반한 구체적인 조언 (2-4문장)"
        }}
    ],
    "total_score": 75
}}

**advice 작성 팁:**
- "이동평균선", "눌림목", "거래량" 등 영상의 핵심 키워드를 포함하세요.
- 데이터가 부족하면 "데이터 부족으로 정확한 분석은 어렵지만~" 형태로 일반적인 조언을 주세요.
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
        # response_format 파라미터 제거하여 400 에러 방지
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": rag_prompt}],
            temperature=0.1,
            max_tokens=2048
        )
        
        if completion.choices:
            raw_content = completion.choices[0].message.content.strip()
            # print(f"[Debug] Raw LLM Response: {raw_content[:100]}...") # 디버깅용
            
            # JSON 클렌징 (마크다운 제거 등)
            clean_content = clean_json_text(raw_content)
            
            try:
                return json.loads(clean_content)
            except json.JSONDecodeError as je:
                print(f"[Error] JSON 파싱 실패: {je}")
                # 파싱 실패 시, 원본 텍스트를 포함한 에러 객체 반환
                return {
                    "error": "JSON 파싱 실패", 
                    "raw_text": raw_content,
                    "advice": "AI가 답변을 생성했으나 형식이 올바르지 않습니다. 다시 시도해주세요."
                }
        else:
            return {"error": "No response"}

    except Exception as e:
        print(f"[Error] LLM 호출 실패: {e}")
        return {"error": str(e)}