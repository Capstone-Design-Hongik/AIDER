from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class Trade(BaseModel):
    date: str
    stockName: str
    stockCode: str
    tradeType: str
    price: float
    quantity: int


class StockPrice(BaseModel):
    date: str
    closePrice: float


class UserData(BaseModel):
    trades: List[Trade]
    stockPrices: List[StockPrice]
    strategy: str
    externalUrl: Optional[str] = None
    indicators: Optional[List[str]] = None
    metrics: Optional[Dict] = None
    portfolio: Optional[List[Dict]] = None
    risk_tolerance: Optional[str] = None


class UserAnalysisResult(BaseModel):
    patterns: List[str]
    pattern_strength: Dict[str, float]
    risk_level: str
    priority_patterns: List[str]
    confidence: float
    learning_stage: str
    additional_insights: Dict[str, Any]


class TranscriptSection(BaseModel):
    section_name: str
    content: str
    summary: str
    key_points: List[str]
    emotion: str
    target_audience: List[str]
    original_length: Optional[int] = None
    summary_length: Optional[int] = None


class TranscriptAnalysisResult(BaseModel):
    sections: List[TranscriptSection]
    keywords: List[str]
    structure: Dict[str, Any]
    confidence: float
    processing_time: float


class VectorSearchResult(BaseModel):
    id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    type: str


class AgentDecision(BaseModel):
    next_action: str
    reasoning: str
    confidence: float
    parameters: Dict[str, Any]


class ScoreBreakdown(BaseModel):
    """3개 항목 각 100점 만점 독립 평가"""
    youtube_strategy: float  # YouTube 전략 준수도 (0~100)
    trend_awareness: float   # 추세 파악 능력 (0~100)
    entry_timing: float      # 매수 타점 적절성 (0~100)


class RAGOutput(BaseModel):
    analysis_result: UserAnalysisResult
    transcript_analysis: TranscriptAnalysisResult
    search_results: List[VectorSearchResult]
    agent_decisions: List[AgentDecision]
    final_advice: str
    total_score: ScoreBreakdown