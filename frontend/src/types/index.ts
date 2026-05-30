// ── 学习 ──
export interface LearningResponse {
  topic: string
  category: string
  content: string
  questions: string[]
  date: string
}

// ── 盘前 ──
export interface MarketEnvInfo {
  index_code: string
  index_name: string
  close: number
  change_pct: number
  trend: '进攻' | '震荡' | '防守'
  advice: string
}

export interface SectorInfo {
  name: string
  change_pct: number
  category: '主线' | '支线' | '一日游'
}

export interface RiskItem {
  risk_type: string
  event: string
  assessment: string
}

export interface PremarketResponse {
  date: string
  market_env: MarketEnvInfo
  policy_direction: Record<string, string>[]
  hot_sectors: SectorInfo[]
  main_lines: string[]
  risks: RiskItem[]
  observe_questions: string[]
}

// ── 选股 ──
export interface StockScoreItem {
  market_env: number
  policy_hot: number
  fundamental: number
  technical: number
  risk_control: number
}

export interface CandidateStock {
  code: string
  name: string
  industry: string
  scores: StockScoreItem
  total: number
  in_pool: boolean
  technical_desc: string
  fundamental_desc: string
  policy_desc: string
  reasons: string[]
  risk_points: string[]
  counter_conditions: string[]
  confirm_questions: string[]
}

export interface ScreeningResponse {
  market_score: number
  market_trend: string
  candidates: CandidateStock[]
  pool_source: string
  total_in_pool: number
  error?: string | null
}

// ── 个股分析 ──
export interface Recommendation {
  action: '买入' | '卖出' | '观望'
  confidence: number  // 0-10
  summary: string
  timeframe: string
  buy_conditions: string[]
  sell_conditions: string[]
  entry_zone: string
  stop_loss: number
  targets: number[]
}

export interface PatternInfo {
  name: string
  type: 'bullish' | 'bearish'
  start_date: string
  end_date: string
  entry_price: number
  stop_loss: number
  target: number
  confidence: number  // 0-10
  description: string
  signal: 'B' | 'S' | '观望'
  signal_price: number
}

export interface TechnicalInfo {
  trend: string
  close: number
  ma5: number
  ma20: number
  ma60: number
  volume: number
  avg_volume_20: number
  volume_ratio: number
  volume_label: string
  support_1: number
  support_2: number
  resistance_1: number
  resistance_2: number
  score: number
  score_desc: string
  ma_directions?: Record<string, { value: number; direction: string }>
}

export interface FinancialInfo {
  pe: number | null
  pb: number | null
  roe: number | null
  revenue_growth: number | null
  profit_growth: number | null
  debt_ratio: number | null
}

export interface FundamentalQuick {
  pe_dynamic: number | null
  pe_level: string
  pe_explanation: string
  revenue_profit_sync: string
  revenue_profit_detail: string
  eps_qoq: string
  eps_qoq_detail: string
  peg: number | null
  peg_level: string
  peg_explanation: string
}

export interface TimeframeTrend {
  period: string
  trend: string
  close: number
  ma20: number
  ma60: number
  label: string
}

export interface StockAnalysisResponse {
  code: string
  name: string
  quick: FundamentalQuick | null
  technical: TechnicalInfo
  financial: FinancialInfo
  patterns: PatternInfo[]
  recommendation: Recommendation | null
  risk_points: string[]
  observe_signals: string[]
  data_source: string
  data_range: string
  multi_timeframe: TimeframeTrend[]
  disclaimer?: string
}

export interface PatternResponse {
  code: string
  name: string
  period: string
  patterns: PatternInfo[]
  data_range: string
}

// ── 复盘 ──
export interface ReviewTemplateResponse {
  date: string
  content: string
}

// ── 策略 ──
export interface StrategyInfo {
  name: string
  exists: boolean
}

export interface StrategyDetailResponse {
  name: string
  content: string
  exists: boolean
}

export interface StrategyCreateResponse {
  name: string
  content: string
  created: boolean
}

// ── 回测 ──
export interface BacktestMetric {
  trade_count: number
  win_count: number
  win_rate: number
  max_drawdown: number
  annual_return: number
  profit_loss_ratio: number
  sharpe_ratio: number
  max_consecutive_loss: number
  total_return: number
  benchmark_return: number
}

export interface EquityPoint {
  date: string
  equity: number
}

export interface TradeRecord {
  date: string
  action: 'buy' | 'sell'
  price: number
  quantity: number
  reason: string
}

export interface BacktestResponse {
  strategy_name: string
  start_date: string
  end_date: string
  test_code: string
  metrics: BacktestMetric
  equity_curve: EquityPoint[]
  trades: TradeRecord[]
  overfit_risk: string
  data_issues: string[]
  disclaimer?: string
}

// ── 通用 ──
export interface CommandsResponse {
  commands: {
    name: string
    slug: string
    description: string
    example: string
  }[]
  disclaimer: string
}

export interface HealthResponse {
  status: string
  version: string
}
