import { useState, useCallback } from 'react'
import { getStockAnalysis } from '../api/client'
import type { StockAnalysisResponse } from '../types'

export function useStockAnalysis() {
  const [data, setData] = useState<StockAnalysisResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const analyze = useCallback(async (code: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await getStockAnalysis(code)
      setData(result)
      return result
    } catch (e: any) {
      const msg = e?.response?.data?.detail ?? e?.message ?? '请求失败'
      setError(msg)
      setData(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, loading, error, analyze }
}
