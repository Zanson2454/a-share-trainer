import { motion } from 'framer-motion'
import { usePremarket } from '../hooks/usePremarket'
import MetricCard from '../components/shared/MetricCard'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'

export default function PremarketPage() {
  const { data, loading, error } = usePremarket()

  if (loading) return <div className="max-w-6xl mx-auto"><LoadingSkeleton /></div>

  if (error || !data) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-900/40 border border-red-500/30 rounded-xl p-4 text-sm text-red-400">
          {error ?? '数据加载失败'}
        </div>
      </div>
    )
  }

  const env = data.market_env
  const trendColor =
    env.trend === '进攻' ? 'text-green-400' :
    env.trend === '防守' ? 'text-red-400' : 'text-amber-400'

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      {/* 大盘环境 */}
      <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
        <h2 className="text-sm font-semibold text-slate-100 mb-4">大盘环境</h2>
        <div className="grid grid-cols-4 gap-4">
          <MetricCard
            label="上证指数"
            value={env.close.toFixed(2)}
            trend={env.change_pct >= 0 ? 'up' : 'down'}
            subtitle={`${env.change_pct >= 0 ? '+' : ''}${env.change_pct.toFixed(2)}%`}
          />
          <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30">
            <p className="text-xs text-slate-400 mb-1">大盘判断</p>
            <p className={`text-2xl font-bold ${trendColor}`}>{env.trend}</p>
            <p className="text-xs text-slate-400 mt-1">{env.advice}</p>
          </div>
          <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30 col-span-2">
            <p className="text-xs text-slate-400 mb-2">五维研究闭环</p>
            <div className="flex items-center justify-between text-xs">
              <span className="px-3 py-1.5 bg-blue-900/40 text-blue-400 rounded-full">技术面</span>
              <span className="text-slate-400">↔</span>
              <span className="px-3 py-1.5 bg-green-900/40 text-green-400 rounded-full">基本面</span>
              <span className="text-slate-400">↔</span>
              <span className="px-3 py-1.5 bg-amber-900/20 text-amber-400 rounded-full">大盘环境</span>
              <span className="text-slate-400">↔</span>
              <span className="px-3 py-1.5 bg-red-900/40 text-red-400 rounded-full">热点新闻</span>
              <span className="text-slate-400">↔</span>
              <span className="px-3 py-1.5 bg-slate-900 text-slate-300 rounded-full">国家政策</span>
            </div>
          </div>
        </div>
      </div>

      {/* 热点板块 */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
          <h3 className="text-sm font-semibold text-slate-100 mb-3">热点板块</h3>
          {data.hot_sectors.length > 0 ? (
            <div className="space-y-2">
              {data.hot_sectors.map((s, i) => (
                <div
                  key={i}
                  className={`flex items-center justify-between p-3 rounded-lg ${
                    s.category === '主线'
                      ? 'bg-green-900/30 border border-green-500/20'
                      : s.category === '支线'
                      ? 'bg-blue-900/30 border border-blue-500/20'
                      : 'bg-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      s.category === '主线' ? 'bg-green-500' :
                      s.category === '支线' ? 'bg-blue-500' : 'bg-slate-400'
                    }`} />
                    <span className="text-sm text-white">{s.name}</span>
                    <span className="text-xs text-slate-400">({s.category})</span>
                  </div>
                  <span className={`text-sm font-medium ${
                    s.change_pct >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {s.change_pct >= 0 ? '+' : ''}{s.change_pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-400">板块数据暂不可用</p>
          )}
          {data.main_lines.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-700/30">
              <p className="text-xs text-slate-400">
                今日主线: <span className="text-green-400">{data.main_lines.join('、')}</span>
              </p>
            </div>
          )}
        </div>

        {/* 风险事件 */}
        <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
          <h3 className="text-sm font-semibold text-slate-100 mb-3">风险事件</h3>
          <div className="space-y-2">
            {data.risks.map((r, i) => (
              <div key={i} className="bg-slate-800/80 rounded-lg p-3">
                <p className="text-sm font-medium text-white">{r.risk_type}</p>
                <p className="text-xs text-slate-400 mt-1">
                  {r.event || '待补充'}
                  {r.assessment && ` — ${r.assessment}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 政策方向 */}
      <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30">
        <h3 className="text-sm font-semibold text-slate-100 mb-3">政策方向</h3>
        <div className="grid grid-cols-3 gap-4">
          {data.policy_direction.map((p, i) => (
            <div key={i} className="bg-slate-800/80 rounded-lg p-4">
              <p className="text-xs font-medium text-slate-100 mb-1">{p.level}</p>
              <p className="text-xs text-slate-400">{p.content}</p>
              {p.status && (
                <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-amber-900/20 text-amber-400 rounded">
                  {p.status}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 观察问题 */}
      <div className="bg-slate-800/60 rounded-xl p-5 border border-l-4 border-l-blue-500 border-slate-700/30">
        <h3 className="text-sm font-semibold text-slate-100 mb-3">今日观察问题</h3>
        <ol className="space-y-2">
          {data.observe_questions.map((q, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
              <span className="text-blue-400 font-medium">{i + 1}.</span>
              {q}
            </li>
          ))}
        </ol>
      </div>

      <p className="text-center text-xs text-slate-400 pb-8">
        仅用于学习研究，不构成投资建议
      </p>
    </motion.div>
  )
}
