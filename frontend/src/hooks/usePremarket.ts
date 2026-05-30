import { useState, useEffect } from 'react'
import { getPremarket } from '../api/client'
import type { PremarketResponse } from '../types'

export function usePremarket() {
  const [data, setData] = useState<PremarketResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getPremarket()
      .then(setData)
      .catch(e => setError(e?.response?.data?.detail ?? e?.message ?? '请求失败'))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}
