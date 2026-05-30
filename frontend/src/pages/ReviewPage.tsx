import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getReviewTemplate, getOperations, getOperationStats,
  createOperation, deleteOperation,
  type OperationRecord, type OperationStats,
  searchStocks,
} from '../api/client'
import MarkdownPreview from '../components/shared/MarkdownPreview'
import LoadingSkeleton from '../components/shared/LoadingSkeleton'

const ACTIONS = ['buy', 'sell', 'hold'] as const
const ACTION_LABELS: Record<string, string> = { buy: '买入', sell: '卖出', hold: '持有' }

export default function ReviewPage() {
  const [tab, setTab] = useState<'daily' | 'operations'>('daily')
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // 操作复盘
  const [ops, setOps] = useState<OperationRecord[]>([])
  const [stats, setStats] = useState<OperationStats | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<Partial<OperationRecord>>({
    date: new Date().toISOString().slice(0, 10),
    action: 'buy',
    code: '',
    name: '',
    price: 0,
    quantity: 100,
    reason: '',
    outcome: '',
    profit_pct: null,
    lesson: '',
    tags: [],
  })

  const loadOps = async () => {
    const [opsData, statsData] = await Promise.all([getOperations(), getOperationStats()])
    setOps(opsData.operations)
    setStats(statsData)
  }

  useEffect(() => {
    getReviewTemplate()
      .then(d => setContent(d.content))
      .finally(() => setLoading(false))
    loadOps()
  }, [])

  const handleCreateOp = async () => {
    if (!form.code) return
    await createOperation(form)
    setShowForm(false)
    setForm({
      date: new Date().toISOString().slice(0, 10),
      action: 'buy',
      code: '',
      name: '',
      price: 0,
      quantity: 100,
      reason: '',
      outcome: '',
      profit_pct: null,
      lesson: '',
      tags: [],
    })
    loadOps()
  }

  const handleDeleteOp = async (id: string) => {
    if (!confirm('删除此操作记录？')) return
    await deleteOperation(id)
    loadOps()
  }

  const lookupName = async (code: string) => {
    if (code.length < 2) return
    try {
      const res = await searchStocks(code)
      if (res.results.length > 0) {
        setForm(f => ({ ...f, name: res.results[0].name, code: res.results[0].code }))
      }
    } catch {}
  }

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex gap-2">
        {([
          ['daily', '每日复盘'],
          ['operations', '操作复盘'],
        ] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === key
                ? 'bg-blue-900/40 text-blue-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === 'daily' && (
          <motion.div
            key="daily"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {loading ? (
              <LoadingSkeleton />
            ) : content ? (
              <div className="bg-slate-800/60 rounded-xl p-6 border border-slate-700/30">
                <MarkdownPreview content={content} />
              </div>
            ) : (
              <div className="bg-slate-800/60 rounded-xl p-8 border border-slate-700/30 text-center">
                <p className="text-slate-400 text-sm">复盘数据加载失败</p>
              </div>
            )}
          </motion.div>
        )}

        {tab === 'operations' && (
          <motion.div
            key="operations"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {stats && (
              <div className="grid grid-cols-6 gap-3">
                {[
                  ['总操作', stats.total],
                  ['买入', stats.buy_count],
                  ['卖出', stats.sell_count],
                  ['盈利', stats.win_count],
                  ['亏损', stats.loss_count],
                  ['胜率', `${(stats.win_rate * 100).toFixed(0)}%`],
                ].map(([label, val]) => (
                  <div key={label as string} className="bg-slate-800/60 rounded-lg p-3 text-center border border-slate-700/30">
                    <p className="text-xs text-slate-400">{label}</p>
                    <p className="text-lg font-bold text-slate-100">{val}</p>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => setShowForm(v => !v)}
              className="px-4 py-2 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium
                         hover:bg-blue-600 transition-all"
            >
              {showForm ? '取消' : '+ 记录操作'}
            </button>

            {showForm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30 space-y-3"
              >
                <div className="grid grid-cols-4 gap-3">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">日期</label>
                    <input
                      type="date"
                      value={form.date || ''}
                      onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">代码</label>
                    <input
                      type="text"
                      value={form.code || ''}
                      onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                      onBlur={e => lookupName(e.target.value)}
                      placeholder="600519"
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">名称</label>
                    <input
                      type="text"
                      value={form.name || ''}
                      onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                      placeholder="自动获取"
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">操作</label>
                    <select
                      value={form.action || 'buy'}
                      onChange={e => setForm(f => ({ ...f, action: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    >
                      {ACTIONS.map(a => (
                        <option key={a} value={a}>{ACTION_LABELS[a]}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">价格</label>
                    <input
                      type="number" step="0.01"
                      value={form.price || 0}
                      onChange={e => setForm(f => ({ ...f, price: Number(e.target.value) }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">数量(股)</label>
                    <input
                      type="number"
                      value={form.quantity || 0}
                      onChange={e => setForm(f => ({ ...f, quantity: Number(e.target.value) }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">盈亏(%)</label>
                    <input
                      type="number" step="0.1"
                      value={form.profit_pct ?? ''}
                      onChange={e => setForm(f => ({ ...f, profit_pct: e.target.value ? Number(e.target.value) : null }))}
                      placeholder="卖出后填"
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">标签(逗号分隔)</label>
                    <input
                      type="text"
                      value={(form.tags || []).join(',')}
                      onChange={e => setForm(f => ({ ...f, tags: e.target.value.split(',').map(s => s.trim()).filter(Boolean) }))}
                      placeholder="追涨, 突破"
                      className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">操作理由</label>
                  <input
                    type="text"
                    value={form.reason || ''}
                    onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
                    placeholder="为什么做这笔操作？"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">教训/总结</label>
                  <input
                    type="text"
                    value={form.lesson || ''}
                    onChange={e => setForm(f => ({ ...f, lesson: e.target.value }))}
                    placeholder="学到了什么？"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={handleCreateOp}
                  disabled={!form.code}
                  className="px-4 py-2 bg-green-500 text-slate-100 rounded-lg text-sm font-medium
                             hover:bg-green-600 disabled:opacity-40 transition-all"
                >
                  保存
                </button>
              </motion.div>
            )}

            {ops.length === 0 ? (
              <div className="bg-slate-800/60 rounded-xl p-12 border border-slate-700/30 text-center">
                <p className="text-slate-400 text-sm">暂无操作记录，点击"+ 记录操作"开始</p>
              </div>
            ) : (
              <div className="space-y-2">
                {ops.map(op => (
                  <div
                    key={op.id}
                    className="bg-slate-800/60 rounded-lg p-4 border border-slate-700/30 flex items-center gap-4"
                  >
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      op.action === 'buy' ? 'bg-red-900/30 text-red-400' :
                      op.action === 'sell' ? 'bg-green-900/30 text-green-400' :
                      'bg-slate-700/50 text-slate-400'
                    }`}>
                      {ACTION_LABELS[op.action] || op.action}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-100">{op.name || op.code}</span>
                        <span className="text-xs text-slate-500">{op.code}</span>
                        <span className="text-xs text-slate-500">{op.date}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {op.price > 0 && `${op.price.toFixed(2)}元 × ${op.quantity}股`}
                        {op.reason && ` · ${op.reason}`}
                      </div>
                    </div>
                    {op.profit_pct != null && (
                      <span className={`text-sm font-medium ${
                        op.profit_pct >= 0 ? 'text-red-400' : 'text-green-400'
                      }`}>
                        {op.profit_pct >= 0 ? '+' : ''}{op.profit_pct.toFixed(1)}%
                      </span>
                    )}
                    <button
                      onClick={() => handleDeleteOp(op.id)}
                      className="text-red-400/50 hover:text-red-400 text-sm"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
