import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { EquityPoint } from '../../types'

function calcDrawdowns(data: EquityPoint[]) {
  let peak = data[0]?.equity ?? 0
  return data.map(p => {
    peak = Math.max(peak, p.equity)
    const dd = peak > 0 ? ((peak - p.equity) / peak) * 100 : 0
    return { date: p.date, drawdown: Number(dd.toFixed(2)) }
  })
}

interface DrawdownAreaProps {
  equityCurve: EquityPoint[]
}

export default function DrawdownArea({ equityCurve }: DrawdownAreaProps) {
  const data = calcDrawdowns(equityCurve)

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#334155' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={v => `${v}%`}
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          reversed
          width={50}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #475569',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#f8fafc',
          }}
          formatter={(value) => [`-${value}%`, '回撤']}
        />
        <defs>
          <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#ef4444"
          fill="url(#ddGradient)"
          strokeWidth={1.5}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
