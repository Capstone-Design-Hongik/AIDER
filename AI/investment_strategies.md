# 투자 전략 선택 가이드

## 1. **외부 자료 기반 (external)** ⭐⭐⭐
- **설명**: YouTube 투자 유튜버의 조언을 기반으로 분석
- **사용 시점**: 특정 유튜버를 신뢰하고 그들의 철학을 따르고 싶을 때
- **장점**: 실전 경험 기반 조언, 심리 관리 팁 포함
- **단점**: 유튜버마다 관점이 다를 수 있음
- **대상**: 초보~중급 투자자

**요청 예시**:
```json
{
  "strategy": "external",
  "externalUrl": "https://youtube.com/..."
}
```

---

## 2. **기술적 분석 (technical_analysis)** ⭐⭐⭐⭐
- **설명**: 차트, 이동평균선, RSI 등 기술 지표 기반 분석
- **사용 시점**: 단기 매매, 진입/청산 타이밍이 중요할 때
- **장점**: 객관적 수치 기반, 백테스팅 가능
- **단점**: 신호가 늦을 수 있음, 급등락에 약함
- **대상**: 중급~고급 투자자

**요청 예시**:
```json
{
  "strategy": "technical_analysis",
  "indicators": ["MA20", "MA60", "RSI", "MACD"],
  "timeframe": "daily"
}
```

---

## 3. **기본 분석 (fundamental_analysis)** ⭐⭐⭐⭐⭐
- **설명**: 기업의 재무제표, PER, PBR, ROE 등 분석
- **사용 시점**: 장기 보유, 저평가 기업 찾기
- **장점**: 기업의 진정한 가치 파악, 안정적
- **단점**: 분석에 시간이 많이 걸림, 시장 심리 무시
- **대상**: 중급~고급 투자자

**요청 예시**:
```json
{
  "strategy": "fundamental_analysis",
  "metrics": {
    "stockCode": "005930",
    "quarter": "Q4_2024"
  }
}
```

---

## 4. **심리 기반 (psychological_analysis)** ⭐⭐⭐
- **설명**: 투자자의 감정, 행동 패턴 분석 후 개선
- **사용 시점**: 반복되는 실수 패턴이 있을 때
- **장점**: 손실의 근본 원인 파악, 장기 수익성 향상
- **단점**: 즉각적인 수익 기대 X
- **대상**: 모든 수준의 투자자

**요청 예시**:
```json
{
  "strategy": "psychological_analysis"
}
```

---

## 5. **포트폴리오 최적화 (portfolio_optimization)** ⭐⭐⭐⭐
- **설명**: 현재 보유 종목의 비중 최적화 & 분산
- **사용 시점**: 여러 종목을 보유 중이고, 리스크 조정하고 싶을 때
- **장점**: 체계적 자산배분, 리스크 최소화
- **단점**: 복잡한 계산
- **대상**: 중급~고급 투자자

**요청 예시**:
```json
{
  "strategy": "portfolio_optimization",
  "portfolio": [
    {"code": "005930", "quantity": 10},
    {"code": "000660", "quantity": 5}
  ],
  "risk_tolerance": "moderate"
}
```

---

## 6. **AI 패턴 기반 (ai_pattern_prediction)** ⭐⭐⭐⭐⭐
- **설명**: 사용자의 매매 패턴을 학습해서 앞으로의 행동 예측 & 조언
- **사용 시점**: 충분한 거래 이력이 있을 때
- **장점**: 개인맞춤형 분석, 시간 지나면서 정확도 ↑
- **단점**: 초기에는 데이터 부족
- **대상**: 모든 수준, 특히 장기 사용자

**요청 예시**:
```json
{
  "strategy": "ai_pattern_prediction",
  "includeHistoricalTrades": true
}
```

---

## 추천 조합

| 사용자 타입 | 추천 전략 | 순서 |
|-----------|---------|------|
| 초보 투자자 | external → psychological_analysis | 1순위: 외부 조언, 2순위: 심리 개선 |
| 단기 매매자 | technical_analysis → ai_pattern_prediction | 1순위: 기술 지표, 2순위: 패턴 학습 |
| 장기 보유자 | fundamental_analysis → portfolio_optimization | 1순위: 기업 분석, 2순위: 자산 배분 |
| 다중 포트폴리오 | portfolio_optimization → psychological_analysis | 1순위: 포트폴리오 최적화, 2순위: 심리 관리 |