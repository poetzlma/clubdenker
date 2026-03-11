import { Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"
import { AppLayout } from "@/components/layout/app-layout"
import { DashboardPage } from "@/pages/dashboard"
import { LoginPage } from "@/pages/login"
import { MitgliederPage } from "@/pages/mitglieder"
import { FinanzenPage } from "@/pages/finanzen"
import { AdminPage } from "@/pages/admin"
import { VereinsSetupPage } from "@/pages/vereins-setup"
import { TrainingPage } from "@/pages/training"
import { KalenderPage } from "@/pages/kalender"
import { DokumentePage } from "@/pages/dokumente"
import { OnboardingPage } from "@/pages/onboarding"
import { McpSetupPage } from "@/pages/mcp-setup"

function App() {
  const { isAuthenticated, loginWithToken, logout } = useAuth()

  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<LoginPage onLogin={loginWithToken} />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/onboarding" element={<OnboardingPage />} />
      <Route element={<AppLayout onLogout={logout} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/mitglieder" element={<MitgliederPage />} />
        <Route path="/finanzen" element={<FinanzenPage />} />
        <Route path="/training" element={<TrainingPage />} />
        <Route path="/kalender" element={<KalenderPage />} />
        <Route path="/dokumente" element={<DokumentePage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/vereins-setup" element={<VereinsSetupPage />} />
        <Route path="/mcp-setup" element={<McpSetupPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
