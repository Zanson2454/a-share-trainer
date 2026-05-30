export function pct(v: number, decimals = 1): string {
  return `${(v * 100).toFixed(decimals)}%`
}

export function money(v: number): string {
  if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
  if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(0)}万`
  return v.toFixed(2)
}

export function ratio(v: number, decimals = 2): string {
  return v.toFixed(decimals)
}
