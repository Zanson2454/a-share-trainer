import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react'
import { motion } from 'framer-motion'
import { useStockAnalysis } from '../hooks/useStockAnalysis'
import { searchStocks, getStockPatterns } from '../api/client'
import type { PatternInfo } from '../types'
import RadarChart from '../components/shared/RadarChart'
import ScoreBadge from '../components/shared/ScoreBadge'
import MetricCard from '../components/shared/MetricCard'
import MarkdownPreview from '../components/shared/MarkdownPreview'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'
import EmptyState from '../components/shared/EmptyState'

const HOT_STOCKS = [
  { code: '600519', name: '贵州茅台' },
  { code: '000858', name: '五粮液' },
  { code: '300750', name: '宁德时代' },
  { code: '002594', name: '比亚迪' },
  { code: '601318', name: '中国平安' },
]

const TIMEFRAMES = [
  { value: 'daily', label: '日线' },
  { value: 'weekly', label: '周线' },
  { value: 'monthly', label: '月线' },
  { value: '4h', label: '4小时' },
  { value: '120', label: '120分' },
  { value: '60', label: '60分' },
  { value: '30', label: '30分' },
  { value: '15', label: '15分' },
]

interface SearchResult {
  code: string
  name: string
}

export default function StockAnalysisPage() {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searching, setSearching] = useState(false)
  const { data, loading, error, analyze } = useStockAnalysis()
  const [showMarkdown, setShowMarkdown] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined)
  const [patternsPeriod, setPatternsPeriod] = useState('daily')
  const [periodPatterns, setPeriodPatterns] = useState<PatternInfo[] | null>(null)
  const [patternsLoading, setPatternsLoading] = useState(false)
  const currentCodeRef = useRef<string>('')

  const fetchPatterns = useCallback(async (code: string, period: string) => {
    setPatternsLoading(true)
    try {
      const res = await getStockPatterns(code, period)
      setPeriodPatterns(res.patterns)
    } catch {
      setPeriodPatterns(null)
    } finally {
      setPatternsLoading(false)
    }
  }, [])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleInput = (value: string) => {
    setInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (value.trim().length < 1) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const res = await searchStocks(value.trim())
        setSuggestions(res.results)
        setShowSuggestions(res.results.length > 0)
      } catch {
        setSuggestions([])
      } finally {
        setSearching(false)
      }
    }, 300)
  }

  const selectStock = (item: SearchResult) => {
    setInput(`${item.name} (${item.code})`)
    setShowSuggestions(false)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const match = input.match(/\((\d{6})\)/)
    const targetCode = match ? match[1] : input.trim()
    if (targetCode.length === 6 && /^\d{6}$/.test(targetCode)) {
      currentCodeRef.current = targetCode
      setPatternsPeriod('daily')
      setPeriodPatterns(null)
      analyze(targetCode)
      setShowSuggestions(false)
    }
  }

  const radarData = data ? [
    { subject: '趋势形态', score: data.technical.score, fullMark: 25 },
    { subject: '支撑压力', score: data.technical.volume_label === '放量' ? 18 : 12, fullMark: 25 },
    { subject: 'PE估值', score: data.financial.pe && data.financial.pe < 30 ? 20 : 12, fullMark: 25 },
    { subject: 'ROE质量', score: data.financial.roe && data.financial.roe > 15 ? 20 : 10, fullMark: 25 },
    { subject: '风险控制', score: 16, fullMark: 25 },
  ] : []

  const generateMarkdown = () => {
    if (!data) return ''
    const t = data.technical
    const f = data.financial
    return `# ${data.name || data.code} 个股分析报告

## 技术面
- 当前趋势: **${t.trend}**
- 收盘价: ${t.close} | MA20: ${t.ma20} | MA60: ${t.ma60}
- 量比: ${t.volume_ratio} (${t.volume_label})
- 支撑: ${t.support_1} / ${t.support_2}
- 压力: ${t.resistance_1} / ${t.resistance_2}
- 技术评分: ${t.score}/25 (${t.score_desc})

## 基本面
| 指标 | 数值 |
|------|------|
| PE | ${f.pe ?? 'N/A'} |
| PB | ${f.pb ?? 'N/A'} |
| ROE | ${f.roe != null ? f.roe + '%' : 'N/A'} |
| 负债率 | ${f.debt_ratio != null ? f.debt_ratio + '%' : 'N/A'} |

## 风险点
${data.risk_points.map(r => `- ${r}`).join('\n')}

## 观察信号
${data.observe_signals.map(s => `- [ ] ${s}`).join('\n')}

> 仅用于学习研究，不构成投资建议
`
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30"
      >
        <div className="flex items-end gap-4">
          <div className="flex-1 relative" ref={searchRef}>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              股票代码或名称
            </label>
            <input
              type="text"
              value={input}
              onChange={e => handleInput(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              placeholder="输入代码如 600519，或名称如 茅台"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 text-sm
                         placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
            {searching && (
              <div className="absolute right-3 top-9">
                <div className="w-4 h-4 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
              </div>
            )}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl overflow-hidden">
                {suggestions.map((s, i) => (
                  <button
                    key={s.code}
                    type="button"
                    onClick={() => selectStock(s)}
                    className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors
                      ${i === 0 ? '' : 'border-t border-slate-700/50'}
                      hover:bg-slate-700/60`}
                  >
                    <span className="text-slate-100">{s.name}</span>
                    <span className="text-xs text-slate-400">{s.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={loading || input.trim().length === 0}
            className="px-6 py-2.5 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium
                       hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {loading ? '分析中...' : '开始分析'}
          </button>
        </div>
        <div className="flex gap-2 mt-3 flex-wrap">
          {HOT_STOCKS.map(s => (
            <button
              key={s.code}
              type="button"
              onClick={() => selectStock(s)}
              className="text-xs text-slate-400 hover:text-blue-400 transition-colors"
            >
              {s.name}({s.code})
            </button>
          ))}
        </div>
      </motion.form>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-red-900/40 border border-red-500/30 rounded-xl p-4 text-sm text-red-400"
        >
          {error}
        </motion.div>
      )}

      {loading && <LoadingSkeleton />}

      {!loading && !data && !error && (
        <EmptyState
          icon="🔬"
          title="个股深度分析"
          description="输入A股代码或名称，获取技术面、基本面和风险评估的完整分析报告"
        />
      )}

      {data && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-4 gap-4">
            <MetricCard
              label="当前价"
              value={data.technical.close.toFixed(2)}
              trend={data.technical.trend === '上升' ? 'up' : data.technical.trend === '下降' ? 'down' : 'neutral'}
              subtitle={`趋势: ${data.technical.trend}`}
            />
            <MetricCard
              label="技术评分"
              value={`${data.technical.score}/25`}
              trend={data.technical.score >= 15 ? 'up' : 'down'}
              subtitle={data.technical.score_desc}
            />
            <MetricCard
              label="量比"
              value={data.technical.volume_ratio.toFixed(2)}
              trend={data.technical.volume_label === '放量' ? 'up' : data.technical.volume_label === '缩量' ? 'down' : 'neutral'}
              subtitle={data.technical.volume_label}
            />
            <MetricCard
              label="PE"
              value={data.financial.pe?.toFixed(1) ?? 'N/A'}
              trend={data.financial.pe && data.financial.pe < 30 ? 'up' : 'down'}
              subtitle="市盈率"
            />
          </div>

          {/* 多周期趋势 */}
          {data.multi_timeframe && data.multi_timeframe.length > 0 && (
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-4">多周期趋势</h3>
              <div className="grid grid-cols-3 gap-4">
                {data.multi_timeframe.map((tf) => (
                  <div
                    key={tf.period}
                    className={`bg-slate-800/80 rounded-lg p-4 border-l-2 ${
                      tf.trend === '上升' ? 'border-green-500' :
                      tf.trend === '下降' ? 'border-red-500' :
                      'border-amber-500'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-700 text-slate-400">
                        {tf.label}
                      </span>
                      <span className="text-xs text-slate-500">{tf.period}</span>
                    </div>
                    <p className={`text-lg font-bold ${
                      tf.trend === '上升' ? 'text-green-400' :
                      tf.trend === '下降' ? 'text-red-400' :
                      tf.trend === '数据不足' ? 'text-slate-500' :
                      'text-amber-400'
                    }`}>
                      {tf.trend}
                    </p>
                    {tf.trend !== '数据不足' && (
                      <div className="mt-2 space-y-1 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-500">收盘</span>
                          <span className="text-slate-300 font-mono">{tf.close.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">MA20</span>
                          <span className="text-slate-300 font-mono">{tf.ma20.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">MA60</span>
                          <span className="text-slate-300 font-mono">{tf.ma60 > 0 ? tf.ma60.toFixed(2) : '--'}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 操作建议 */}
          {data.recommendation && (
            <div className={`rounded-xl p-5 border-2 ${
              data.recommendation.action === '买入' ? 'bg-green-900/10 border-green-500/40' :
              data.recommendation.action === '卖出' ? 'bg-red-900/10 border-red-500/40' :
              'bg-slate-800/60 border-slate-600/40'
            }`}>
              <div className="flex items-center gap-4 mb-4">
                <span className={`text-lg font-bold px-4 py-1.5 rounded-lg ${
                  data.recommendation.action === '买入' ? 'bg-green-500/20 text-green-400' :
                  data.recommendation.action === '卖出' ? 'bg-red-500/20 text-red-400' :
                  'bg-amber-500/20 text-amber-400'
                }`}>
                  {data.recommendation.action}
                </span>
                <span className={`text-xs px-2 py-1 rounded font-mono ${
                  data.recommendation.confidence >= 7 ? 'bg-blue-900/40 text-blue-400' :
                  data.recommendation.confidence >= 4 ? 'bg-slate-700/50 text-slate-300' :
                  'bg-slate-700/30 text-slate-500'
                }`}>
                  {data.recommendation.confidence}/10 分
                </span>
                <span className="text-sm text-slate-300">{data.recommendation.summary}</span>
                <span className="text-xs text-slate-500 ml-auto">{data.recommendation.timeframe}</span>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-3">
                <div className="bg-slate-800/80 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">入场区间</p>
                  <p className="text-sm font-mono text-blue-400">{data.recommendation.entry_zone}</p>
                </div>
                <div className="bg-slate-800/80 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">止损价</p>
                  <p className="text-sm font-mono text-red-400">{data.recommendation.stop_loss.toFixed(2)}</p>
                </div>
                <div className="bg-slate-800/80 rounded-lg p-3">
                  <p className="text-xs text-slate-400 mb-1">目标价</p>
                  <p className="text-sm font-mono text-green-400">
                    {data.recommendation.targets.length > 0
                      ? data.recommendation.targets.map(t => t.toFixed(2)).join(' / ')
                      : '待定'}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs font-medium text-green-400 mb-2">买入条件</p>
                  <ul className="space-y-1">
                    {data.recommendation.buy_conditions.length > 0
                      ? data.recommendation.buy_conditions.map((c, i) => (
                          <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                            <span className="text-green-500 mt-0.5">+</span>
                            {c}
                          </li>
                        ))
                      : <li className="text-xs text-slate-500">暂无明确买入条件</li>
                    }
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium text-red-400 mb-2">卖出/止损条件</p>
                  <ul className="space-y-1">
                    {data.recommendation.sell_conditions.length > 0
                      ? data.recommendation.sell_conditions.map((c, i) => (
                          <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                            <span className="text-red-500 mt-0.5">-</span>
                            {c}
                          </li>
                        ))
                      : <li className="text-xs text-slate-500">暂无明确卖出条件</li>
                    }
                  </ul>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-4">技术指标</h3>
              <div className="grid grid-cols-3 gap-3">
                {[['MA5', data.technical.ma5], ['MA20', data.technical.ma20], ['MA60', data.technical.ma60]].map(([label, val]) => (
                  <div key={label as string} className="bg-slate-800/80 rounded-lg p-3">
                    <p className="text-xs text-slate-400">{label}</p>
                    <p className="text-lg font-bold text-white">{Number(val).toFixed(2)}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {Number(val) < data.technical.close ? '价格在上' : '价格在下'}
                    </p>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div className="bg-slate-800/80 rounded-lg p-3">
                  <p className="text-xs text-slate-400">支撑位</p>
                  <p className="text-sm font-medium text-green-400">{data.technical.support_1.toFixed(2)}</p>
                </div>
                <div className="bg-slate-800/80 rounded-lg p-3">
                  <p className="text-xs text-slate-400">压力位</p>
                  <p className="text-sm font-medium text-red-400">{data.technical.resistance_1.toFixed(2)}</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-slate-100 mb-2">多维度评估</h3>
              <RadarChart data={radarData} />
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
            <h3 className="text-sm font-semibold text-slate-100 mb-3">财务质量</h3>
            <div className="grid grid-cols-5 gap-3">
              {[
                ['PE', data.financial.pe, data.financial.pe != null && data.financial.pe < 30],
                ['PB', data.financial.pb, null],
                ['ROE %', data.financial.roe, data.financial.roe != null && data.financial.roe > 15],
                ['利润增速 %', data.financial.profit_growth, data.financial.profit_growth != null && data.financial.profit_growth > 20],
                ['负债率 %', data.financial.debt_ratio, data.financial.debt_ratio != null && data.financial.debt_ratio < 50],
              ].map(([label, val, good]) => (
                <div key={label as string} className="bg-slate-800/80 rounded-lg p-3 text-center">
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className={`text-lg font-bold mt-1 ${
                    good === true ? 'text-green-400' : good === false ? 'text-red-400' : 'text-slate-100'
                  }`}>
                    {val != null ? Number(val).toFixed(1) : '--'}
                  </p>
                  {good !== null && (
                    <ScoreBadge score={good ? 75 : 25} max={100} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 基本面快速分析 */}
          {data.quick && (
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30 space-y-4">
              <h3 className="text-sm font-semibold text-slate-100">基本面快速分析</h3>

              {/* 1. PE */}
              <div className="bg-slate-800/80 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    data.quick.pe_level === '偏低' ? 'bg-green-900/40 text-green-400' :
                    data.quick.pe_level === '合理' ? 'bg-blue-900/40 text-blue-400' :
                    data.quick.pe_level === '偏高' ? 'bg-amber-900/40 text-amber-400' :
                    'bg-red-900/40 text-red-400'
                  }`}>
                    PE {data.quick.pe_level}
                  </span>
                  <span className="text-xs text-slate-400">静态投资回收年限 ≈ {data.quick.pe_dynamic?.toFixed(1) ?? '--'} 年</span>
                </div>
                <p className="text-sm text-slate-300">{data.quick.pe_explanation}</p>
              </div>

              {/* 2. 营收利润同步 */}
              <div className="bg-slate-800/80 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    data.quick.revenue_profit_sync === '同步' ? 'bg-green-900/40 text-green-400' :
                    data.quick.revenue_profit_sync === '数据不足' ? 'bg-slate-700/50 text-slate-400' :
                    'bg-amber-900/40 text-amber-400'
                  }`}>
                    {data.quick.revenue_profit_sync}
                  </span>
                  <span className="text-xs text-slate-400">营收与利润是否同步增长</span>
                </div>
                <p className="text-sm text-slate-300">{data.quick.revenue_profit_detail || '待获取财务摘要数据'}</p>
              </div>

              {/* 3. EPS 环比 */}
              <div className="bg-slate-800/80 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    data.quick.eps_qoq === '环比增长' ? 'bg-green-900/40 text-green-400' :
                    data.quick.eps_qoq === '环比下降' ? 'bg-red-900/40 text-red-400' :
                    data.quick.eps_qoq === '环比持平' ? 'bg-blue-900/40 text-blue-400' :
                    'bg-slate-700/50 text-slate-400'
                  }`}>
                    {data.quick.eps_qoq}
                  </span>
                  <span className="text-xs text-slate-400">每股收益最近一期与上期对比</span>
                </div>
                <p className="text-sm text-slate-300">{data.quick.eps_qoq_detail || '待获取财务摘要数据'}</p>
              </div>

              {/* 4. PEG */}
              <div className="bg-slate-800/80 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    data.quick.peg_level === '低估' ? 'bg-green-900/40 text-green-400' :
                    data.quick.peg_level === '合理' ? 'bg-blue-900/40 text-blue-400' :
                    data.quick.peg_level === '高估' ? 'bg-red-900/40 text-red-400' :
                    'bg-slate-700/50 text-slate-400'
                  }`}>
                    PEG {data.quick.peg_level} ({data.quick.peg?.toFixed(2) ?? '--'})
                  </span>
                  <span className="text-xs text-slate-400">PEG = 净利润同比增长率 ÷ 动态市盈率</span>
                </div>
                <p className="text-sm text-slate-300">{data.quick.peg_explanation}</p>
              </div>
            </div>
          )}

          {/* K线形态识别 */}
          <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-100">K线形态识别</h3>
              <div className="flex gap-1 bg-slate-800 rounded-lg p-0.5 border border-slate-700/50">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf.value}
                    onClick={() => {
                      setPatternsPeriod(tf.value)
                      if (currentCodeRef.current) {
                        fetchPatterns(currentCodeRef.current, tf.value)
                      }
                    }}
                    className={`px-2.5 py-1 text-xs rounded transition-colors ${
                      patternsPeriod === tf.value
                        ? 'bg-blue-500/20 text-blue-400 font-medium'
                        : 'text-slate-400 hover:text-slate-300'
                    }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>

            {(() => {
              const displayPatterns = patternsPeriod === 'daily' ? data.patterns : (periodPatterns ?? [])
              const isLoading = patternsPeriod !== 'daily' && patternsLoading

              if (isLoading) {
                return (
                  <div className="flex items-center justify-center py-8">
                    <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                    <span className="ml-3 text-sm text-slate-400">加载{patternsPeriod}形态...</span>
                  </div>
                )
              }

              if (displayPatterns.length === 0) {
                return (
                  <p className="text-sm text-slate-500 text-center py-6">
                    {patternsPeriod === 'daily' ? '未检测到明显K线形态' : `${patternsPeriod}周期未检测到明显K线形态`}
                  </p>
                )
              }

              return (
                <div className="grid grid-cols-2 gap-3">
                  {displayPatterns.map((p, i) => (
                    <div
                      key={i}
                      className={`bg-slate-800/80 rounded-lg p-4 border-l-2 ${
                        p.signal === 'B' ? 'border-green-500' :
                        p.signal === 'S' ? 'border-red-500' :
                        'border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-slate-100">{p.name}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          p.type === 'bullish' ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'
                        }`}>
                          {p.type === 'bullish' ? '看涨' : '看跌'}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                          p.signal === 'B' ? 'bg-green-500/20 text-green-400' :
                          p.signal === 'S' ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-700/50 text-slate-400'
                        }`}>
                          {p.signal === 'B' ? 'B 买点' : p.signal === 'S' ? 'S 卖点' : '观望'}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                          p.confidence >= 7 ? 'bg-amber-900/40 text-amber-400' :
                          p.confidence >= 4 ? 'bg-slate-700/50 text-slate-300' :
                          'bg-slate-700/30 text-slate-500'
                        }`}>
                          {p.confidence}/10
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-2">{p.description}</p>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-slate-500">入场: </span>
                          <span className="text-slate-300 font-mono">{p.entry_price.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">止损: </span>
                          <span className="text-red-400 font-mono">{p.stop_loss.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">目标: </span>
                          <span className="text-green-400 font-mono">{p.target.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-red-400 mb-3">风险点</h3>
              <ul className="space-y-2">
                {data.risk_points.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-red-400 mt-0.5">●</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
              <h3 className="text-sm font-semibold text-blue-400 mb-3">观察信号</h3>
              <ul className="space-y-2">
                {data.observe_signals.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-blue-400 mt-0.5">○</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="bg-slate-800/60 rounded-xl border border-slate-700/30 overflow-hidden">
            <button
              onClick={() => setShowMarkdown(!showMarkdown)}
              className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-slate-300
                         hover:bg-slate-700/60 transition-colors"
            >
              Markdown 报告
              <span className={`transform transition-transform ${showMarkdown ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {showMarkdown && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                className="px-5 pb-5 border-t border-slate-700/30 pt-4"
              >
                <MarkdownPreview content={generateMarkdown()} />
              </motion.div>
            )}
          </div>

          <p className="text-center text-xs text-slate-500 pb-2">
            数据来源: {data.data_source} | 数据区间: {data.data_range}
          </p>
          <p className="text-center text-xs text-slate-400 pb-8">
            仅用于学习研究，不构成投资建议
          </p>
        </motion.div>
      )}
    </div>
  )
}
