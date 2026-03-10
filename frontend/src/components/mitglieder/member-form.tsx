import { useState, useEffect, type FormEvent } from "react"
import type { Member } from "@/types/member"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface MemberFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  member?: Member | null
  onSubmit: (data: MemberFormData) => Promise<void>
}

export interface MemberFormData {
  vorname: string
  nachname: string
  email: string
  telefon: string
  geburtsdatum: string
  strasse: string
  plz: string
  ort: string
  beitragskategorie: Member["beitragskategorie"]
  notizen: string
  abteilungen: string[]
}

const defaultDepartments = [
  "Fussball",
  "Tennis",
  "Schwimmen",
  "Leichtathletik",
  "Fitness",
  "Handball",
]

const beitragOptions: { value: Member["beitragskategorie"]; label: string }[] = [
  { value: "erwachsene", label: "Erwachsene" },
  { value: "jugend", label: "Jugend" },
  { value: "familie", label: "Familie" },
  { value: "passiv", label: "Passiv" },
  { value: "ehrenmitglied", label: "Ehrenmitglied" },
]

const inputClassName =
  "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"

export function MemberForm({ open, onOpenChange, member, onSubmit }: MemberFormProps) {
  const isEdit = !!member

  const [formData, setFormData] = useState<MemberFormData>(() => ({
    vorname: member?.vorname ?? "",
    nachname: member?.nachname ?? "",
    email: member?.email ?? "",
    telefon: member?.telefon ?? "",
    geburtsdatum: member?.geburtsdatum ?? "",
    strasse: member?.strasse ?? "",
    plz: member?.plz ?? "",
    ort: member?.ort ?? "",
    beitragskategorie: member?.beitragskategorie ?? "erwachsene",
    notizen: member?.notizen ?? "",
    abteilungen: [],
  }))

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [departments, setDepartments] = useState<string[]>(defaultDepartments)

  useEffect(() => {
    let cancelled = false
    async function fetchDepartments() {
      try {
        const res = await fetch("/api/mitglieder/abteilungen")
        if (!res.ok) throw new Error("fetch failed")
        const data = await res.json()
        if (!cancelled && Array.isArray(data)) {
          setDepartments(data.map((d: { name: string }) => d.name ?? d))
        }
      } catch {
        // Use default departments as fallback
      }
    }
    fetchDepartments()
    return () => { cancelled = true }
  }, [])

  function validate(): boolean {
    const newErrors: Record<string, string> = {}
    if (!formData.vorname.trim()) newErrors.vorname = "Vorname ist erforderlich"
    if (!formData.nachname.trim()) newErrors.nachname = "Nachname ist erforderlich"
    if (!formData.email.trim()) newErrors.email = "E-Mail ist erforderlich"
    if (!formData.geburtsdatum) newErrors.geburtsdatum = "Geburtsdatum ist erforderlich"
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      await onSubmit(formData)
      onOpenChange(false)
    } catch {
      // error handling could be added here
    } finally {
      setLoading(false)
    }
  }

  function updateField(field: keyof MemberFormData, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[field]
        return next
      })
    }
  }

  function toggleDepartment(dept: string) {
    setFormData((prev) => ({
      ...prev,
      abteilungen: prev.abteilungen.includes(dept)
        ? prev.abteilungen.filter((d) => d !== dept)
        : [...prev.abteilungen, dept],
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Mitglied bearbeiten" : "Neues Mitglied"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Bearbeiten Sie die Mitgliedsdaten."
              : "Geben Sie die Daten des neuen Mitglieds ein."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Vorname */}
            <div className="space-y-1">
              <label className="text-sm font-medium">
                Vorname <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.vorname}
                onChange={(e) => updateField("vorname", e.target.value)}
                className={cn(inputClassName, errors.vorname && "border-red-500")}
                placeholder="Vorname"
              />
              {errors.vorname && (
                <p className="text-xs text-red-500">{errors.vorname}</p>
              )}
            </div>

            {/* Nachname */}
            <div className="space-y-1">
              <label className="text-sm font-medium">
                Nachname <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.nachname}
                onChange={(e) => updateField("nachname", e.target.value)}
                className={cn(inputClassName, errors.nachname && "border-red-500")}
                placeholder="Nachname"
              />
              {errors.nachname && (
                <p className="text-xs text-red-500">{errors.nachname}</p>
              )}
            </div>

            {/* Email */}
            <div className="space-y-1">
              <label className="text-sm font-medium">
                E-Mail <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => updateField("email", e.target.value)}
                className={cn(inputClassName, errors.email && "border-red-500")}
                placeholder="email@beispiel.de"
              />
              {errors.email && (
                <p className="text-xs text-red-500">{errors.email}</p>
              )}
            </div>

            {/* Telefon */}
            <div className="space-y-1">
              <label className="text-sm font-medium">Telefon</label>
              <input
                type="tel"
                value={formData.telefon}
                onChange={(e) => updateField("telefon", e.target.value)}
                className={inputClassName}
                placeholder="+49 ..."
              />
            </div>

            {/* Geburtsdatum */}
            <div className="space-y-1">
              <label className="text-sm font-medium">
                Geburtsdatum <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                value={formData.geburtsdatum}
                onChange={(e) => updateField("geburtsdatum", e.target.value)}
                className={cn(inputClassName, errors.geburtsdatum && "border-red-500")}
              />
              {errors.geburtsdatum && (
                <p className="text-xs text-red-500">{errors.geburtsdatum}</p>
              )}
            </div>

            {/* Beitragskategorie */}
            <div className="space-y-1">
              <label className="text-sm font-medium">Beitragskategorie</label>
              <Select
                value={formData.beitragskategorie}
                onValueChange={(val) =>
                  updateField("beitragskategorie", val)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Kategorie wählen" />
                </SelectTrigger>
                <SelectContent>
                  {beitragOptions.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Abteilungen — only for new members */}
            {!isEdit && (
              <div className="col-span-2 space-y-1">
                <label className="text-sm font-medium">Abteilungen</label>
                <div className="flex flex-wrap gap-2">
                  {departments.map((dept) => {
                    const selected = formData.abteilungen.includes(dept)
                    return (
                      <button
                        key={dept}
                        type="button"
                        onClick={() => toggleDepartment(dept)}
                        className={cn(
                          "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium transition-colors",
                          selected
                            ? "bg-primary text-primary-foreground"
                            : "border border-input bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )}
                      >
                        {dept}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Straße */}
            <div className="col-span-2 space-y-1">
              <label className="text-sm font-medium">Straße</label>
              <input
                type="text"
                value={formData.strasse}
                onChange={(e) => updateField("strasse", e.target.value)}
                className={inputClassName}
                placeholder="Musterstraße 1"
              />
            </div>

            {/* PLZ */}
            <div className="space-y-1">
              <label className="text-sm font-medium">PLZ</label>
              <input
                type="text"
                value={formData.plz}
                onChange={(e) => updateField("plz", e.target.value)}
                className={inputClassName}
                placeholder="12345"
              />
            </div>

            {/* Ort */}
            <div className="space-y-1">
              <label className="text-sm font-medium">Ort</label>
              <input
                type="text"
                value={formData.ort}
                onChange={(e) => updateField("ort", e.target.value)}
                className={inputClassName}
                placeholder="Musterstadt"
              />
            </div>
          </div>

          {/* Notizen */}
          <div className="space-y-1">
            <label className="text-sm font-medium">Notizen</label>
            <Textarea
              value={formData.notizen}
              onChange={(e) => updateField("notizen", e.target.value)}
              placeholder="Zusätzliche Notizen..."
              rows={3}
            />
          </div>

          <DialogFooter>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="inline-flex h-9 items-center justify-center rounded-md border border-input bg-transparent px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
            >
              {loading ? "Speichern..." : isEdit ? "Aktualisieren" : "Erstellen"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
