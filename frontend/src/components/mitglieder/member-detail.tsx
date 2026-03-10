import { useState } from "react"
import type { Member } from "@/types/member"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { STATUS_COLORS } from "@/constants/design"

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-"
  const date = new Date(dateStr)
  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}

const beitragLabels: Record<Member["beitragskategorie"], string> = {
  erwachsene: "Erwachsene",
  jugend: "Jugend",
  familie: "Familie",
  passiv: "Passiv",
  ehrenmitglied: "Ehrenmitglied",
}

const allDepartments = [
  "Fußball",
  "Tennis",
  "Schwimmen",
  "Leichtathletik",
  "Turnen",
  "Handball",
]

interface MemberDetailProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  member: Member | null
  onEdit?: (member: Member) => void
  onCancel?: (member: Member) => Promise<void>
  onAddDepartment?: (memberId: number, department: string) => Promise<void>
  onRemoveDepartment?: (memberId: number, department: string) => Promise<void>
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-2 border-b border-border/50">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      <span className="col-span-2 text-sm">{value}</span>
    </div>
  )
}

export function MemberDetail({
  open,
  onOpenChange,
  member,
  onEdit,
  onCancel,
  onAddDepartment,
  onRemoveDepartment,
}: MemberDetailProps) {
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [cancelLoading, setCancelLoading] = useState(false)

  if (!member) return null

  const statusInfo = STATUS_COLORS[member.status]

  async function handleCancel() {
    if (!member || !onCancel) return
    setCancelLoading(true)
    try {
      await onCancel(member)
      setConfirmCancel(false)
      onOpenChange(false)
    } catch {
      // error handling
    } finally {
      setCancelLoading(false)
    }
  }

  const availableDepts = allDepartments.filter(
    (d) => !member.abteilungen.includes(d)
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {member.vorname} {member.nachname}
          </DialogTitle>
          <DialogDescription>
            Mitgliedsnummer: {member.mitgliedsnummer}
            <span
              className={cn(
                "ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                statusInfo.bg,
                statusInfo.text
              )}
            >
              {statusInfo.label}
            </span>
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="stammdaten" className="w-full">
          <TabsList className="w-full">
            <TabsTrigger value="stammdaten" className="flex-1">
              Stammdaten
            </TabsTrigger>
            <TabsTrigger value="abteilungen" className="flex-1">
              Abteilungen
            </TabsTrigger>
            <TabsTrigger value="beitraege" className="flex-1">
              Beiträge
            </TabsTrigger>
          </TabsList>

          <TabsContent value="stammdaten" className="space-y-1">
            <InfoRow label="Vorname" value={member.vorname} />
            <InfoRow label="Nachname" value={member.nachname} />
            <InfoRow label="E-Mail" value={member.email} />
            <InfoRow label="Telefon" value={member.telefon || "-"} />
            <InfoRow
              label="Geburtsdatum"
              value={formatDate(member.geburtsdatum)}
            />
            <InfoRow label="Straße" value={member.strasse || "-"} />
            <InfoRow label="PLZ" value={member.plz || "-"} />
            <InfoRow label="Ort" value={member.ort || "-"} />
            <InfoRow
              label="Beitragskategorie"
              value={beitragLabels[member.beitragskategorie]}
            />
            <InfoRow
              label="Eintrittsdatum"
              value={formatDate(member.eintrittsdatum)}
            />
            <InfoRow
              label="Austrittsdatum"
              value={formatDate(member.austrittsdatum)}
            />
            <InfoRow label="Notizen" value={member.notizen || "-"} />

            <div className="flex gap-2 pt-4">
              {onEdit && (
                <button
                  onClick={() => onEdit(member)}
                  className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
                >
                  Bearbeiten
                </button>
              )}
              {member.status !== "gekuendigt" && onCancel && (
                <>
                  {!confirmCancel ? (
                    <button
                      onClick={() => setConfirmCancel(true)}
                      className="inline-flex h-9 items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-red-700"
                    >
                      Kündigen
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-red-600">
                        Wirklich kündigen?
                      </span>
                      <button
                        onClick={handleCancel}
                        disabled={cancelLoading}
                        className="inline-flex h-8 items-center justify-center rounded-md bg-red-600 px-3 py-1 text-sm font-medium text-white shadow hover:bg-red-700 disabled:opacity-50"
                      >
                        {cancelLoading ? "..." : "Ja"}
                      </button>
                      <button
                        onClick={() => setConfirmCancel(false)}
                        className="inline-flex h-8 items-center justify-center rounded-md border border-input bg-transparent px-3 py-1 text-sm font-medium shadow-sm hover:bg-accent"
                      >
                        Nein
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </TabsContent>

          <TabsContent value="abteilungen" className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Aktuelle Abteilungen</h4>
              {member.abteilungen.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Keine Abteilungen zugeordnet.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {member.abteilungen.map((dept) => (
                    <div
                      key={dept}
                      className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700"
                    >
                      {dept}
                      {onRemoveDepartment && (
                        <button
                          onClick={() =>
                            onRemoveDepartment(member.id, dept)
                          }
                          className="ml-1 rounded-full p-0.5 hover:bg-gray-200"
                          title="Entfernen"
                        >
                          &times;
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {availableDepts.length > 0 && onAddDepartment && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Abteilung hinzufügen</h4>
                <div className="flex flex-wrap gap-2">
                  {availableDepts.map((dept) => (
                    <button
                      key={dept}
                      onClick={() => onAddDepartment(member.id, dept)}
                      className="inline-flex items-center rounded-full border border-dashed border-gray-300 px-3 py-1 text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700"
                    >
                      + {dept}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="beitraege" className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Beitragshistorie wird in einer zukünftigen Version verfügbar sein.
            </p>
            <div className="rounded-md border border-dashed p-8 text-center text-muted-foreground">
              <p className="text-sm">Hier werden zukünftig Beitragszahlungen angezeigt.</p>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
