import { useState, useMemo } from 'react'
import type { TradeRecord } from '../../types'

interface TradeTableProps {
  trades: TradeRecord[]
}

export default function TradeTable({ trades }: TradeTableProps) {
  const [showAll, setShowAll] = useState(false)
  const display = showAll ? trades : trades.slice(0, 10)

  const stats = useMemo(() => {
    const sells = trades.filter(t => t.action === 'sell')
    const wins = sells.filter(t => {
      // Find preceding buy to calculate profit
      const idx = trades.indexOf(t)
      const buy = trades.slice(0, idx).reverse().find(b => b.action === 'buy')
      return buy && t.price > buy.price
    })
    return {
      totalSignals: trades.length,
      sellCount: sells.length,
      winCount: wins.length,
    }
  }, [trades])

  return (
    <div>
      <div className="flex items-center gap-4 mb-3 text-xs text-slate-400">
        <span>信号: {stats.totalSignals}</span>
        <span>卖出: {stats.sellCount}</span>
        <span>盈利: {stats.winCount}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/30 text-slate-400">
              <th className="text-left py-2 px-3 font-medium">日期</th>
              <th className="text-left py-2 px-3 font-medium">方向</th>
              <th className="text-right py-2 px-3 font-medium">价格</th>
              <th className="text-right py-2 px-3 font-medium">数量</th>
              <th className="text-left py-2 px-3 font-medium">原因</th>
            </tr>
          </thead>
          <tbody>
            {display.map((t, i) => (
              <tr key={i} className="border-b border-slate-700/30 hover:bg-slate-700/60 transition-colors">
                <td className="py-2 px-3 text-slate-300">{t.date}</td>
                <td className="py-2 px-3">
                  <span className={t.action === 'buy' ? 'text-red-400' : 'text-green-400'}>
                    {t.action === 'buy' ? '买入' : '卖出'}
                  </span>
                </td>
                <td className="py-2 px-3 text-right text-white">{t.price.toFixed(2)}</td>
                <td className="py-2 px-3 text-right text-slate-300">{t.quantity}</td>
                <td className="py-2 px-3 text-slate-400 max-w-64 truncate">{t.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {trades.length > 10 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-3 text-xs text-blue-400 hover:text-blue-400 transition-colors"
        >
          {showAll ? '收起' : `查看全部 ${trades.length} 条记录`}
        </button>
      )}
    </div>
  )
}
