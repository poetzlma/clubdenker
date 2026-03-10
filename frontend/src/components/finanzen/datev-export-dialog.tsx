import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const API_BASE = "/api"

type ExportType = "buchungen" | "rechnungen"

interface DatevExportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  exportType: ExportType
}

const currentYear = new Date().getFullYear()
const years = Array.from({ length: 5 }, (_, i) => currentYear - i)
const months = [
  { value: "", label: "Alle Monate" },
  { value: "1", label: "Januar" },
  { value: "2", label: "Februar" },
  { value: "3", label: "Maerz" },
  { value: "4", label: "April" },
  { value: "5", label: "Mai" },
  { value: "6", label: "Juni" },
  { value: "7", label: "Juli" },
  { value: "8", label: "August" },
  { value: "9", label: "September" },
  { value: "10", label: "Oktober" },
  { value: "11", label: "November" },
  { value: "12", label: "Dezember" },
]

export function DatevExportDialog({
  open,
  onOpenChange,
  exportType,
}: DatevExportDialogProps) {
  const [year, setYear] = useState<string>(String(currentYear))
  const [month, setMonth] = useState<string>("")
  const [loading, setLoading] = useState(false)

  const title =
    exportType === "buchungen"
      ? "DATEV Buchungen exportieren"
      : "DATEV Rechnungen exportieren"

  const handleExport = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ jahr: year })
      if (exportType === "buchungen" && month) {
        params.set("monat", month)
      }
      const url = `${API_BASE}/finanzen/export/datev/${exportType}?${params.toString()}`
      const res = await fetch(url)
      if (!res.ok) throw new Error("Export fehlgeschlagen")

      const blob = await res.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = downloadUrl
      const monthSuffix =
        exportType === "buchungen" && month
          ? `_${month.padStart(2, "0")}`
          : ""
      a.download = `DATEV_${exportType === "buchungen" ? "Buchungen" : "Rechnungen"}_${year}${monthSuffix}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(downloadUrl)
      onOpenChange(false)
    } catch {
      // Could add toast notification here
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            CSV-Datei im DATEV-Format (Windows-1252, Semikolon-getrennt)
            herunterladen.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="datev-year">Jahr</Label>
            <Select value={year} onValueChange={setYear}>
              <SelectTrigger id="datev-year" data-testid="datev-year">
                <SelectValue placeholder="Jahr" />
              </SelectTrigger>
              <SelectContent>
                {years.map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {exportType === "buchungen" && (
            <div className="space-y-2">
              <Label htmlFor="datev-month">Monat (optional)</Label>
              <Select value={month} onValueChange={setMonth}>
                <SelectTrigger id="datev-month" data-testid="datev-month">
                  <SelectValue placeholder="Alle Monate" />
                </SelectTrigger>
                <SelectContent>
                  {months.map((m) => (
                    <SelectItem key={m.value || "all"} value={m.value || "all"}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Abbrechen
          </Button>
          <Button
            onClick={handleExport}
            disabled={loading}
            data-testid="datev-export-btn"
          >
            {loading ? "Exportiere..." : "Exportieren"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
