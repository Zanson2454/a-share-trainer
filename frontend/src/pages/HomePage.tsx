import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { getHealth } from '../api/client'

const FEATURES = [
  { path: '/learning', icon: '📚', title: '每日学习', desc: '技术面、基本面、风控的系统化学习' },
  { path: '/premarket', icon: '🌅', title: '盘前分析', desc: '大盘环境、政策方向、热点板块' },
  { path: '/screening', icon: '🔍', title: '选股评分', desc: '五维评分模型筛选候选股' },
  { path: '/analysis', icon: '🔬', title: '个股分析', desc: '技术面+基本面深度分析' },
  { path: '/review', icon: '📊', title: '每日复盘', desc: '复盘模板，修正交易规则' },
  { path: '/strategies', icon: '📋', title: '策略管理', desc: '策略库管理与创建' },
  { path: '/backtest', icon: '⚡', title: '策略回测', desc: '历史回测验证策略表现' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  useEffect(() => {
    getHealth()
      .then(d => setApiStatus(d.status === 'ok' ? 'online' : 'offline'))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* 欢迎区 */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-8"
      >
        <h1 className="text-3xl font-bold text-slate-100 mb-2">
          A股训练系统
        </h1>
        <p className="text-slate-300 max-w-lg mx-auto">
          教练型投资学习助手 — 不提供买卖建议，引导你形成自己的交易规则
        </p>
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className={`w-2 h-2 rounded-full ${
            apiStatus === 'online' ? 'bg-green-500' :
            apiStatus === 'offline' ? 'bg-red-500' : 'bg-amber-500'
          }`} />
          <span className="text-xs text-slate-400">
            API: {apiStatus === 'checking' ? '检测中...' :
                   apiStatus === 'online' ? '已连接' : '未连接'}
          </span>
        </div>
      </motion.div>

      {/* 功能卡片网格 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {FEATURES.map((f, i) => (
          <motion.button
            key={f.path}
            onClick={() => navigate(f.path)}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-slate-800/60 hover:bg-slate-700/60 border border-slate-700/30 rounded-xl p-5 text-left
                       transition-all hover:border-blue-500/30 hover:shadow-lg group"
          >
            <span className="text-2xl mb-3 block">{f.icon}</span>
            <h3 className="text-sm font-semibold text-slate-100 mb-1 group-hover:text-blue-400 transition-colors">
              {f.title}
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {f.desc}
            </p>
          </motion.button>
        ))}
      </div>

      {/* 核心原则 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/30"
      >
        <h2 className="text-sm font-semibold text-slate-100 mb-4">核心原则</h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: '不做建议', desc: '教练型助手，帮你形成自己的判断，不给买卖结论' },
            { label: '数据驱动', desc: '基于AKShare免费数据源，所有分析有据可查' },
            { label: '持续迭代', desc: '每日学习 → 回测 → 复盘 → 修正规则的闭环' },
          ].map(p => (
            <div key={p.label} className="text-center">
              <p className="text-sm font-medium text-slate-100 mb-1">{p.label}</p>
              <p className="text-xs text-slate-400 leading-relaxed">{p.desc}</p>
            </div>
          ))}
        </div>
      </motion.div>

      <p className="text-center text-xs text-slate-400 pb-8">
        仅用于学习研究，不构成投资建议
      </p>
    </div>
  )
}
