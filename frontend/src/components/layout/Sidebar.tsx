import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'

const NAV_ITEMS = [
  { to: '/', label: '总览', icon: '◉', end: true },
  { to: '/learning', label: '学习', icon: '📚' },
  { to: '/premarket', label: '盘前', icon: '🌅' },
  { to: '/screening', label: '选股', icon: '🔍' },
  { to: '/analysis', label: '个股', icon: '🔬' },
  { to: '/review', label: '复盘', icon: '📊' },
  { to: '/strategies', label: '策略', icon: '📋' },
  { to: '/backtest', label: '回测', icon: '⚡' },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* 移动端遮罩 */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* 侧边栏 */}
      <aside
        className={`fixed top-0 left-0 h-full w-56 bg-slate-800 border-r border-slate-700/30 flex flex-col z-50
          transition-transform duration-200 lg:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="px-5 py-5 border-b border-slate-700/30">
          <h1 className="text-lg font-semibold text-slate-100 tracking-tight">
            A股训练系统
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">教练型股票分析助手</p>
        </div>

        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-500/15 text-blue-400'
                    : 'text-slate-400 hover:bg-slate-700/60 hover:text-slate-200'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className="text-base">{item.icon}</span>
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="ml-auto w-1 h-5 rounded-full bg-blue-500"
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="px-5 py-3 border-t border-slate-700/30">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="w-2 h-2 rounded-full bg-green-500/70" />
            v1.0.0
          </div>
        </div>
      </aside>
    </>
  )
}
