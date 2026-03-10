import { useState, useEffect, useCallback, useMemo } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { RECHNUNG_TYP_LABELS, SPHERE_COLORS, STEUERBEFREIUNG_VORLAGEN } from "@/constants/design"
import { Plus, Trash2, FileText } from "lucide-react"
import type { RechnungCreatePayload, EmpfaengerTyp, RechnungTyp, RechnungTemplate } from "@/types/finance"

const API_BASE = "/api"

interface InvoiceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

interface PositionRow {
  beschreibung: string
  menge: number
  einheit: string
  einzelpreis_netto: number
  steuersatz: number
  steuerbefreiungsgrund: string
  kostenstelle_id?: number
}

function emptyPosition(): PositionRow {
  return {
    beschreibung: "",
    menge: 1,
    einheit: "×",
    einzelpreis_netto: 0,
    steuersatz: 0,
    steuerbefreiungsgrund: "",
  }
}

interface MitgliedOption {
  id: number
  name: string
}

const MOCK_MITGLIEDER: MitgliedOption[] = [
  { id: 1, name: "Schmidt, Thomas" },
  { id: 2, name: "Müller, Anna" },
  { id: 3, name: "Weber, Klaus" },
  { id: 4, name: "Fischer, Maria" },
  { id: 5, name: "Becker, Stefan" },
  { id: 6, name: "Hoffmann, Lisa" },
  { id: 7, name: "Klein, Tom" },
  { id: 8, name: "Wagner, Peter" },
  { id: 9, name: "Braun, Sabine" },
  { id: 10, name: "Koch, Michael" },
]

const EINHEIT_OPTIONS = ["×", "h", "Monat", "Stück", "Kurs"]

function formatEuro(amount: number): string {
  return amount.toLocaleString("de-DE", { style: "currency", currency: "EUR" })
}

function getSteuerhinweisForSphaere(sphaere: string): string {
  if (sphaere === "ideell") {
    return STEUERBEFREIUNG_VORLAGEN[0].text
  }
  if (sphaere === "zweckbetrieb") {
    return STEUERBEFREIUNG_VORLAGEN[1].text
  }
  return ""
}

const SPHERE_BADGE_STYLES: Record<string, string> = {
  ideell: "bg-blue-50 text-blue-700 border-blue-200",
  zweckbetrieb: "bg-emerald-50 text-emerald-700 border-emerald-200",
  vermoegensverwaltung: "bg-amber-50 text-amber-700 border-amber-200",
  wirtschaftlich: "bg-purple-50 text-purple-700 border-purple-200",
}

export function InvoiceDialog({ open, onOpenChange, onSuccess }: InvoiceDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Template step
  const [templates, setTemplates] = useState<RechnungTemplate[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [templateStepDone, setTemplateStepDone] = useState(false)

  // Section 1: Typ & Empfänger
  const [rechnungstyp, setRechnungstyp] = useState<RechnungTyp>("mitgliedsbeitrag")
  const [empfaengerTyp, setEmpfaengerTyp] = useState<EmpfaengerTyp>("mitglied")
  const [mitgliedId, setMitgliedId] = useState<number | undefined>(undefined)
  const [empfaengerName, setEmpfaengerName] = useState("")
  const [empfaengerStrasse, setEmpfaengerStrasse] = useState("")
  const [empfaengerPlz, setEmpfaengerPlz] = useState("")
  const [empfaengerOrt, setEmpfaengerOrt] = useState("")

  // Section 2: Sphäre & Steuer
  const [sphaere, setSphaere] = useState("")
  const [steuerhinweisText, setSteuerhinweisText] = useState("")

  // Section 3: Leistungszeitraum
  const [leistungsModus, setLeistungsModus] = useState<"einmalig" | "zeitraum">("einmalig")
  const [leistungsdatum, setLeistungsdatum] = useState("")
  const [leistungszeitraumVon, setLeistungszeitraumVon] = useState("")
  const [leistungszeitraumBis, setLeistungszeitraumBis] = useState("")
  const [leistungEqualsRechnungsdatum, setLeistungEqualsRechnungsdatum] = useState(false)

  // Section 4: Positionen
  const [positionen, setPositionen] = useState<PositionRow[]>([emptyPosition()])

  // Section 5: Zahlung
  const [zahlungszielTage, setZahlungszielTage] = useState(14)

  // Mitglieder list
  const [mitglieder, setMitglieder] = useState<MitgliedOption[]>([])
  const [mitgliedSearch, setMitgliedSearch] = useState("")

  const fetchMitglieder = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mitglieder`)
      if (!res.ok) throw new Error("API error")
      const data = await res.json()
      const items = data.items ?? data
      setMitglieder(
        items.map((m: { id: number; vorname?: string; nachname?: string; name?: string }) => ({
          id: m.id,
          name: m.nachname && m.vorname ? `${m.nachname}, ${m.vorname}` : m.name ?? `Mitglied #${m.id}`,
        }))
      )
    } catch {
      setMitglieder(MOCK_MITGLIEDER)
    }
  }, [])

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen/vorlagen`)
      if (!res.ok) throw new Error("API error")
      const data: RechnungTemplate[] = await res.json()
      setTemplates(data)
    } catch {
      // No templates available — skip template step, go straight to form
      setTemplates([])
      setTemplateStepDone(true)
    }
  }, [])

  useEffect(() => {
    if (open) {
      fetchMitglieder()
      fetchTemplates()
    }
  }, [open, fetchMitglieder, fetchTemplates])

  // Auto-fill steuerhinweis when sphäre changes
  useEffect(() => {
    const hint = getSteuerhinweisForSphaere(sphaere)
    if (hint) {
      setSteuerhinweisText(hint)
    }
  }, [sphaere])

  // Auto-fill leistungsdatum when checkbox is set
  useEffect(() => {
    if (leistungEqualsRechnungsdatum) {
      const today = new Date().toISOString().split("T")[0]
      if (leistungsModus === "einmalig") {
        setLeistungsdatum(today)
      }
    }
  }, [leistungEqualsRechnungsdatum, leistungsModus])

  const filteredMitglieder = useMemo(() => {
    if (!mitgliedSearch) return mitglieder
    const term = mitgliedSearch.toLowerCase()
    return mitglieder.filter((m) => m.name.toLowerCase().includes(term))
  }, [mitglieder, mitgliedSearch])

  // Computed totals per position
  function positionTotals(pos: PositionRow) {
    const netto = pos.menge * pos.einzelpreis_netto
    const steuer = netto * (pos.steuersatz / 100)
    const brutto = netto + steuer
    return { netto, steuer, brutto }
  }

  const summeNetto = positionen.reduce((sum, p) => sum + positionTotals(p).netto, 0)
  const summeSteuer = positionen.reduce((sum, p) => sum + positionTotals(p).steuer, 0)
  const summeBrutto = positionen.reduce((sum, p) => sum + positionTotals(p).brutto, 0)

  // Fälligkeitsdatum
  const faelligkeitsdatum = useMemo(() => {
    const d = new Date()
    d.setDate(d.getDate() + zahlungszielTage)
    return d.toISOString().split("T")[0]
  }, [zahlungszielTage])

  function updatePosition(index: number, updates: Partial<PositionRow>) {
    setPositionen((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...updates } : p))
    )
  }

  function removePosition(index: number) {
    setPositionen((prev) => prev.filter((_, i) => i !== index))
  }

  function addPosition() {
    setPositionen((prev) => [...prev, emptyPosition()])
  }

  function applyTemplate(template: RechnungTemplate) {
    setRechnungstyp(template.rechnungstyp)
    if (template.sphaere) {
      setSphaere(template.sphaere)
    }
    if (template.empfaenger_typ) {
      setEmpfaengerTyp(template.empfaenger_typ)
    }
    if (template.steuerhinweis_text) {
      setSteuerhinweisText(template.steuerhinweis_text)
    } else {
      setSteuerhinweisText("")
    }
    setZahlungszielTage(template.zahlungsziel_tage)

    if (template.positionen.length > 0) {
      setPositionen(
        template.positionen.map((p) => ({
          beschreibung: p.beschreibung,
          menge: p.menge,
          einheit: p.einheit,
          einzelpreis_netto: p.einzelpreis_netto ?? 0,
          steuersatz: p.steuersatz,
          steuerbefreiungsgrund: p.steuerbefreiungsgrund ?? "",
        }))
      )
    } else {
      setPositionen([emptyPosition()])
    }
  }

  function handleTemplateSelect(templateId: string | null) {
    setSelectedTemplateId(templateId)
    if (templateId) {
      const template = templates.find((t) => t.id === templateId)
      if (template) {
        applyTemplate(template)
      }
    }
    setTemplateStepDone(true)
  }

  function resetForm() {
    setRechnungstyp("mitgliedsbeitrag")
    setEmpfaengerTyp("mitglied")
    setMitgliedId(undefined)
    setEmpfaengerName("")
    setEmpfaengerStrasse("")
    setEmpfaengerPlz("")
    setEmpfaengerOrt("")
    setSphaere("")
    setSteuerhinweisText("")
    setLeistungsModus("einmalig")
    setLeistungsdatum("")
    setLeistungszeitraumVon("")
    setLeistungszeitraumBis("")
    setLeistungEqualsRechnungsdatum(false)
    setPositionen([emptyPosition()])
    setZahlungszielTage(14)
    setMitgliedSearch("")
    setError(null)
    setSelectedTemplateId(null)
    setTemplateStepDone(false)
  }

  async function handleSubmit() {
    // Validation
    if (empfaengerTyp === "mitglied" && !mitgliedId) {
      setError("Bitte ein Mitglied auswählen.")
      return
    }
    if (empfaengerTyp !== "mitglied" && !empfaengerName.trim()) {
      setError("Bitte einen Empfängernamen eingeben.")
      return
    }
    if (positionen.length === 0) {
      setError("Bitte mindestens eine Position hinzufügen.")
      return
    }
    const filledPositionen = positionen.filter((p) => p.beschreibung.trim())
    if (filledPositionen.length === 0) {
      setError("Bitte eine Beschreibung für mindestens eine Position eingeben.")
      return
    }
    if (filledPositionen.some((p) => p.einzelpreis_netto <= 0)) {
      setError("Bitte einen Netto-Preis für alle Positionen eingeben.")
      return
    }

    const payload: RechnungCreatePayload = {
      rechnungstyp,
      empfaenger_typ: empfaengerTyp,
      mitglied_id: empfaengerTyp === "mitglied" ? mitgliedId : undefined,
      empfaenger_name: empfaengerTyp !== "mitglied" ? empfaengerName : undefined,
      empfaenger_strasse: empfaengerTyp !== "mitglied" ? empfaengerStrasse : undefined,
      empfaenger_plz: empfaengerTyp !== "mitglied" ? empfaengerPlz : undefined,
      empfaenger_ort: empfaengerTyp !== "mitglied" ? empfaengerOrt : undefined,
      sphaere: sphaere || undefined,
      leistungsdatum: leistungsModus === "einmalig" ? leistungsdatum || undefined : undefined,
      leistungszeitraum_von: leistungsModus === "zeitraum" ? leistungszeitraumVon || undefined : undefined,
      leistungszeitraum_bis: leistungsModus === "zeitraum" ? leistungszeitraumBis || undefined : undefined,
      zahlungsziel_tage: zahlungszielTage,
      steuerhinweis_text: steuerhinweisText || undefined,
      positionen: filledPositionen
        .map((p) => ({
          beschreibung: p.beschreibung,
          menge: p.menge,
          einheit: p.einheit,
          einzelpreis_netto: p.einzelpreis_netto,
          steuersatz: p.steuersatz,
          steuerbefreiungsgrund: p.steuersatz === 0 ? p.steuerbefreiungsgrund || undefined : undefined,
          kostenstelle_id: p.kostenstelle_id,
        })),
    }

    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/finanzen/rechnungen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error("Rechnung konnte nicht erstellt werden.")
      resetForm()
      onOpenChange(false)
      onSuccess?.()
    } catch {
      setError("Fehler beim Erstellen der Rechnung. Bitte erneut versuchen.")
    } finally {
      setSubmitting(false)
    }
  }

  // Template step view
  function renderTemplateStep() {
    return (
      <div className="space-y-4 pb-4">
        <h3 className="text-sm font-semibold text-foreground">Vorlage auswählen</h3>
        <p className="text-sm text-muted-foreground">
          Wählen Sie eine Vorlage, um die Rechnung vorzubefüllen, oder erstellen Sie eine leere Rechnung.
        </p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {/* Empty invoice card */}
          <button
            type="button"
            className={cn(
              "rounded-lg border-2 border-dashed p-4 text-left transition-all hover:border-primary/50 hover:bg-muted/30",
              selectedTemplateId === null && templateStepDone
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25"
            )}
            onClick={() => handleTemplateSelect(null)}
          >
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="font-semibold text-sm">Leere Rechnung</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Manuelle Erstellung ohne Vorlage
            </p>
          </button>

          {/* Template cards */}
          {templates.map((template) => {
            const sphereStyle = template.sphaere
              ? SPHERE_BADGE_STYLES[template.sphaere]
              : undefined
            const sphereLabel = template.sphaere
              ? (SPHERE_COLORS as Record<string, { label: string }>)[template.sphaere]?.label
              : undefined

            return (
              <button
                key={template.id}
                type="button"
                className={cn(
                  "rounded-lg border-2 p-4 text-left transition-all hover:border-primary/50 hover:bg-muted/30",
                  selectedTemplateId === template.id
                    ? "border-primary bg-primary/5"
                    : "border-muted"
                )}
                onClick={() => handleTemplateSelect(template.id)}
              >
                <div className="mb-2">
                  <span className="font-semibold text-sm">{template.name}</span>
                </div>
                <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                  {template.beschreibung}
                </p>
                {sphereLabel && (
                  <Badge
                    variant="outline"
                    className={cn("text-[10px] px-1.5 py-0", sphereStyle)}
                  >
                    {sphereLabel}
                  </Badge>
                )}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v)
        if (!v) resetForm()
      }}
    >
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Neue Rechnung erstellen</DialogTitle>
          <DialogDescription>
            {!templateStepDone
              ? "Wählen Sie eine Vorlage oder erstellen Sie eine leere Rechnung."
              : "Erstellen Sie eine rechtskonforme Rechnung mit Positionen."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-y-auto -mx-6 px-6">
          {!templateStepDone ? (
            renderTemplateStep()
          ) : (
            <div className="space-y-6 pb-4">
              {/* Template info banner */}
              {selectedTemplateId && (
                <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
                  <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm text-muted-foreground">
                    Vorlage: <span className="font-medium text-foreground">{templates.find((t) => t.id === selectedTemplateId)?.name}</span>
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto h-7 text-xs"
                    onClick={() => {
                      resetForm()
                    }}
                  >
                    Vorlage wechseln
                  </Button>
                </div>
              )}

              {/* Section 1: Rechnungstyp & Empfänger */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Rechnungstyp &amp; Empfänger</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rechnungstyp">Rechnungstyp</Label>
                    <Select value={rechnungstyp} onValueChange={(v) => setRechnungstyp(v as RechnungTyp)}>
                      <SelectTrigger id="rechnungstyp">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(RECHNUNG_TYP_LABELS).map(([key, label]) => (
                          <SelectItem key={key} value={key}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Empfänger Typ</Label>
                    <Select value={empfaengerTyp} onValueChange={(v) => setEmpfaengerTyp(v as EmpfaengerTyp)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="mitglied">Mitglied</SelectItem>
                        <SelectItem value="sponsor">Sponsor</SelectItem>
                        <SelectItem value="extern">Extern</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {empfaengerTyp === "mitglied" ? (
                  <div className="space-y-2">
                    <Label>Mitglied auswählen</Label>
                    <Input
                      placeholder="Mitglied suchen..."
                      value={mitgliedSearch}
                      onChange={(e) => setMitgliedSearch(e.target.value)}
                      className="mb-2"
                    />
                    <Select
                      value={mitgliedId?.toString() ?? ""}
                      onValueChange={(v) => setMitgliedId(parseInt(v))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Mitglied wählen..." />
                      </SelectTrigger>
                      <SelectContent>
                        {filteredMitglieder.map((m) => (
                          <SelectItem key={m.id} value={m.id.toString()}>
                            {m.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="empfaenger_name">
                        {empfaengerTyp === "sponsor" ? "Firma / Sponsor" : "Name"} *
                      </Label>
                      <Input
                        id="empfaenger_name"
                        value={empfaengerName}
                        onChange={(e) => setEmpfaengerName(e.target.value)}
                        placeholder="Name des Empfängers"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="empfaenger_strasse">Straße</Label>
                      <Input
                        id="empfaenger_strasse"
                        value={empfaengerStrasse}
                        onChange={(e) => setEmpfaengerStrasse(e.target.value)}
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="space-y-2">
                        <Label htmlFor="empfaenger_plz">PLZ</Label>
                        <Input
                          id="empfaenger_plz"
                          value={empfaengerPlz}
                          onChange={(e) => setEmpfaengerPlz(e.target.value)}
                        />
                      </div>
                      <div className="col-span-2 space-y-2">
                        <Label htmlFor="empfaenger_ort">Ort</Label>
                        <Input
                          id="empfaenger_ort"
                          value={empfaengerOrt}
                          onChange={(e) => setEmpfaengerOrt(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <Separator />

              {/* Section 2: Sphäre & Steuer */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Sphäre &amp; Steuer</h3>

                <div className="space-y-2">
                  <Label>Sphäre</Label>
                  <div className="grid grid-cols-4 gap-2">
                    {(Object.entries(SPHERE_COLORS) as [string, { bg: string; text: string; label: string }][]).map(
                      ([key, config]) => (
                        <button
                          key={key}
                          type="button"
                          className={cn(
                            "rounded-lg border p-2 text-center text-xs font-medium transition-all",
                            sphaere === key
                              ? `${config.bg} ${config.text} border-current ring-1 ring-current`
                              : "border-gray-200 text-gray-500 hover:border-gray-300"
                          )}
                          onClick={() => setSphaere(key)}
                        >
                          {config.label}
                        </button>
                      )
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="steuerhinweis">Steuerbefreiungshinweis</Label>
                  <div className="flex flex-wrap gap-1 mb-1">
                    {STEUERBEFREIUNG_VORLAGEN.map((v) => (
                      <button
                        key={v.label}
                        type="button"
                        className="rounded border border-gray-200 px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-50"
                        onClick={() => setSteuerhinweisText(v.text)}
                      >
                        {v.label}
                      </button>
                    ))}
                  </div>
                  <Textarea
                    id="steuerhinweis"
                    value={steuerhinweisText}
                    onChange={(e) => setSteuerhinweisText(e.target.value)}
                    placeholder="Steuerbefreiungsgrund eingeben oder Vorlage wählen..."
                    rows={2}
                  />
                </div>
              </div>

              <Separator />

              {/* Section 3: Leistungszeitraum */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Leistungszeitraum</h3>

                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="leistungsmodus"
                      checked={leistungsModus === "einmalig"}
                      onChange={() => setLeistungsModus("einmalig")}
                      className="accent-blue-600"
                    />
                    Einmaliges Datum
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name="leistungsmodus"
                      checked={leistungsModus === "zeitraum"}
                      onChange={() => setLeistungsModus("zeitraum")}
                      className="accent-blue-600"
                    />
                    Zeitraum
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer ml-auto">
                    <input
                      type="checkbox"
                      checked={leistungEqualsRechnungsdatum}
                      onChange={(e) => setLeistungEqualsRechnungsdatum(e.target.checked)}
                      className="accent-blue-600"
                    />
                    = Rechnungsdatum
                  </label>
                </div>

                {leistungsModus === "einmalig" ? (
                  <div className="space-y-2">
                    <Label htmlFor="leistungsdatum">Leistungsdatum</Label>
                    <Input
                      id="leistungsdatum"
                      type="date"
                      value={leistungsdatum}
                      onChange={(e) => setLeistungsdatum(e.target.value)}
                      disabled={leistungEqualsRechnungsdatum}
                    />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="leistungszeitraum_von">Von</Label>
                      <Input
                        id="leistungszeitraum_von"
                        type="date"
                        value={leistungszeitraumVon}
                        onChange={(e) => setLeistungszeitraumVon(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="leistungszeitraum_bis">Bis</Label>
                      <Input
                        id="leistungszeitraum_bis"
                        type="date"
                        value={leistungszeitraumBis}
                        onChange={(e) => setLeistungszeitraumBis(e.target.value)}
                      />
                    </div>
                  </div>
                )}
              </div>

              <Separator />

              {/* Section 4: Positionen */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Positionen</h3>

                <div className="space-y-3">
                  {positionen.map((pos, idx) => {
                    const totals = positionTotals(pos)
                    return (
                      <div key={idx} className="rounded-lg border p-3 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-muted-foreground">
                            Position {idx + 1}
                          </span>
                          {positionen.length > 1 && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => removePosition(idx)}
                            >
                              <Trash2 className="h-3.5 w-3.5 text-red-500" />
                            </Button>
                          )}
                        </div>

                        <div className="space-y-2">
                          <Label>Beschreibung</Label>
                          <Input
                            value={pos.beschreibung}
                            onChange={(e) => updatePosition(idx, { beschreibung: e.target.value })}
                            placeholder="z.B. Jahresbeitrag 2026"
                          />
                        </div>

                        <div className="grid grid-cols-5 gap-2">
                          <div className="space-y-1">
                            <Label className="text-xs">Menge</Label>
                            <Input
                              type="number"
                              min="0"
                              step="0.01"
                              value={pos.menge || ""}
                              onChange={(e) => updatePosition(idx, { menge: parseFloat(e.target.value) || 0 })}
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">Einheit</Label>
                            <Select
                              value={pos.einheit}
                              onValueChange={(v) => updatePosition(idx, { einheit: v })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {EINHEIT_OPTIONS.map((e) => (
                                  <SelectItem key={e} value={e}>
                                    {e}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">Netto-Preis</Label>
                            <Input
                              type="number"
                              min="0"
                              step="0.01"
                              value={pos.einzelpreis_netto || ""}
                              onChange={(e) =>
                                updatePosition(idx, { einzelpreis_netto: parseFloat(e.target.value) || 0 })
                              }
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">USt %</Label>
                            <Select
                              value={pos.steuersatz.toString()}
                              onValueChange={(v) => updatePosition(idx, { steuersatz: parseInt(v) })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="0">0%</SelectItem>
                                <SelectItem value="7">7%</SelectItem>
                                <SelectItem value="19">19%</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs">Brutto</Label>
                            <div className="flex h-9 items-center rounded-md border bg-muted/50 px-3 text-sm font-medium tabular-nums">
                              {formatEuro(totals.brutto)}
                            </div>
                          </div>
                        </div>

                        {pos.steuersatz === 0 && (
                          <div className="space-y-1">
                            <Label className="text-xs">Befreiungsgrund</Label>
                            <Input
                              value={pos.steuerbefreiungsgrund}
                              onChange={(e) =>
                                updatePosition(idx, { steuerbefreiungsgrund: e.target.value })
                              }
                              placeholder="z.B. §4 Nr. 22b UStG"
                            />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                <Button variant="outline" size="sm" onClick={addPosition} className="w-full">
                  <Plus className="h-4 w-4 mr-1" />
                  Position hinzufügen
                </Button>

                {/* Summen */}
                <div className="rounded-lg border bg-muted/30 p-3 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Summe Netto</span>
                    <span className="font-medium tabular-nums">{formatEuro(summeNetto)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">USt</span>
                    <span className="font-medium tabular-nums">{formatEuro(summeSteuer)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between text-sm font-semibold">
                    <span>Summe Brutto</span>
                    <span className="tabular-nums">{formatEuro(summeBrutto)}</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Section 5: Zahlung */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground">Zahlung</h3>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="zahlungsziel">Zahlungsziel (Tage)</Label>
                    <Input
                      id="zahlungsziel"
                      type="number"
                      min="0"
                      value={zahlungszielTage}
                      onChange={(e) => setZahlungszielTage(parseInt(e.target.value) || 0)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Fälligkeitsdatum</Label>
                    <div className="flex h-9 items-center rounded-md border bg-muted/50 px-3 text-sm">
                      {faelligkeitsdatum
                        ? new Date(faelligkeitsdatum).toLocaleDateString("de-DE")
                        : "---"}
                    </div>
                  </div>
                </div>
              </div>

              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          )}
        </div>

        <DialogFooter className="pt-4 border-t flex-shrink-0">
          {!templateStepDone ? (
            <Button
              variant="outline"
              onClick={() => {
                onOpenChange(false)
                resetForm()
              }}
            >
              Abbrechen
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => {
                  if (selectedTemplateId !== null || templateStepDone) {
                    resetForm()
                  } else {
                    onOpenChange(false)
                    resetForm()
                  }
                }}
              >
                {templateStepDone ? "Zurück zur Vorlagenauswahl" : "Abbrechen"}
              </Button>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Wird erstellt..." : "Rechnung erstellen"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
