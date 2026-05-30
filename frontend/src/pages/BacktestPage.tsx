import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useBacktest } from '../hooks/useBacktest'
import { getBacktestParams } from '../api/client'
import type { BacktestParams } from '../api/client'
import EquityCurve from '../components/charts/EquityCurve'
import DrawdownArea from '../components/charts/DrawdownArea'
import TradeTable from '../components/charts/TradeTable'
import MetricCard from '../components/shared/MetricCard'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'
import EmptyState from '../components/shared/EmptyState'
import { pct } from '../utils/formatters'

const STRATEGIES = [
  { value: '均线金叉', label: '均线金叉', group: '经典' },
  { value: '均线金叉增强版', label: '均线金叉增强版', group: '经典' },
  { value: 'MACD金叉', label: 'MACD金叉', group: '经典' },
  { value: 'RSI超卖反弹', label: 'RSI超卖反弹', group: '经典' },
  { value: '布林带突破', label: '布林带突破', group: '经典' },
  { value: '均线多头排列', label: '均线多头排列', group: '经典' },
  { value: '海龟交易法则', label: '海龟交易法则', group: '经典' },
  { value: 'L0-纯金叉死叉', label: 'L0 纯金叉死叉', group: '分层回测' },
  { value: 'L1-道氏趋势过滤', label: 'L1 道氏趋势过滤', group: '分层回测' },
  { value: 'L2-葛兰威尔加仓止盈', label: 'L2 葛兰威尔加仓止盈', group: '分层回测' },
  { value: 'L3-江恩回调共振', label: 'L3 江恩回调共振', group: '分层回测' },
  { value: 'L4-完整四大理论', label: 'L4 完整四大理论', group: '分层回测' },
]

type ParamDef = { min: number; max: number; step: number; label: string; options?: number[] }

const HOT_TARGETS = [
  { code: '000300', label: '沪深300' },
  { code: '000001', label: '上证指数' },
  { code: '399001', label: '深证成指' },
  { code: '399006', label: '创业板指' },
  { code: '600519', label: '贵州茅台' },
  { code: '300750', label: '宁德时代' },
  { code: '000858', label: '五粮液' },
  { code: '002594', label: '比亚迪' },
]

export default function BacktestPage() {
  const { data, loading, error, run } = useBacktest()

  const [strategy, setStrategy] = useState('均线金叉')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-12-31')
  const [testCode, setTestCode] = useState('000300')
  const [paramDefs, setParamDefs] = useState<Record<string, ParamDef>>({})
  const [defaultParams, setDefaultParams] = useState<Record<string, number>>({})
  const [customParams, setCustomParams] = useState<Record<string, number>>({})

  const isLayered = strategy.startsWith('L')
  const layerNum = isLayered ? parseInt(strategy.charAt(1)) : 4

  useEffect(() => {
    getBacktestParams().then(({ params, ranges }) => {
      setParamDefs(ranges)
      setDefaultParams(params)
      setCustomParams(params)
    }).catch(() => {})
  }, [])

  // 切换策略时自动联动参数：L0-L4 自动设置 layer，经典策略重置为默认
  useEffect(() => {
    if (isLayered && Object.keys(defaultParams).length > 0) {
      setCustomParams(prev => ({ ...defaultParams, ...prev, layer: layerNum }))
    }
  }, [strategy, isLayered, layerNum, defaultParams])

  const handleRun = () => {
    const req: BacktestParams = {
      strategy_name: strategy,
      start_date: startDate.replace(/-/g, ''),
      end_date: endDate.replace(/-/g, ''),
      code: testCode,
    }
    // 分层策略始终带参数，经典策略不带
    if (isLayered) {
      req.custom_params = customParams
    }
    run(req)
  }

  const updateParam = (key: string, value: number) => {
    setCustomParams(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* 参数表单 */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30"
      >
        <h2 className="text-sm font-semibold text-slate-100 mb-4">回测参数</h2>
        <div className="grid grid-cols-5 gap-4 mb-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">策略</label>
            <select
              value={strategy}
              onChange={e => setStrategy(e.target.value)}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2.5 text-slate-100 text-sm
                         focus:outline-none focus:border-blue-500"
            >
              <optgroup label="经典策略">
                {STRATEGIES.filter(s => s.group === '经典').map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </optgroup>
              <optgroup label="分层回测 (四大理论 L0-L4)">
                {STRATEGIES.filter(s => s.group === '分层回测').map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </optgroup>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">开始日期</label>
            <input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2.5 text-slate-100 text-sm
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">结束日期</label>
            <input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2.5 text-slate-100 text-sm
                         focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">回测标的</label>
            <input
              type="text"
              value={testCode}
              onChange={e => setTestCode(e.target.value)}
              placeholder="000300 或 600519"
              className="w-full bg-slate-900 border border-border rounded-lg px-3 py-2.5 text-slate-100 text-sm
                         placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleRun}
              disabled={loading}
              className="w-full py-2.5 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium
                         hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              {loading ? '回测中...' : '执行回测'}
            </button>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          {HOT_TARGETS.map(t => (
            <button
              key={t.code}
              type="button"
              onClick={() => setTestCode(t.code)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                testCode === t.code
                  ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                  : 'text-slate-500 border-slate-700/50 hover:text-slate-300 hover:border-slate-600'
              }`}
            >
              {t.label}
            </button>
          ))}
          {isLayered && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
              理论层 L{layerNum}
            </span>
          )}
          {!isLayered && (
            <span className="text-xs text-slate-500">选择 L0-L4 分层策略可调参</span>
          )}
        </div>

        {/* 参数面板 — 仅分层策略显示 */}
        {isLayered && Object.keys(paramDefs).length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-700/30">
            <p className="text-xs text-slate-400 mb-3">
              L{layerNum} 策略参数 — 当前层已叠加：
              {layerNum >= 1 && ' 道氏趋势过滤'}
              {layerNum >= 2 && ' + 葛兰威尔加仓止盈'}
              {layerNum >= 3 && ' + 江恩回调共振'}
              {layerNum >= 4 && ' + 超跌反弹/跌破收回'}
              — 调整任意参数后执行回测
            </p>
            <div className="grid grid-cols-4 gap-3">
              {Object.entries(paramDefs).map(([key, def]) => (
                <div key={key} className="bg-slate-800/80 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs text-slate-400">{def.label}</label>
                    <span className="text-xs text-amber-400 font-mono">
                      {customParams[key] ?? '--'}
                    </span>
                  </div>
                  {def.options ? (
                    <div className="flex gap-1">
                      {def.options.map(opt => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => updateParam(key, opt)}
                          className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                            customParams[key] === opt
                              ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                              : 'text-slate-500 border-slate-700/50 hover:text-slate-300'
                          }`}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <input
                      type="range"
                      min={def.min}
                      max={def.max}
                      step={def.step}
                      value={customParams[key] ?? def.min}
                      onChange={e => updateParam(key, parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer
                                 accent-amber-500"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-900/40 border border-red-500/30 rounded-xl p-4 text-sm text-red-400"
        >
          {error}
        </motion.div>
      )}

      <AnimatePresence mode="wait">
        {loading && <LoadingSkeleton key="loading" />}

        {!loading && !data && !error && (
          <EmptyState
            key="empty"
            icon="⚡"
            title="策略回测中心"
            description="选择策略、日期区间和回测标的，验证策略的历史表现。回测结果不代表未来收益。"
          />
        )}

        {data && !loading && (
          <motion.div
            key="result"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* 核心指标 */}
            <div className="grid grid-cols-5 gap-4">
              <MetricCard
                label="累计收益"
                value={pct(data.metrics.total_return)}
                trend={data.metrics.total_return >= 0 ? 'up' : 'down'}
                subtitle={`基准(沪深300): ${pct(data.metrics.benchmark_return)}`}
              />
              <MetricCard
                label="胜率"
                value={pct(data.metrics.win_rate)}
                trend={data.metrics.win_rate >= 0.5 ? 'up' : 'down'}
                subtitle={`${data.metrics.win_count}/${data.metrics.trade_count} 笔`}
              />
              <MetricCard
                label="最大回撤"
                value={pct(data.metrics.max_drawdown)}
                trend={data.metrics.max_drawdown <= 0.2 ? 'up' : 'down'}
              />
              <MetricCard
                label="夏普比率"
                value={data.metrics.sharpe_ratio.toFixed(2)}
                trend={data.metrics.sharpe_ratio >= 1 ? 'up' : data.metrics.sharpe_ratio <= 0 ? 'down' : 'neutral'}
              />
              <MetricCard
                label="年化收益"
                value={pct(data.metrics.annual_return)}
                trend={data.metrics.annual_return >= 0 ? 'up' : 'down'}
              />
            </div>

            <div className="grid grid-cols-5 gap-4">
              <MetricCard label="交易次数" value={data.metrics.trade_count} />
              <MetricCard label="盈亏比" value={data.metrics.profit_loss_ratio.toFixed(2)} />
              <MetricCard
                label="最大连亏"
                value={`${data.metrics.max_consecutive_loss}次`}
                trend={data.metrics.max_consecutive_loss <= 3 ? 'up' : 'down'}
              />
              <MetricCard
                label="过拟合风险"
                value={data.overfit_risk}
                subtitle={data.overfit_risk.startsWith('高') ? '样本不足' : ''}
              />
              <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30 flex flex-col gap-2">
                <p className="text-xs text-slate-400">回测区间</p>
                <p className="text-xs text-slate-300">{data.start_date} ~ {data.end_date}</p>
                <p className="text-xs text-slate-400">标的: {data.test_code}</p>
              </div>
            </div>

            {/* 权益曲线 */}
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-4">权益曲线</h3>
              <EquityCurve data={data.equity_curve} />
            </div>

            {/* 回撤曲线 */}
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-4">回撤曲线</h3>
              <DrawdownArea equityCurve={data.equity_curve} />
            </div>

            {/* 交易明细 */}
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-4">交易明细</h3>
              <TradeTable trades={data.trades} />
            </div>

            {/* 数据问题 */}
            {data.data_issues.length > 0 && (
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4">
                <h3 className="text-xs font-medium text-amber-400 mb-2">数据说明</h3>
                <ul className="space-y-1">
                  {data.data_issues.map((issue, i) => (
                    <li key={i} className="text-xs text-slate-400">· {issue}</li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-center text-xs text-slate-400 pb-8">
              仅用于学习研究，回测结果不代表未来表现
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
