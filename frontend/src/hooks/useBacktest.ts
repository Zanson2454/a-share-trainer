import { useState, useCallback } from 'react'
import { postBacktest } from '../api/client'
import type { BacktestResponse } from '../types'

export function useBacktest() {
  const [data, setData] = useState<BacktestResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (params: {
    strategy_name: string
    start_date: string
    end_date: string
    code?: string
  }) => {
    setLoading(true)
    setError(null)
    try {
      const result = await postBacktest(params)
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

  return { data, loading, error, run }
}
