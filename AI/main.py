import asyncio
from typing import Dict, List
from models import UserData, Trade, StockPrice
from agent import AgentManager
from vector_db import VectorDB
from config import LLMConfig, VECTOR_DB_PATH, EMBEDDING_MODEL
import json

async def main():
    """메인 실행"""
    
    # 1. Vector DB 초기화
    print("🗄️ Vector DB 초기화 중...")
    vector_db = VectorDB(VECTOR_DB_PATH, EMBEDDING_MODEL)
    
    # 2. YouTube 자막을 벡터DB에 저장 (미리 처리)
    print("📝 YouTube 자막을 벡터DB에 저장 중...")
    sample_documents = [
        {
            "content": "물타기는 같은 종목을 여러 번 매수하는 행동입니다. 이는 매우 위험합니다.",
            "section": "물타기",
            "emotion": "경고",
            "target_audience": ["초보자", "감정적_거래자"],
            "level": "초급",
            "type": "raw"
        },
        {
            "content": "손절은 손실을 최소화하는 가장 중요한 기술입니다. 기준을 정하고 지켜야 합니다.",
            "section": "손절",
            "emotion": "교육",
            "target_audience": ["모든_수준"],
            "level": "초급",
            "type": "raw"
        },
        {
            "content": "DCA 전략은 일정 금액을 정기적으로 투자하는 방식입니다. 감정을 제거하고 규칙을 지킵니다.",
            "section": "DCA",
            "emotion": "격려",
            "target_audience": ["초보자", "규칙적_거래자"],
            "level": "초급",
            "type": "raw"
        },
    ]
    
    vector_db.add_documents(sample_documents)
    
    # 3. 샘플 사용자 데이터
    sample_user_data = UserData(
        trades=[
            Trade(
                date="2024-10-06",
                stockName="삼성전자",
                stockCode="005930",
                tradeType="buy",
                price=72000,
                quantity=5
            ),
            Trade(
                date="2024-12-05",
                stockName="삼성전자",
                stockCode="005930",
                tradeType="buy",
                price=70000,
                quantity=10
            ),
            Trade(
                date="2024-10-20",
                stockName="LG전자",
                stockCode="066570",
                tradeType="buy",
                price=50000,
                quantity=3
            ),
        ],
        stockPrices=[
            StockPrice(date="2024-10-01", closePrice=68000),
            StockPrice(date="2024-10-02", closePrice=69000),
            StockPrice(date="2024-10-03", closePrice=67500),
            StockPrice(date="2024-10-04", closePrice=71000),
            StockPrice(date="2024-10-05", closePrice=71200),
            StockPrice(date="2024-10-06", closePrice=73000),
            StockPrice(date="2024-10-07", closePrice=72500),
        ],
        externalUrl="https://www.youtube.com/watch?v=EMfQuZkzmuc"
    )
    
    # 4. Agent 실행
    print("\n🤖 Agent Manager 초기화 중...")
    agent = AgentManager(vector_db)
    
    print("\n🚀 Agentic RAG 시작...")
    result = await agent.run(sample_user_data)
    
    # 5. 결과 출력
    print("\n" + "=" * 50)
    print("📊 최종 결과")
    print("=" * 50)
    
    print(f"\n👤 사용자 분석:")
    print(f"  - 감지된 패턴: {', '.join(result.analysis_result.patterns)}")
    print(f"  - 위험도: {result.analysis_result.risk_level}")
    print(f"  - 신뢰도: {result.analysis_result.confidence:.2%}")
    
    print(f"\n📺 YouTube 분석:")
    print(f"  - 섹션 수: {len(result.transcript_analysis.sections)}")
    print(f"  - 섹션들: {', '.join([s.section_name for s in result.transcript_analysis.sections])}")
    
    print(f"\n🔍 검색 결과:")
    print(f"  - 찾은 관련 내용: {len(result.search_results)}개")
    print(f"  - 커버리지: {result.confidence_score:.2%}")
    
    print(f"\n🤖 Agent 판단:")
    print(f"  - 수행한 반복: {len(result.agent_decisions)}회")
    for i, decision in enumerate(result.agent_decisions, 1):
        print(f"    {i}. {decision.next_action} (신뢰도: {decision.confidence:.2%})")
    
    print(f"\n💬 최종 조언:")
    print("-" * 50)
    print(result.final_advice)
    print("-" * 50)
    
    # 6. 결과 저장
    output_file = "rag_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "analysis": result.analysis_result.dict(),
            "transcript": {
                "sections": [s.dict() for s in result.transcript_analysis.sections],
                "keywords": result.transcript_analysis.keywords,
            },
            "search_results": [r.dict() for r in result.search_results],
            "agent_decisions": [d.dict() for d in result.agent_decisions],
            "final_advice": result.final_advice,
            "confidence_score": result.confidence_score,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 결과가 {output_file}에 저장되었습니다")

if __name__ == "__main__":
    asyncio.run(main())