import { useState, useEffect, useCallback } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { Vereinsstammdaten } from "@/types/finance"

const API_BASE = "/api"

const MOCK_STAMMDATEN: Vereinsstammdaten = {
  id: 1,
  name: "TSV Musterstadt 1899 e.V.",
  strasse: "Sportstraße 12",
  plz: "12345",
  ort: "Musterstadt",
  steuernummer: "123/456/78901",
  ust_id: "",
  iban: "DE89370400440532013000",
  bic: "COBADEFFXXX",
  registergericht: "Amtsgericht Musterstadt",
  registernummer: "VR 1234",
}

export function VereinsstammdatenForm() {
  const [data, setData] = useState<Vereinsstammdaten>(MOCK_STAMMDATEN)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/finanzen/vereinsstammdaten`)
      if (!res.ok) throw new Error("API error")
      const json = await res.json()
      setData(json)
    } catch {
      setData(MOCK_STAMMDATEN)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const res = await fetch(`${API_BASE}/finanzen/vereinsstammdaten`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error("Speichern fehlgeschlagen")
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError("Fehler beim Speichern. Bitte erneut versuchen.")
    } finally {
      setSaving(false)
    }
  }

  function update(field: keyof Vereinsstammdaten, value: string) {
    setData((prev) => ({ ...prev, [field]: value }))
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="flex h-32 items-center justify-center">
          <p className="text-sm text-muted-foreground">Laden...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vereinsstammdaten</CardTitle>
        <CardDescription>
          Stammdaten des Vereins, die auf Rechnungen und offiziellen Dokumenten erscheinen.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Vereinsname */}
          <div className="space-y-2">
            <Label htmlFor="verein-name">Vereinsname *</Label>
            <Input
              id="verein-name"
              value={data.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="z.B. TSV Musterstadt 1899 e.V."
            />
          </div>

          {/* Adresse */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Adresse</h4>
            <div className="space-y-2">
              <Label htmlFor="verein-strasse">Straße *</Label>
              <Input
                id="verein-strasse"
                value={data.strasse}
                onChange={(e) => update("strasse", e.target.value)}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="verein-plz">PLZ *</Label>
                <Input
                  id="verein-plz"
                  value={data.plz}
                  onChange={(e) => update("plz", e.target.value)}
                />
              </div>
              <div className="col-span-2 space-y-2">
                <Label htmlFor="verein-ort">Ort *</Label>
                <Input
                  id="verein-ort"
                  value={data.ort}
                  onChange={(e) => update("ort", e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Steuerliche Daten */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Steuerliche Daten</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="verein-steuernummer">Steuernummer</Label>
                <Input
                  id="verein-steuernummer"
                  value={data.steuernummer ?? ""}
                  onChange={(e) => update("steuernummer", e.target.value)}
                  placeholder="123/456/78901"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="verein-ust-id">USt-IdNr.</Label>
                <Input
                  id="verein-ust-id"
                  value={data.ust_id ?? ""}
                  onChange={(e) => update("ust_id", e.target.value)}
                  placeholder="DE123456789"
                />
              </div>
            </div>
          </div>

          {/* Bankverbindung */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Bankverbindung</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="verein-iban">IBAN *</Label>
                <Input
                  id="verein-iban"
                  value={data.iban}
                  onChange={(e) => update("iban", e.target.value)}
                  placeholder="DE89 3704 0044 0532 0130 00"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="verein-bic">BIC</Label>
                <Input
                  id="verein-bic"
                  value={data.bic ?? ""}
                  onChange={(e) => update("bic", e.target.value)}
                  placeholder="COBADEFFXXX"
                />
              </div>
            </div>
          </div>

          {/* Registerinformationen */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Registerinformationen</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="verein-registergericht">Registergericht</Label>
                <Input
                  id="verein-registergericht"
                  value={data.registergericht ?? ""}
                  onChange={(e) => update("registergericht", e.target.value)}
                  placeholder="Amtsgericht Musterstadt"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="verein-registernummer">Registernummer</Label>
                <Input
                  id="verein-registernummer"
                  value={data.registernummer ?? ""}
                  onChange={(e) => update("registernummer", e.target.value)}
                  placeholder="VR 1234"
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <Button onClick={handleSave} disabled={saving || !data.name.trim()}>
              {saving ? "Wird gespeichert..." : "Stammdaten speichern"}
            </Button>
            {saved && (
              <span className="text-sm text-emerald-600 font-medium">
                Gespeichert
              </span>
            )}
            {error && (
              <span className="text-sm text-red-600">{error}</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
