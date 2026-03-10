import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Plus, RotateCw, ShieldOff, Copy, Check } from "lucide-react"

interface ApiToken {
  id: number
  name: string
  created_at: string
  last_used_at: string | null
  is_active: boolean
}

const mockTokens: ApiToken[] = [
  {
    id: 1,
    name: "Backend-Service",
    created_at: "2025-11-01T10:00:00Z",
    last_used_at: "2026-03-09T14:32:00Z",
    is_active: true,
  },
  {
    id: 2,
    name: "CI/CD Pipeline",
    created_at: "2025-09-15T08:00:00Z",
    last_used_at: "2026-03-08T09:15:00Z",
    is_active: true,
  },
  {
    id: 3,
    name: "Alter Testtoken",
    created_at: "2025-06-01T12:00:00Z",
    last_used_at: null,
    is_active: false,
  },
]

function generateMockToken(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789"
  let result = "svk_"
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Nie"
  return new Date(dateStr).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function TokenManagement() {
  const [tokens, setTokens] = useState<ApiToken[]>(mockTokens)
  const [createOpen, setCreateOpen] = useState(false)
  const [newTokenName, setNewTokenName] = useState("")
  const [newTokenExpiry, setNewTokenExpiry] = useState("")
  const [successOpen, setSuccessOpen] = useState(false)
  const [newTokenValue, setNewTokenValue] = useState("")
  const [confirmRotateId, setConfirmRotateId] = useState<number | null>(null)
  const [confirmRevokeId, setConfirmRevokeId] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)

  function handleCreate() {
    const tokenValue = generateMockToken()
    const newToken: ApiToken = {
      id: Date.now(),
      name: newTokenName,
      created_at: new Date().toISOString(),
      last_used_at: null,
      is_active: true,
    }
    setTokens((prev) => [...prev, newToken])
    setNewTokenValue(tokenValue)
    setCreateOpen(false)
    setNewTokenName("")
    setNewTokenExpiry("")
    setSuccessOpen(true)
    setCopied(false)
  }

  function handleRotateConfirm() {
    if (confirmRotateId === null) return
    const tokenValue = generateMockToken()
    setTokens((prev) =>
      prev.map((t) =>
        t.id === confirmRotateId
          ? { ...t, created_at: new Date().toISOString() }
          : t
      )
    )
    setNewTokenValue(tokenValue)
    setConfirmRotateId(null)
    setSuccessOpen(true)
    setCopied(false)
  }

  function handleRevokeConfirm() {
    if (confirmRevokeId === null) return
    setTokens((prev) =>
      prev.map((t) =>
        t.id === confirmRevokeId ? { ...t, is_active: false } : t
      )
    )
    setConfirmRevokeId(null)
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(newTokenValue)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback: select the text
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>API-Token Verwaltung</CardTitle>
            <CardDescription>
              Erstellen und verwalten Sie API-Tokens für den Zugriff auf die
              Schnittstelle.
            </CardDescription>
          </div>
          <Button onClick={() => setCreateOpen(true)} size="sm">
            <Plus className="h-4 w-4" />
            Neuer Token
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Erstellt am</TableHead>
              <TableHead>Zuletzt verwendet</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Aktionen</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tokens.map((token) => (
              <TableRow key={token.id}>
                <TableCell className="font-medium">{token.name}</TableCell>
                <TableCell>{formatDate(token.created_at)}</TableCell>
                <TableCell>{formatDate(token.last_used_at)}</TableCell>
                <TableCell>
                  <Badge
                    variant={token.is_active ? "default" : "secondary"}
                  >
                    {token.is_active ? "aktiv" : "inaktiv"}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmRotateId(token.id)}
                      disabled={!token.is_active}
                    >
                      <RotateCw className="h-3 w-3" />
                      Rotieren
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => setConfirmRevokeId(token.id)}
                      disabled={!token.is_active}
                    >
                      <ShieldOff className="h-3 w-3" />
                      Widerrufen
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Neuen API-Token erstellen</DialogTitle>
            <DialogDescription>
              Geben Sie einen Namen und optional eine Ablaufzeit an.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label htmlFor="token-name" className="text-sm font-medium">
                Name
              </label>
              <Input
                id="token-name"
                placeholder="z.B. Backend-Service"
                value={newTokenName}
                onChange={(e) => setNewTokenName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="token-expiry" className="text-sm font-medium">
                Ablaufzeit in Stunden (optional)
              </label>
              <Input
                id="token-expiry"
                type="number"
                placeholder="z.B. 720"
                value={newTokenExpiry}
                onChange={(e) => setNewTokenExpiry(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreate} disabled={!newTokenName.trim()}>
              Erstellen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Success Dialog - Show Token Value */}
      <Dialog open={successOpen} onOpenChange={setSuccessOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token erstellt</DialogTitle>
            <DialogDescription>
              Kopieren Sie den Token jetzt. Er wird nur einmal angezeigt und
              kann nicht erneut abgerufen werden.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-md bg-muted p-3 font-mono text-sm break-all">
                {newTokenValue}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={handleCopy}
                aria-label="Token kopieren"
              >
                {copied ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-sm text-destructive font-medium">
              Achtung: Dieser Token wird nur einmal angezeigt!
            </p>
          </div>
          <DialogFooter>
            <Button onClick={() => setSuccessOpen(false)}>Schliessen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rotate Confirmation Dialog */}
      <Dialog
        open={confirmRotateId !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmRotateId(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token rotieren</DialogTitle>
            <DialogDescription>
              Der bestehende Token wird ungueltig und durch einen neuen ersetzt.
              Sind Sie sicher?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmRotateId(null)}
            >
              Abbrechen
            </Button>
            <Button onClick={handleRotateConfirm}>Rotieren</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Confirmation Dialog */}
      <Dialog
        open={confirmRevokeId !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmRevokeId(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token widerrufen</DialogTitle>
            <DialogDescription>
              Der Token wird dauerhaft deaktiviert und kann nicht
              wiederhergestellt werden. Sind Sie sicher?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmRevokeId(null)}
            >
              Abbrechen
            </Button>
            <Button variant="destructive" onClick={handleRevokeConfirm}>
              Widerrufen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
