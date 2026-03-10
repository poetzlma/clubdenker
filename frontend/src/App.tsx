import { Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { AppLayout } from "@/components/layout/app-layout"
import { DashboardPage } from "@/pages/dashboard"
import { LoginPage } from "@/pages/login"
import { MitgliederPage } from "@/pages/mitglieder"
import { FinanzenPage } from "@/pages/finanzen"
import { AdminPage } from "@/pages/admin"

function App() {
  const { isAuthenticated, loginWithToken, logout } = useAuth()

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage onLogin={loginWithToken} />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<AppLayout onLogout={logout} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/mitglieder" element={<MitgliederPage />} />
        <Route path="/finanzen" element={<FinanzenPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
