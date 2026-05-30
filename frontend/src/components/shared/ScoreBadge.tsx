interface ScoreBadgeProps {
  score: number
  max?: number
  label?: string
}

export default function ScoreBadge({ score, max = 100, label }: ScoreBadgeProps) {
  const ratio = score / max
  const color =
    ratio >= 0.7 ? 'bg-green-500 text-black' :
    ratio >= 0.4 ? 'bg-amber-500 text-black' :
    'bg-red-500 text-white'

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${color}`}>
      {score}{max !== 100 ? `/${max}` : ''}
      {label && <span className="opacity-70 ml-0.5">{label}</span>}
    </span>
  )
}
