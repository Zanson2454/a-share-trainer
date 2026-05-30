import axios from 'axios'
import type {
  CommandsResponse,
  HealthResponse,
  LearningResponse,
  PremarketResponse,
  ScreeningResponse,
  StockAnalysisResponse,
  ReviewTemplateResponse,
  BacktestResponse,
  PatternResponse,
} from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── 系统 ──
export const getHealth = () => api.get<HealthResponse>('/health').then(r => r.data)
export const getCommands = () => api.get<CommandsResponse>('/commands').then(r => r.data)

// ── 学习 ──
export const getDailyLearning = () =>
  api.get<LearningResponse>('/learn/daily').then(r => r.data)

// ── 盘前 ──
export const getPremarket = () =>
  api.get<PremarketResponse>('/premarket', { timeout: 60000 }).then(r => r.data)

// ── 选股 ──
export const getScreening = (codes?: string[]) =>
  api.get<ScreeningResponse>('/screening', {
    params: codes?.length ? { codes: codes.join(',') } : {},
  }).then(r => r.data)

export const postNaturalScreening = (query: string) =>
  api.post<ScreeningResponse>('/screening/natural', { query }, { timeout: 60000 }).then(r => r.data)

// ── 个股分析 ──
export const getStockAnalysis = (code: string) =>
  api.get<StockAnalysisResponse>(`/stocks/${code}/analysis`, { timeout: 60000 }).then(r => r.data)

export const getStockPatterns = (code: string, period: string = 'daily') =>
  api.get<PatternResponse>(`/stocks/${code}/patterns`, { params: { period }, timeout: 30000 }).then(r => r.data)

export const searchStocks = (keyword: string) =>
  api.get<{ keyword: string; results: { code: string; name: string }[]; count: number }>(
    '/stocks/search', { params: { q: keyword } }
  ).then(r => r.data)

// ── 复盘 ──
export const getReviewTemplate = () =>
  api.get<ReviewTemplateResponse>('/review/template').then(r => r.data)

export interface OperationRecord {
  id: string
  date: string
  code: string
  name: string
  action: string
  price: number
  quantity: number
  reason: string
  outcome: string
  profit_pct: number | null
  lesson: string
  tags: string[]
  created_at: string
  updated_at: string
}

export interface OperationStats {
  total: number
  buy_count: number
  sell_count: number
  win_count: number
  loss_count: number
  win_rate: number
  avg_profit: number
  recent_tags: string[]
}

export const getOperationStats = () =>
  api.get<OperationStats>('/review/operations/stats').then(r => r.data)

export const getOperations = () =>
  api.get<{ operations: OperationRecord[]; count: number }>('/review/operations').then(r => r.data)

export const createOperation = (data: Partial<OperationRecord>) =>
  api.post<OperationRecord>('/review/operations', data).then(r => r.data)

export const updateOperation = (opId: string, data: Partial<OperationRecord>) =>
  api.put<OperationRecord>(`/review/operations/${opId}`, data).then(r => r.data)

export const deleteOperation = (opId: string) =>
  api.delete(`/review/operations/${opId}`).then(r => r.data)

// ── 策略 ──
export interface StrategySummary {
  name: string
  status: string
  updated: string
  condition_count: number
}

export interface StrategyFull {
  name: string
  version: string
  created: string
  updated: string
  status: string
  market_env: string[]
  entry_conditions: ConditionRule[]
  exit_conditions: ConditionRule[]
  stop_loss_pct: number
  take_profit_pct: number
  position_pct: number
  notes: string
  exists?: boolean
}

export interface ConditionRule {
  indicator: string
  operator: string
  value: string
  connector?: string
  desc: string
}

export interface IndicatorDef {
  label: string
  params: string[]
  example: string
  desc: string
}

export const getIndicatorReference = () =>
  api.get<{
    indicators: Record<string, IndicatorDef>
    operators: { symbol: string; label: string }[]
    connectors: string[]
  }>('/strategies/indicators').then(r => r.data)

export const getStrategies = () =>
  api.get<{ strategies: StrategySummary[]; count: number }>('/strategies').then(r => r.data)

export const getStrategy = (name: string) =>
  api.get<StrategyFull>(`/strategies/${encodeURIComponent(name)}`).then(r => r.data)

export const createStrategy = (name: string) =>
  api.post<StrategyFull>('/strategies', { name }).then(r => r.data)

export const updateStrategy = (name: string, updates: Partial<StrategyFull>) =>
  api.put<StrategyFull>(`/strategies/${encodeURIComponent(name)}`, updates).then(r => r.data)

export const deleteStrategy = (name: string) =>
  api.delete<{ deleted: boolean; name: string }>(`/strategies/${encodeURIComponent(name)}`).then(r => r.data)

// ── 回测 ──
export interface BacktestParams {
  strategy_name: string
  start_date: string
  end_date: string
  code?: string
  custom_params?: Record<string, number>
}

export const getBacktestParams = () =>
  api.get<{ params: Record<string, number>; ranges: Record<string, { min: number; max: number; step: number; label: string; options?: number[] }> }>(
    '/backtest/params'
  ).then(r => r.data)

export const postBacktest = (params: BacktestParams) =>
  api.post<BacktestResponse>('/backtest', params, { timeout: 60000 }).then(r => r.data)
