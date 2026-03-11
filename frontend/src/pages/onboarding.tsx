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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, UserPlus, ArrowLeft } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

const beitragskategorien = [
  { value: "erwachsene", label: "Erwachsene" },
  { value: "jugend", label: "Jugend" },
  { value: "familie", label: "Familie" },
  { value: "passiv", label: "Passiv" },
  { value: "ehrenmitglied", label: "Ehrenmitglied" },
]

const abteilungen = [
  "Fussball",
  "Tennis",
  "Handball",
  "Schwimmen",
  "Turnen",
  "Leichtathletik",
  "Volleyball",
  "Basketball",
]

interface FormData {
  vorname: string
  nachname: string
  email: string
  telefon: string
  geburtsdatum: string
  strasse: string
  plz: string
  ort: string
  beitragskategorie: string
  abteilungen: string[]
}

const emptyForm: FormData = {
  vorname: "",
  nachname: "",
  email: "",
  telefon: "",
  geburtsdatum: "",
  strasse: "",
  plz: "",
  ort: "",
  beitragskategorie: "erwachsene",
  abteilungen: [],
}

export function OnboardingPage() {
  const [form, setForm] = useState<FormData>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  function updateField(field: keyof FormData, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function toggleAbteilung(abt: string) {
    setForm((prev) => ({
      ...prev,
      abteilungen: prev.abteilungen.includes(abt)
        ? prev.abteilungen.filter((a) => a !== abt)
        : [...prev.abteilungen, abt],
    }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.vorname.trim() || !form.nachname.trim() || !form.email.trim()) {
      setError("Bitte mindestens Vorname, Nachname und E-Mail ausfüllen.")
      return
    }
    setError("")
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/mitglieder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vorname: form.vorname.trim(),
          nachname: form.nachname.trim(),
          email: form.email.trim(),
          telefon: form.telefon.trim(),
          geburtsdatum: form.geburtsdatum || null,
          strasse: form.strasse.trim(),
          plz: form.plz.trim(),
          ort: form.ort.trim(),
          beitragskategorie: form.beitragskategorie,
          status: "aktiv",
        }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        throw new Error(errData?.detail || "Fehler beim Anlegen des Mitglieds")
      }

      // Assign departments after successful member creation
      if (form.abteilungen.length > 0) {
        const created = await res.json().catch(() => null)
        const memberId = created?.id
        if (memberId) {
          for (const dept of form.abteilungen) {
            try {
              await fetch(
                `${API_BASE}/api/mitglieder/${memberId}/abteilungen/${encodeURIComponent(dept)}`,
                {
                  method: "POST",
                }
              )
            } catch {
              // Department assignment is best-effort
            }
          }
        }
      }

      setSuccess(true)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Fehler beim Anlegen des Mitglieds"
      )
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setForm(emptyForm)
    setSuccess(false)
    setError("")
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-lg text-center">
          <CardContent className="py-12">
            <CheckCircle className="mx-auto mb-4 h-16 w-16 text-green-600" />
            <h2 className="mb-2 text-2xl font-bold">
              Mitglied erfolgreich angelegt!
            </h2>
            <p className="mb-6 text-muted-foreground">
              {form.vorname} {form.nachname} wurde als neues Mitglied
              registriert.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Button size="lg" onClick={handleReset} data-testid="add-another">
                <UserPlus className="mr-2 h-5 w-5" />
                Weiteres Mitglied anlegen
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link to="/">Zur Startseite</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <div className="mb-2 flex items-center justify-center gap-2">
            <Button variant="ghost" size="icon" asChild className="absolute left-4">
              <Link to="/">
                <ArrowLeft className="h-5 w-5" />
              </Link>
            </Button>
            <UserPlus className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Schnell-Onboarding</CardTitle>
          <CardDescription>
            Neues Mitglied am Infostand schnell registrieren.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* h-12 inputs are intentionally oversized for touch/tablet use at the info booth (Infostand) */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Name */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="vorname">Vorname *</Label>
                <Input
                  id="vorname"
                  placeholder="Vorname"
                  value={form.vorname}
                  onChange={(e) => updateField("vorname", e.target.value)}
                  className="h-12 text-lg"
                  data-testid="input-vorname"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nachname">Nachname *</Label>
                <Input
                  id="nachname"
                  placeholder="Nachname"
                  value={form.nachname}
                  onChange={(e) => updateField("nachname", e.target.value)}
                  className="h-12 text-lg"
                  data-testid="input-nachname"
                />
              </div>
            </div>

            {/* Contact */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email">E-Mail *</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="email@beispiel.de"
                  value={form.email}
                  onChange={(e) => updateField("email", e.target.value)}
                  className="h-12 text-lg"
                  data-testid="input-email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="telefon">Telefon</Label>
                <Input
                  id="telefon"
                  type="tel"
                  placeholder="+49 170 1234567"
                  value={form.telefon}
                  onChange={(e) => updateField("telefon", e.target.value)}
                  className="h-12 text-lg"
                  data-testid="input-telefon"
                />
              </div>
            </div>

            {/* Birthday */}
            <div className="space-y-2">
              <Label htmlFor="geburtsdatum">Geburtsdatum</Label>
              <Input
                id="geburtsdatum"
                type="date"
                value={form.geburtsdatum}
                onChange={(e) => updateField("geburtsdatum", e.target.value)}
                className="h-12 text-lg"
                data-testid="input-geburtsdatum"
              />
            </div>

            {/* Address */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="strasse">Straße</Label>
                <Input
                  id="strasse"
                  placeholder="Hauptstraße 1"
                  value={form.strasse}
                  onChange={(e) => updateField("strasse", e.target.value)}
                  className="h-12 text-lg"
                  data-testid="input-strasse"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="plz">PLZ</Label>
                  <Input
                    id="plz"
                    placeholder="10115"
                    value={form.plz}
                    onChange={(e) => updateField("plz", e.target.value)}
                    className="h-12 text-lg"
                    data-testid="input-plz"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ort">Ort</Label>
                  <Input
                    id="ort"
                    placeholder="Berlin"
                    value={form.ort}
                    onChange={(e) => updateField("ort", e.target.value)}
                    className="h-12 text-lg"
                    data-testid="input-ort"
                  />
                </div>
              </div>
            </div>

            {/* Beitragskategorie */}
            <div className="space-y-2">
              <Label>Beitragskategorie</Label>
              <Select
                value={form.beitragskategorie}
                onValueChange={(v) => updateField("beitragskategorie", v)}
              >
                <SelectTrigger className="h-12 text-lg" data-testid="select-kategorie">
                  <SelectValue placeholder="Kategorie wählen" />
                </SelectTrigger>
                <SelectContent>
                  {beitragskategorien.map((k) => (
                    <SelectItem key={k.value} value={k.value}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Abteilungen */}
            <div className="space-y-2">
              <Label>Abteilungen</Label>
              <div className="flex flex-wrap gap-2" data-testid="abteilungen-select">
                {abteilungen.map((abt) => (
                  <Badge
                    key={abt}
                    variant={
                      form.abteilungen.includes(abt) ? "default" : "outline"
                    }
                    className="cursor-pointer px-4 py-2 text-sm"
                    onClick={() => toggleAbteilung(abt)}
                  >
                    {abt}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Error */}
            {error && (
              <p className="text-sm text-destructive" data-testid="error-message">
                {error}
              </p>
            )}

            {/* Submit */}
            <Button
              type="submit"
              className="h-14 w-full text-lg"
              disabled={loading}
              data-testid="submit-button"
            >
              {loading ? "Wird angelegt..." : "Mitglied anlegen"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
