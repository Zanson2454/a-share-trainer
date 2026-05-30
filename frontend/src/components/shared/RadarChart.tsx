import {
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'

interface RadarChartProps {
  data: {
    subject: string
    score: number
    fullMark: number
  }[]
}

export default function RadarChart({ data }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <RechartsRadar data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="#475569" strokeDasharray="3 3" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 'auto']}
          tick={{ fill: '#64748b', fontSize: 10 }}
          axisLine={false}
        />
        <Radar
          name="评分"
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.2}
          strokeWidth={2}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  )
}
