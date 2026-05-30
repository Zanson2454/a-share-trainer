import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import type { EquityPoint } from '../../types'

interface EquityCurveProps {
  data: EquityPoint[]
  benchmarkReturn?: number
}

export default function EquityCurve({ data, benchmarkReturn }: EquityCurveProps) {
  if (!data.length) return null

  const initial = data[0]?.equity ?? 100000
  const chartData = data.map(p => ({
    ...p,
    equity: Number(p.equity.toFixed(0)),
    pct: Number((((p.equity - initial) / initial) * 100).toFixed(2)),
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#334155' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={v => `${(v / 10000).toFixed(0)}万`}
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #475569',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#f8fafc',
          }}
          formatter={(value: any, name: any) => [
            name === 'pct' ? `${value}%` : `${Number(value).toLocaleString()}元`,
            name === 'pct' ? '收益率' : '权益',
          ]}
        />
        <Legend
          wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="#3b82f6"
          fill="url(#equityGradient)"
          strokeWidth={2}
          name="权益"
        />
        {benchmarkReturn != null && (
          <Line
            type="monotone"
            dataKey="pct"
            stroke="#22c55e"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            name="收益率%"
            dot={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
