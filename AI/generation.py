# generation.py
import os
import json
from openai import OpenAI
from typing import List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# 환경 변수 체크
if "HF_TOKEN" not in os.environ:
    print("[Warning] HF_TOKEN 환경 변수가 없습니다.")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ.get("HF_TOKEN", "dummy_key"),
    timeout=90.0
)

MODEL_NAME = "openai/gpt-oss-20b:groq"

# [Helper] 날짜 문자열 비교를 위한 함수
def get_price_context(trade_date_str: str, stock_prices: List[Any]) -> str:
    """
    매매일(trade_date)을 기준으로 앞뒤 5일치 주가 데이터만 뽑아서 문자열로 만듭니다.
    데이터가 너무 많으면 LLM이 헷갈려하고, 날짜가 안 맞으면 분석을 못하기 때문입니다.
    """
    try:
        # 날짜 포맷 파싱 (YYYY-MM-DD)
        target_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
        
        relevant_prices = []
        for p in stock_prices:
            # p가 객체인지 dict인지 확인하여 처리
            p_date_str = p.date if hasattr(p, 'date') else p['date']
            p_price = p.closePrice if hasattr(p, 'closePrice') else p['closePrice']
            
            p_date = datetime.strptime(p_date_str, "%Y-%m-%d")
            
            # 매매일 기준 과거 10일 ~ 미래 5일 데이터만 가져오기 (문맥 파악용)
            if (target_date - timedelta(days=10)) <= p_date <= (target_date + timedelta(days=5)):
                relevant_prices.append(f"- {p_date_str}: {p_price}원")
        
        if not relevant_prices:
            return "(해당 날짜 주변의 주가 데이터가 없습니다. 분석 불가)"
            
        return "\n".join(relevant_prices)
        
    except Exception as e:
        print(f"[Error] 날짜 처리 중 오류: {e}")
        return "(날짜 형식 오류로 데이터 추출 실패)"

def make_rag_prompt(video_context: str, user_data: Any) -> str:
    print("\n[Generation] 매수 타점 분석 프롬프트 구성 중...")
    
    # 매매 기록 하나하나를 분석할 수 있도록 포맷팅
    trades_analysis_text = ""
    
    for i, trade in enumerate(user_data.trades):
        # 객체 접근 방식 통일 (Pydantic 모델인 경우)
        t_date = trade.date
        t_name = trade.stockName
        t_type = "매수(Buy)" if trade.tradeType == 'buy' else "매도(Sell)"
        t_price = trade.price
        
        # 해당 매매일 주변의 주가 흐름 가져오기
        price_context = get_price_context(t_date, user_data.stockPrices)
        
        trades_analysis_text += f"""
        [매매 {i+1}]
        - 종목: {t_name}
        - 날짜: {t_date}
        - 행위: {t_type} (가격: {t_price}원)
        - 당시 주가 흐름:
        {price_context}
        --------------------------------
        """

    PROMPT_TEMPLATE = """
    당신은 주식 초보자를 위한 **친절하고 예리한 투자 멘토 AI**입니다.
    
    **[역할]**
    사용자의 '매매 기록'과 '당시 주가 흐름'을 보고, **유튜브 영상의 전략(Context)**에 비추어 잘한 매매인지 못한 매매인지 평가해주세요.
    특히 **'매수(Buy)'**인 경우, 진입 타점이 적절했는지 집중적으로 분석하세요.

    **[영상 전략 내용 (Context)]**
    {context}

    **[사용자 매매 기록 및 주가 상황]**
    {trades_context}

    **[지시 사항]**
    1. 주가 데이터가 매매일과 맞지 않거나 부족하면 "데이터가 부족하여 정확한 분석이 어렵습니다"라고 솔직하게 말하세요.
    2. 데이터가 있다면, 전략에 근거하여 "추격 매수였다", "눌림목을 잘 잡았다" 등으로 구체적으로 조언하세요.
    3. 반드시 아래 JSON 형식으로만 답변하세요.

    **[출력 형식 (JSON)]**
    {{
        "analysis": [
            {{
                "trade_id": 1,
                "type": "매수",
                "evaluation": "잘한 점/못한 점 평가 내용",
                "advice": "다음 투자를 위한 구체적 조언"
            }}
        ],
        "total_score": 80 (0~100 사이 점수)
    }}
    """
    
    final_prompt = PROMPT_TEMPLATE.format(
        context=video_context,
        trades_context=trades_analysis_text
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
            max_tokens=2048,
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