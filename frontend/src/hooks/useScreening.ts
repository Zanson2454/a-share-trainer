import { useState, useEffect, useCallback } from 'react'
import { getScreening } from '../api/client'
import type { ScreeningResponse } from '../types'

export function useScreening(codes?: string[]) {
  const [data, setData] = useState<ScreeningResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getScreening(codes)
      setData(result)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? '请求失败')
    } finally {
      setLoading(false)
    }
  }, [codes?.join(',')])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
