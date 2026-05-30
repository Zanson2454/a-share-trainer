interface TopBarProps {
  onMenuClick: () => void
}

const PAGE_TITLES: Record<string, string> = {
  '/': '仪表盘总览',
  '/learning': '每日学习',
  '/premarket': '盘前分析',
  '/screening': '选股评分',
  '/analysis': '个股分析',
  '/review': '每日复盘',
  '/strategies': '策略管理',
  '/backtest': '策略回测',
}

import { useLocation } from 'react-router-dom'

export default function TopBar({ onMenuClick }: TopBarProps) {
  const location = useLocation()
  const title = PAGE_TITLES[location.pathname] ?? 'A股训练系统'

  return (
    <header className="h-14 bg-slate-800/80 backdrop-blur-sm border-b border-slate-700/30 flex items-center justify-between px-4 lg:px-6 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 transition-colors"
          aria-label="Toggle menu"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <h2 className="text-sm font-medium text-slate-200">{title}</h2>
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500/70" />
          AKShare
        </span>
      </div>
    </header>
  )
}
