import { useState, useEffect, useCallback } from "react"
import api from "@/lib/api"

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T>(path: string | null) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: !!path,
    error: null,
  })

  const fetchData = useCallback(async () => {
    if (!path) return

    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await api.get<T>(path)
      setState({ data, loading: false, error: null })
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : "An error occurred",
      })
    }
  }, [path])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { ...state, refetch: fetchData }
}
