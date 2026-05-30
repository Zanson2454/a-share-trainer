import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  getStrategies, getStrategy, createStrategy, updateStrategy, deleteStrategy,
  getIndicatorReference,
  type StrategySummary, type StrategyFull, type ConditionRule, type IndicatorDef,
} from '../api/client'

const EMPTY_CONDITION: ConditionRule = {
  indicator: 'close',
  operator: '>',
  value: '',
  desc: '',
}

const STATUS_OPTIONS = ['开发中', '测试中', '实盘中', '已废弃']
const ENV_OPTIONS = ['进攻', '震荡', '防守']

function ConditionRow({
  rule, onChange, onRemove, canRemove, connectors, operators, indicators,
}: {
  rule: ConditionRule
  onChange: (r: ConditionRule) => void
  onRemove: () => void
  canRemove: boolean
  connectors: string[]
  operators: { symbol: string; label: string }[]
  indicators: Record<string, IndicatorDef>
}) {
  const isCross = rule.operator === 'cross_above' || rule.operator === 'cross_below'

  return (
    <div className="flex items-center gap-2 mb-2">
      {rule.connector && (
        <select
          value={rule.connector}
          onChange={e => onChange({ ...rule, connector: e.target.value })}
          className="w-16 bg-blue-900/40 border border-blue-500/30 rounded px-2 py-1.5 text-xs text-blue-400
                     focus:outline-none"
        >
          {connectors.map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      )}
      <span className="text-xs text-slate-500 w-6 text-center">
        {!rule.connector && 'IF'}
      </span>
      <select
        value={rule.indicator}
        onChange={e => onChange({ ...rule, indicator: e.target.value })}
        className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200
                   focus:outline-none focus:border-blue-500"
      >
        {Object.entries(indicators).map(([key, ind]) => (
          <option key={key} value={key}>{ind.label} ({ind.example})</option>
        ))}
      </select>
      <select
        value={rule.operator}
        onChange={e => onChange({ ...rule, operator: e.target.value })}
        className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200
                   focus:outline-none focus:border-blue-500"
      >
        {operators.map(op => (
          <option key={op.symbol} value={op.symbol}>{op.label}</option>
        ))}
      </select>
      {isCross ? (
        <select
          value={rule.value}
          onChange={e => onChange({ ...rule, value: e.target.value })}
          className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200
                     focus:outline-none focus:border-blue-500"
        >
          {Object.entries(indicators).map(([key, ind]) => (
            <option key={key} value={key}>{ind.label} ({ind.example})</option>
          ))}
        </select>
      ) : (
        <input
          type="text"
          value={rule.value}
          onChange={e => onChange({ ...rule, value: e.target.value })}
          placeholder="值，如 ma(20), 30"
          className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200
                     placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
        />
      )}
      <input
        type="text"
        value={rule.desc}
        onChange={e => onChange({ ...rule, desc: e.target.value })}
        placeholder="描述"
        className="w-40 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-200
                   placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
      />
      {canRemove && (
        <button
          onClick={onRemove}
          className="text-red-400 hover:text-red-300 text-sm px-1"
        >
          ×
        </button>
      )}
    </div>
  )
}

export default function StrategyPage() {
  const [strategies, setStrategies] = useState<StrategySummary[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [data, setData] = useState<StrategyFull | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [tab, setTab] = useState<'entry' | 'exit' | 'settings'>('entry')
  const [indicators, setIndicators] = useState<Record<string, IndicatorDef>>({})
  const [operators, setOperators] = useState<{ symbol: string; label: string }[]>([])
  const [connectors, setConnectors] = useState<string[]>([])
  const [message, setMessage] = useState('')

  useEffect(() => {
    Promise.all([
      getStrategies(),
      getIndicatorReference(),
    ]).then(([d, ref]) => {
      setStrategies(d.strategies)
      setIndicators(ref.indicators)
      setOperators(ref.operators)
      setConnectors(ref.connectors)
    }).finally(() => setLoading(false))
  }, [])

  const handleSelect = async (name: string) => {
    setSelected(name)
    setMessage('')
    const detail = await getStrategy(name)
    setData(detail)
  }

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    try {
      const result = await createStrategy(name)
      setStrategies(prev => [...prev, { name: result.name, status: result.status, updated: result.updated, condition_count: 0 }])
      setNewName('')
      setSelected(result.name)
      setData(result)
    } catch (e: any) {
      setMessage(e?.response?.data?.detail ?? '创建失败')
    }
    setCreating(false)
  }

  const handleDelete = async () => {
    if (!selected || !confirm(`确定删除策略「${selected}」？`)) return
    await deleteStrategy(selected)
    setStrategies(prev => prev.filter(s => s.name !== selected))
    setSelected(null)
    setData(null)
  }

  const handleSave = async () => {
    if (!data || !selected) return
    setSaving(true)
    setMessage('')
    try {
      const result = await updateStrategy(selected, {
        name: data.name !== selected ? data.name : undefined,
        entry_conditions: data.entry_conditions,
        exit_conditions: data.exit_conditions,
        stop_loss_pct: data.stop_loss_pct,
        take_profit_pct: data.take_profit_pct,
        position_pct: data.position_pct,
        status: data.status,
        market_env: data.market_env,
        notes: data.notes,
      })
      if (data.name !== selected) {
        setStrategies(prev => prev.map(s => s.name === selected ? { ...s, name: data.name } : s))
        setSelected(data.name)
      }
      setData(result)
      setMessage('保存成功')
      setTimeout(() => setMessage(''), 2000)
    } catch (e: any) {
      setMessage(e?.response?.data?.detail ?? '保存失败')
    }
    setSaving(false)
  }

  const addCondition = (type: 'entry' | 'exit' | 'afterEntry') => {
    if (!data) return
    const key = type === 'entry' ? 'entry_conditions' : 'exit_conditions'
    const conditions = [...data[key], { ...EMPTY_CONDITION }]
    if (conditions.length > 1) {
      conditions[conditions.length - 1].connector = 'AND'
    }
    setData({ ...data, [key]: conditions })
  }

  const updateCondition = (type: 'entry' | 'exit', idx: number, rule: ConditionRule) => {
    if (!data) return
    const key = type === 'entry' ? 'entry_conditions' : 'exit_conditions'
    const conditions = data[key].map((c, i) => i === idx ? rule : c)
    setData({ ...data, [key]: conditions })
  }

  const removeCondition = (type: 'entry' | 'exit', idx: number) => {
    if (!data) return
    const key = type === 'entry' ? 'entry_conditions' : 'exit_conditions'
    const conditions = data[key].filter((_, i) => i !== idx)
    if (conditions.length > 0) {
      conditions[0] = { ...conditions[0], connector: undefined }
    }
    setData({ ...data, [key]: conditions })
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex gap-6">
        {/* 左侧列表 */}
        <div className="w-56 shrink-0 space-y-3">
          <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30">
            <h3 className="text-sm font-semibold text-slate-100 mb-3">策略库</h3>
            {loading ? (
              <p className="text-xs text-slate-400">加载中...</p>
            ) : strategies.length === 0 ? (
              <p className="text-xs text-slate-400">暂无策略，创建一个</p>
            ) : (
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {strategies.map(s => (
                  <button
                    key={s.name}
                    onClick={() => handleSelect(s.name)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      selected === s.name
                        ? 'bg-blue-900/40 text-blue-400'
                        : 'text-slate-300 hover:bg-slate-700/60 hover:text-white'
                    }`}
                  >
                    <div className="font-medium truncate">{s.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {s.status} · {s.condition_count}条规则
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30">
            <h3 className="text-sm font-semibold text-slate-100 mb-2">新建</h3>
            <input
              type="text"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
              placeholder="策略名称"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm
                         placeholder:text-slate-500 focus:outline-none focus:border-blue-500 mb-2"
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="w-full py-1.5 bg-blue-500 text-slate-100 rounded-lg text-sm font-medium
                         hover:bg-blue-600 disabled:opacity-40 transition-all"
            >
              {creating ? '创建中...' : '创建'}
            </button>
          </div>

          {selected && (
            <button
              onClick={handleDelete}
              className="w-full py-1.5 text-red-400 text-sm hover:text-red-300 transition-colors"
            >
              删除当前策略
            </button>
          )}
        </div>

        {/* 右侧编辑器 */}
        <div className="flex-1 min-w-0">
          {!selected || !data ? (
            <div className="bg-slate-800/60 rounded-xl p-12 border border-slate-700/30 text-center">
              <p className="text-slate-400 text-sm">选择或创建一个策略开始编辑</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 标题栏 */}
              <div className="bg-slate-800/60 rounded-xl p-4 border border-slate-700/30 flex items-center gap-4">
                <input
                  type="text"
                  value={data.name}
                  onChange={e => setData({ ...data, name: e.target.value })}
                  className="text-lg font-semibold text-slate-100 bg-transparent border-b border-transparent
                             hover:border-slate-600 focus:border-blue-500 focus:outline-none px-1"
                />
                <select
                  value={data.status}
                  onChange={e => setData({ ...data, status: e.target.value })}
                  className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300
                             focus:outline-none focus:border-blue-500"
                >
                  {STATUS_OPTIONS.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <div className="flex-1" />
                {message && (
                  <span className={`text-xs ${message.includes('成功') ? 'text-green-400' : 'text-red-400'}`}>
                    {message}
                  </span>
                )}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-1.5 bg-green-500 text-slate-100 rounded-lg text-sm font-medium
                             hover:bg-green-600 disabled:opacity-40 transition-all"
                >
                  {saving ? '保存中...' : '保存'}
                </button>
              </div>

              {/* Tab 切换 */}
              <div className="flex gap-2">
                {([
                  ['entry', '买入条件'],
                  ['exit', '卖出条件'],
                  ['settings', '参数设置'],
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

              {/* 编辑器内容 */}
              <AnimatePresence mode="wait">
                {(tab === 'entry' || tab === 'exit') && (
                  <motion.div
                    key={tab}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-semibold text-slate-100">
                        {tab === 'entry' ? '买入条件' : '卖出条件'}
                      </h3>
                      <button
                        onClick={() => addCondition(tab)}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        + 添加条件
                      </button>
                    </div>

                    {(tab === 'entry' ? data.entry_conditions : data.exit_conditions).length === 0 ? (
                      <p className="text-xs text-slate-500 py-6 text-center">
                        暂无条件，点击"+ 添加条件"开始定义
                      </p>
                    ) : (
                      (tab === 'entry' ? data.entry_conditions : data.exit_conditions).map((rule, idx) => (
                        <ConditionRow
                          key={idx}
                          rule={rule}
                          onChange={r => updateCondition(tab, idx, r)}
                          onRemove={() => removeCondition(tab, idx)}
                          canRemove={(tab === 'entry' ? data.entry_conditions : data.exit_conditions).length > 1 || idx > 0}
                          connectors={connectors}
                          operators={operators}
                          indicators={indicators}
                        />
                      ))
                    )}

                    {/* 公式预览 */}
                    <div className="mt-4 pt-3 border-t border-slate-700/50">
                      <p className="text-xs text-slate-500 mb-1">公式预览</p>
                      <code className="text-xs text-slate-300 font-mono bg-slate-900 rounded px-3 py-2 block">
                        {(tab === 'entry' ? data.entry_conditions : data.exit_conditions).map((r, i) => {
                          const prefix = i === 0 ? '' : ` ${r.connector || 'AND'} `
                          return `${prefix}${r.indicator} ${r.operator} ${r.value}`
                        }).join('') || '(空)'}
                      </code>
                    </div>
                  </motion.div>
                )}

                {tab === 'settings' && (
                  <motion.div
                    key="settings"
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/30 space-y-4"
                  >
                    <h3 className="text-sm font-semibold text-slate-100">参数设置</h3>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs text-slate-400 block mb-1">止损 (%)</label>
                        <input
                          type="number"
                          value={data.stop_loss_pct}
                          onChange={e => setData({ ...data, stop_loss_pct: Number(e.target.value) })}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200
                                     focus:outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-slate-400 block mb-1">止盈 (%)</label>
                        <input
                          type="number"
                          value={data.take_profit_pct}
                          onChange={e => setData({ ...data, take_profit_pct: Number(e.target.value) })}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200
                                     focus:outline-none focus:border-blue-500"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-slate-400 block mb-1">仓位 (%)</label>
                        <input
                          type="number"
                          value={data.position_pct}
                          onChange={e => setData({ ...data, position_pct: Number(e.target.value) })}
                          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200
                                     focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-2">适用市场环境</label>
                      <div className="flex gap-3">
                        {ENV_OPTIONS.map(env => (
                          <label key={env} className="flex items-center gap-1.5 text-sm text-slate-300">
                            <input
                              type="checkbox"
                              checked={data.market_env.includes(env)}
                              onChange={e => {
                                const next = e.target.checked
                                  ? [...data.market_env, env]
                                  : data.market_env.filter(v => v !== env)
                                setData({ ...data, market_env: next })
                              }}
                              className="rounded"
                            />
                            {env}
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-2">备注</label>
                      <textarea
                        value={data.notes}
                        onChange={e => setData({ ...data, notes: e.target.value })}
                        rows={3}
                        placeholder="策略思路、参考来源等"
                        className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200
                                   placeholder:text-slate-500 focus:outline-none focus:border-blue-500 resize-none"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
