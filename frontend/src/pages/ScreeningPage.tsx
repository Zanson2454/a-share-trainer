import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { postNaturalScreening } from '../api/client'
import type { ScreeningResponse, CandidateStock } from '../types'
import ScoreBadge from '../components/shared/ScoreBadge'
import MetricCard from '../components/shared/MetricCard'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'
import EmptyState from '../components/shared/EmptyState'

const EXAMPLE_QUERIES = [
  '高ROE低PE的白酒股',
  '放量突破的科技龙头',
  '低估值高分红的蓝筹股',
  '金叉多头的成长股',
  '底部放量的医药股',
  '低负债高增长的新能源',
]

function CandidateCard({ stock, idx }: { stock: CandidateStock; idx: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.08 }}
      className="bg-slate-800/60 rounded-xl border border-slate-700/30 overflow-hidden"
    >
      <div className={`p-5 border-l-4 ${
        stock.in_pool ? 'border-l-green-500' : 'border-l-slate-600'
      }`}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-white">
                {stock.name || stock.code}
              </h3>
              {stock.name && (
                <span className="text-xs text-slate-400">{stock.code}</span>
              )}
              <ScoreBadge score={stock.total} label="分" />
              {stock.in_pool && (
                <span className="text-xs px-2 py-0.5 bg-green-900/40 text-green-400 rounded-full">
                  入池
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {stock.industry}{stock.industry ? ' · ' : ''}{stock.fundamental_desc} · {stock.technical_desc}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-5 gap-3 mb-4">
          {Object.entries(stock.scores).map(([key, val]) => {
            const max = key === 'fundamental' || key === 'technical' ? 25 :
                       key === 'risk_control' ? 10 : 20
            const ratio = Math.min((val as number) / max, 1)
            return (
              <div key={key} className="text-center">
                <div className="relative w-12 h-12 mx-auto mb-1">
                  <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
                    <circle cx="18" cy="18" r="15" fill="none" stroke="#334155" strokeWidth="3" />
                    <circle
                      cx="18" cy="18" r="15" fill="none"
                      stroke={ratio >= 0.7 ? '#22c55e' : ratio >= 0.4 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="3"
                      strokeDasharray={`${ratio * 94.2} 94.2`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">
                    {val as number}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {key === 'market_env' ? '大盘' :
                   key === 'policy_hot' ? '政策' :
                   key === 'fundamental' ? '基本面' :
                   key === 'technical' ? '技术面' : '风控'}
                </p>
              </div>
            )
          })}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-800/80 rounded-lg p-3">
            <p className="text-xs font-medium text-slate-100 mb-1">入选原因</p>
            <ul className="space-y-0.5">
              {stock.reasons.map((r, i) => (
                <li key={i} className="text-xs text-slate-400">{r}</li>
              ))}
            </ul>
          </div>
          <div className="bg-slate-800/80 rounded-lg p-3">
            <p className="text-xs font-medium text-slate-100 mb-1">确认问题</p>
            <ul className="space-y-0.5">
              {stock.confirm_questions.map((q, i) => (
                <li key={i} className="text-xs text-slate-400">- {q}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default function ScreeningPage() {
  const [query, setQuery] = useState('')
  const [data, setData] = useState<ScreeningResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    try {
      const result = await postNaturalScreening(q)
      setData(result)
      if (result.error) setError(result.error)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? '请求失败')
    } finally {
      setLoading(false)
    }
  }

  const handleExample = (q: string) => {
    setQuery(q)
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30"
      >
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              一句话描述你想找的股票
            </label>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="例如：高ROE低PE的白酒股、放量突破的科技龙头..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 text-sm
                         placeholder:text-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="px-6 py-2.5 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium
                       hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {loading ? '筛选中...' : '筛选'}
          </button>
        </div>
        <div className="flex gap-2 mt-3 flex-wrap">
          {EXAMPLE_QUERIES.map(q => (
            <button
              key={q}
              type="button"
              onClick={() => handleExample(q)}
              className="text-xs text-slate-500 hover:text-blue-400 bg-slate-800/80 px-2.5 py-1 rounded-full
                         border border-slate-700/50 hover:border-blue-500/30 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </motion.div>

      {error && (
        <div className="bg-red-900/40 border border-red-500/30 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      <AnimatePresence mode="wait">
        {loading && <LoadingSkeleton key="loading" />}

        {!loading && !data && !error && (
          <EmptyState
            key="empty"
            icon="🔍"
            title="一句话选股"
            description="用自然语言描述你想找的股票，系统自动识别行业、风格、技术面和财务条件，基于五维评分模型进行筛选"
            action={{ label: '试试「高ROE低PE的白酒股」', onClick: () => setQuery('高ROE低PE的白酒股') }}
          />
        )}

        {data && !loading && (
          <motion.div key="result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              <MetricCard
                label="大盘评分"
                value={`${data.market_score?.toFixed(0) ?? '--'}分`}
                subtitle={`趋势: ${data.market_trend}`}
              />
              <MetricCard
                label="入池数量"
                value={data.total_in_pool}
                trend={data.total_in_pool > 0 ? 'up' : 'neutral'}
                subtitle="总分 ≥ 70"
              />
              <MetricCard label="候选数量" value={data.candidates.length} />
              <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30">
                <p className="text-xs text-slate-400 mb-1">筛选来源</p>
                <p className="text-sm text-slate-300 truncate">{data.pool_source}</p>
              </div>
            </div>

            {data.candidates.length > 0 ? (
              data.candidates.map((stock, idx) => (
                <CandidateCard key={stock.code} stock={stock} idx={idx} />
              ))
            ) : (
              <div className="text-center py-12 text-slate-400 text-sm">
                当前无股票满足条件，试试换个描述
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <p className="text-center text-xs text-slate-500 pb-8">
        仅用于学习研究，不构成投资建议
      </p>
    </div>
  )
}
