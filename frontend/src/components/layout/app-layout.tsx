import { useState } from "react"
import { Outlet, useLocation } from "react-router-dom"
import { Sidebar } from "./sidebar"
import { Header } from "./header"
import { ChatSidebar } from "@/components/chat/chat-sidebar"

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/mitglieder": "Mitglieder",
  "/finanzen": "Finanzen",
  "/admin": "Administration",
}

interface AppLayoutProps {
  onLogout: () => void
}

export function AppLayout({ onLogout }: AppLayoutProps) {
  const location = useLocation()
  const title = pageTitles[location.pathname] || "Sportverein"
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title={title}
          onLogout={onLogout}
          onChatToggle={() => setChatOpen((prev) => !prev)}
        />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <ChatSidebar open={chatOpen} onOpenChange={setChatOpen} />
    </div>
  )
}
