import { useState, useEffect, useCallback, useRef } from "react"
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
  const currentPath = useRef(path)
  currentPath.current = path

  const fetchData = useCallback(async () => {
    const activePath = currentPath.current
    if (!activePath) return

    setState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await api.get<T>(activePath)
      setState({ data, loading: false, error: null })
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err instanceof Error ? err.message : "An error occurred",
      })
    }
  }, [])

  useEffect(() => {
    fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path])

  return { ...state, refetch: fetchData }
}
