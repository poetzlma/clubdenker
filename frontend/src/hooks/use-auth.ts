import { useState, useCallback } from "react"
import { api, setToken, clearToken, getToken } from "@/lib/api"

interface LoginResponse {
  access_token: string
  token_type: string
}

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(
    () => !!getToken()
  )

  const login = useCallback(async (username: string, password: string) => {
    const formBody = new URLSearchParams()
    formBody.append("username", username)
    formBody.append("password", password)

    const response = await api.post<LoginResponse>("/auth/login", {
      username,
      password,
    })

    setToken(response.access_token)
    setIsAuthenticated(true)
  }, [])

  const loginWithToken = useCallback((token: string) => {
    setToken(token)
    setIsAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    setIsAuthenticated(false)
  }, [])

  return {
    isAuthenticated,
    login,
    loginWithToken,
    logout,
  }
}
