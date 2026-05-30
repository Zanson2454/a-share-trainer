"""Pydantic response models for API endpoints."""

from datetime import date
from pydantic import BaseModel, Field


# ── 学习 ──

class LearningResponse(BaseModel):
    topic: str
    category: str
    content: str
    questions: list[str]
    date: str

# ── 盘前 ──

class MarketEnvInfo(BaseModel):
    index_code: str = ""
    index_name: str = ""
    close: float = 0
    change_pct: float = 0
    trend: str = ""  # 进攻 / 震荡 / 防守
    advice: str = ""

class SectorInfo(BaseModel):
    name: str
    change_pct: float
    category: str  # 主线 / 支线 / 一日游

class RiskItem(BaseModel):
    risk_type: str
    event: str = ""
    assessment: str = ""

class PremarketResponse(BaseModel):
    date: str
    market_env: MarketEnvInfo
    policy_direction: list[dict]
    hot_sectors: list[SectorInfo]
    main_lines: list[str]
    risks: list[RiskItem]
    observe_questions: list[str]


# ── 选股 ──

class StockScoreItem(BaseModel):
    market_env: float = 0
    policy_hot: float = 0
    fundamental: float = 0
    technical: float = 0
    risk_control: float = 0

class CandidateStock(BaseModel):
    code: str
    name: str = ""
    industry: str = ""
    scores: StockScoreItem
    total: float
    in_pool: bool
    technical_desc: str = ""
    fundamental_desc: str = ""
    policy_desc: str = ""
    reasons: list[str] = []
    risk_points: list[str] = []
    counter_conditions: list[str] = []
    confirm_questions: list[str] = []

class ScreeningResponse(BaseModel):
    market_score: float
    market_trend: str
    candidates: list[CandidateStock]
    pool_source: str = ""
    total_in_pool: int = 0
    error: str | None = None


# ── 个股分析 ──

class TechnicalInfo(BaseModel):
    trend: str = ""
    close: float = 0
    ma5: float = 0
    ma20: float = 0
    ma60: float = 0
    volume_ratio: float = 0
    volume_label: str = ""
    support_1: float = 0
    support_2: float = 0
    resistance_1: float = 0
    resistance_2: float = 0
    score: float = 0
    score_desc: str = ""

class FinancialInfo(BaseModel):
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    debt_ratio: float | None = None

class FundamentalQuick(BaseModel):
    pe_dynamic: float | None = None
    pe_level: str = ""
    pe_explanation: str = ""
    revenue_profit_sync: str = ""
    revenue_profit_detail: str = ""
    eps_qoq: str = ""
    eps_qoq_detail: str = ""
    peg: float | None = None
    peg_level: str = ""
    peg_explanation: str = ""

class PatternInfo(BaseModel):
    name: str
    type: str  # bullish / bearish
    start_date: str = ""
    end_date: str = ""
    entry_price: float = 0
    stop_loss: float = 0
    target: float = 0
    confidence: int = 0  # 0-10 分
    description: str = ""
    signal: str = ""  # B / S / 观望
    signal_price: float = 0


class Recommendation(BaseModel):
    action: str = ""  # 买入 / 卖出 / 观望
    confidence: int = 0  # 0-10 分
    summary: str = ""
    timeframe: str = ""  # 建议覆盖的时间维度
    buy_conditions: list[str] = []
    sell_conditions: list[str] = []
    entry_zone: str = ""
    stop_loss: float = 0
    targets: list[float] = []


class TimeframeTrend(BaseModel):
    period: str = ""  # 日线/周线/月线
    trend: str = ""  # 上升/下降/震荡
    close: float = 0
    ma20: float = 0
    ma60: float = 0
    label: str = ""  # 短期/中期/长期


class StockAnalysisResponse(BaseModel):
    code: str
    name: str = ""
    quick: FundamentalQuick | None = None
    technical: TechnicalInfo
    financial: FinancialInfo
    patterns: list[PatternInfo] = []
    recommendation: Recommendation | None = None
    risk_points: list[str]
    observe_signals: list[str]
    data_source: str = ""
    data_range: str = ""
    multi_timeframe: list[TimeframeTrend] = []
    disclaimer: str = "仅用于学习研究，不构成投资建议"


class PatternResponse(BaseModel):
    code: str
    name: str = ""
    period: str = "daily"
    patterns: list[PatternInfo] = []
    data_range: str = ""


# ── 复盘 ──

class ReviewTemplateResponse(BaseModel):
    date: str
    content: str


# ── 策略 ──

class StrategyInfo(BaseModel):
    name: str
    exists: bool

class StrategyDetailResponse(BaseModel):
    name: str
    content: str
    exists: bool

class StrategyCreateResponse(BaseModel):
    name: str
    content: str
    created: bool


# ── Agent 分析 ──


class DebateRound(BaseModel):
    round: int
    type: str = "debate"  # opening / debate
    bull: str = ""
    bear: str = ""


class AgentAnalysisResponse(BaseModel):
    code: str
    name: str = ""
    model: str = ""
    decision: str = ""  # 买入/增持/持有/减持/卖出
    confidence: float = 0
    confidence_level: str = ""
    core_reason: str = ""
    key_risk: str = ""
    analyst_reports: dict = {}
    debate: list[DebateRound] = []
    token_usage: dict = {}
    elapsed_seconds: float = 0
    disclaimer: str = "⚠️ 本分析由 AI 生成，仅用于学习研究，不构成投资建议"


# ── 回测 ──

class BacktestMetric(BaseModel):
    trade_count: int
    win_count: int
    win_rate: float
    max_drawdown: float
    annual_return: float
    profit_loss_ratio: float
    sharpe_ratio: float
    max_consecutive_loss: int
    total_return: float
    benchmark_return: float

class EquityPoint(BaseModel):
    date: str
    equity: float

class TradeRecord(BaseModel):
    date: str
    action: str  # buy / sell
    price: float
    quantity: int
    reason: str = ""

class BacktestResponse(BaseModel):
    strategy_name: str
    start_date: str
    end_date: str
    test_code: str = ""
    metrics: BacktestMetric
    equity_curve: list[EquityPoint]
    trades: list[TradeRecord]
    overfit_risk: str
    data_issues: list[str]
    disclaimer: str = "仅用于学习研究，回测结果不代表未来表现"
