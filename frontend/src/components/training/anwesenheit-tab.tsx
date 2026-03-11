import { useState, useEffect, useCallback } from "react"
import { Save } from "lucide-react"
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
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import api from "@/lib/api"
import type { Trainingsgruppe } from "./trainingsgruppen-table"

interface MemberEntry {
  id: number
  vorname: string
  nachname: string
  mitgliedsnummer: string
}

interface AttendanceRecord {
  mitglied_id: number
  anwesend: boolean
  notiz: string
}

export function AnwesenheitTab() {
  const [gruppen, setGruppen] = useState<Trainingsgruppe[]>([])
  const [selectedGruppeId, setSelectedGruppeId] = useState("")
  const [datum, setDatum] = useState(() => new Date().toISOString().split("T")[0])
  const [members, setMembers] = useState<MemberEntry[]>([])
  const [attendance, setAttendance] = useState<Record<number, AttendanceRecord>>({})
  const [loadingGruppen, setLoadingGruppen] = useState(true)
  const [loadingMembers, setLoadingMembers] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState("")

  // Fetch training groups
  useEffect(() => {
    async function loadGruppen() {
      setLoadingGruppen(true)
      try {
        const data = await api.get<Trainingsgruppe[]>("/api/training/gruppen?aktiv=true")
        setGruppen(data)
      } catch {
        setGruppen([])
      } finally {
        setLoadingGruppen(false)
      }
    }
    loadGruppen()
  }, [])

  // Fetch members when group changes
  const selectedGruppe = gruppen.find((g) => g.id.toString() === selectedGruppeId)

  const fetchMembers = useCallback(async () => {
    if (!selectedGruppe) {
      setMembers([])
      return
    }
    setLoadingMembers(true)
    try {
      const data = await api.get<{ items?: MemberEntry[] }>(
        `/api/mitglieder?abteilung_id=${selectedGruppe.abteilung_id}`
      )
      const memberList = Array.isArray(data) ? data : (data.items ?? [])
      setMembers(memberList)
      // Initialize attendance state
      const initial: Record<number, AttendanceRecord> = {}
      for (const m of memberList) {
        initial[m.id] = { mitglied_id: m.id, anwesend: false, notiz: "" }
      }
      setAttendance(initial)
    } catch {
      setMembers([])
      setAttendance({})
    } finally {
      setLoadingMembers(false)
    }
  }, [selectedGruppe])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  function toggleAttendance(memberId: number) {
    setAttendance((prev) => ({
      ...prev,
      [memberId]: {
        ...prev[memberId],
        anwesend: !prev[memberId].anwesend,
      },
    }))
  }

  function updateNotiz(memberId: number, notiz: string) {
    setAttendance((prev) => ({
      ...prev,
      [memberId]: {
        ...prev[memberId],
        notiz,
      },
    }))
  }

  async function handleSave() {
    if (!selectedGruppeId || !datum) return
    setSaving(true)
    setSaveMessage("")

    const gruppeId = parseInt(selectedGruppeId)
    let errorCount = 0

    for (const record of Object.values(attendance)) {
      try {
        await api.post("/api/training/anwesenheit", {
          trainingsgruppe_id: gruppeId,
          mitglied_id: record.mitglied_id,
          datum,
          anwesend: record.anwesend,
          notiz: record.notiz || undefined,
        })
      } catch {
        errorCount++
      }
    }

    setSaving(false)
    if (errorCount === 0) {
      setSaveMessage("Anwesenheit erfolgreich gespeichert.")
    } else {
      setSaveMessage(`${errorCount} Einträge konnten nicht gespeichert werden.`)
    }
    // Clear message after 3 seconds
    setTimeout(() => setSaveMessage(""), 3000)
  }

  const presentCount = Object.values(attendance).filter((a) => a.anwesend).length

  return (
    <Card>
      <CardHeader>
        <CardTitle>Anwesenheit erfassen</CardTitle>
        <CardDescription>
          Wählen Sie eine Trainingsgruppe und erfassen Sie die Anwesenheit.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Selection row */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="anw-gruppe">Trainingsgruppe</Label>
            {loadingGruppen ? (
              <p className="text-sm text-muted-foreground">Laden...</p>
            ) : (
              <Select value={selectedGruppeId} onValueChange={setSelectedGruppeId}>
                <SelectTrigger id="anw-gruppe">
                  <SelectValue placeholder="Gruppe wählen" />
                </SelectTrigger>
                <SelectContent>
                  {gruppen.map((g) => (
                    <SelectItem key={g.id} value={g.id.toString()}>
                      {g.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="anw-datum">Datum</Label>
            <Input
              id="anw-datum"
              type="date"
              value={datum}
              onChange={(e) => setDatum(e.target.value)}
            />
          </div>
        </div>

        {/* Members list */}
        {selectedGruppeId && (
          <>
            {loadingMembers ? (
              <p className="text-sm text-muted-foreground">Mitglieder laden...</p>
            ) : members.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Keine Mitglieder in dieser Abteilung gefunden.
              </p>
            ) : (
              <>
                <div className="text-sm text-muted-foreground">
                  {presentCount} von {members.length} anwesend
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">Anwesend</TableHead>
                      <TableHead>Mitgliedsnr.</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Notiz</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => {
                      const record = attendance[member.id]
                      return (
                        <TableRow key={member.id}>
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={record?.anwesend ?? false}
                              onChange={() => toggleAttendance(member.id)}
                              className="h-4 w-4 rounded border-gray-300"
                            />
                          </TableCell>
                          <TableCell className="font-mono text-sm">
                            {member.mitgliedsnummer}
                          </TableCell>
                          <TableCell className="font-medium">
                            {member.vorname} {member.nachname}
                          </TableCell>
                          <TableCell>
                            <Input
                              value={record?.notiz ?? ""}
                              onChange={(e) => updateNotiz(member.id, e.target.value)}
                              placeholder="Optionale Notiz"
                              className="h-8"
                            />
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>

                <div className="flex items-center gap-4">
                  <Button onClick={handleSave} disabled={saving || !datum}>
                    <Save className="mr-2 h-4 w-4" />
                    {saving ? "Speichern..." : "Anwesenheit speichern"}
                  </Button>
                  {saveMessage && (
                    <p className="text-sm text-muted-foreground">{saveMessage}</p>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
