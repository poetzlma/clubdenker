import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { setToken } from "@/lib/api"

interface LoginPageProps {
  onLogin: (token: string) => void
}

interface LoginResponse {
  access_token: string
  token_type: string
  admin: { id: number; email: string; name: string }
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [token, setTokenValue] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleEmailLogin(e: FormEvent) {
    e.preventDefault()
    if (!email.trim() || !password.trim()) {
      setError("Bitte E-Mail und Passwort eingeben")
      return
    }
    setError("")
    setLoading(true)
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password: password.trim() }),
        }
      )
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || "Anmeldung fehlgeschlagen")
      }
      const data: LoginResponse = await response.json()
      setToken(data.access_token)
      onLogin(data.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anmeldung fehlgeschlagen")
    } finally {
      setLoading(false)
    }
  }

  function handleTokenLogin(e: FormEvent) {
    e.preventDefault()
    if (!token.trim()) {
      setError("Bitte Token eingeben")
      return
    }
    setError("")
    onLogin(token.trim())
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Klubdenker</CardTitle>
          <CardDescription>
            Bitte melden Sie sich an, um fortzufahren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Anmeldung</TabsTrigger>
              <TabsTrigger value="token">API Token</TabsTrigger>
            </TabsList>
            <TabsContent value="login">
              <form onSubmit={handleEmailLogin} className="space-y-4 pt-2">
                <div className="space-y-2">
                  <Label htmlFor="email">E-Mail</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="admin@klubdenker.de"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Passwort</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Passwort eingeben..."
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? "Anmeldung..." : "Anmelden"}
                </Button>
              </form>
            </TabsContent>
            <TabsContent value="token">
              <form onSubmit={handleTokenLogin} className="space-y-4 pt-2">
                <div className="space-y-2">
                  <Label htmlFor="token">API Token</Label>
                  <Input
                    id="token"
                    type="password"
                    placeholder="Token eingeben..."
                    value={token}
                    onChange={(e) => setTokenValue(e.target.value)}
                  />
                </div>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
                <Button type="submit" className="w-full">
                  Anmelden
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      <div className="mt-4 text-center">
        <Button variant="link" asChild>
          <Link to="/onboarding">Schnell-Onboarding (Infostand)</Link>
        </Button>
      </div>
    </div>
  )
}
