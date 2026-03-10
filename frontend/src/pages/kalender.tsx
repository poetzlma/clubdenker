import { useState, useEffect, useCallback, useMemo } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { PageHeader } from "@/components/dashboard/page-header"
import { WeekView } from "@/components/calendar/week-view"
import type { CalendarEvent } from "@/components/calendar/week-view"
import api from "@/lib/api"
import type { Abteilung } from "@/types/setup"

interface TrainingsgruppeAPI {
  id: number
  name: string
  abteilung_id: number
  trainer: string | null
  wochentag: string
  uhrzeit: string
  dauer_minuten: number
  max_teilnehmer: number | null
  ort: string | null
  aktiv: boolean
}

/**
 * Returns the Monday of the week containing the given date.
 */
function getMonday(d: Date): Date {
  const result = new Date(d)
  const day = result.getDay()
  // JS: Sunday=0, Monday=1, ...
  const diff = day === 0 ? -6 : 1 - day
  result.setDate(result.getDate() + diff)
  result.setHours(0, 0, 0, 0)
  return result
}

/**
 * Returns an array of 7 dates starting from the given Monday.
 */
function getWeekDates(monday: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })
}

function formatWeekLabel(monday: Date): string {
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)

  const fmtDay = (d: Date) =>
    `${d.getDate().toString().padStart(2, "0")}.${(d.getMonth() + 1).toString().padStart(2, "0")}.${d.getFullYear()}`

  return `${fmtDay(monday)} - ${fmtDay(sunday)}`
}

const WOCHENTAG_TO_INDEX: Record<string, number> = {
  montag: 0,
  dienstag: 1,
  mittwoch: 2,
  donnerstag: 3,
  freitag: 4,
  samstag: 5,
  sonntag: 6,
}

export function KalenderPage() {
  const [monday, setMonday] = useState(() => getMonday(new Date()))
  const [gruppen, setGruppen] = useState<TrainingsgruppeAPI[]>([])
  const [abteilungen, setAbteilungen] = useState<Abteilung[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)

  const weekDates = useMemo(() => getWeekDates(monday), [monday])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [gData, aData] = await Promise.all([
        api.get<TrainingsgruppeAPI[]>("/api/training/gruppen"),
        api.get<Abteilung[]>("/api/setup/abteilungen"),
      ])
      setGruppen(gData)
      setAbteilungen(aData)
    } catch {
      setGruppen([])
      setAbteilungen([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Build abteilung lookup
  const abteilungMap = useMemo(() => {
    const map: Record<number, string> = {}
    for (const a of abteilungen) {
      map[a.id] = a.name
    }
    return map
  }, [abteilungen])

  // Generate calendar events from recurring training groups
  const events: CalendarEvent[] = useMemo(() => {
    return gruppen
      .filter((g) => g.aktiv)
      .map((g) => {
        const dayIndex = WOCHENTAG_TO_INDEX[g.wochentag.toLowerCase()] ?? 0
        const date = weekDates[dayIndex]
        return {
          id: g.id,
          name: g.name,
          trainer: g.trainer,
          ort: g.ort,
          wochentag: g.wochentag,
          uhrzeit: g.uhrzeit,
          dauer_minuten: g.dauer_minuten,
          abteilung_id: g.abteilung_id,
          abteilung_name: abteilungMap[g.abteilung_id] ?? "Unbekannt",
          date: date?.toISOString().slice(0, 10) ?? "",
        }
      })
  }, [gruppen, abteilungMap, weekDates])

  // Unique abteilungen with colors for the legend
  const legendItems = useMemo(() => {
    const seen = new Set<number>()
    const items: { id: number; name: string }[] = []
    for (const e of events) {
      if (!seen.has(e.abteilung_id)) {
        seen.add(e.abteilung_id)
        items.push({ id: e.abteilung_id, name: e.abteilung_name })
      }
    }
    return items.sort((a, b) => a.id - b.id)
  }, [events])

  function goToday() {
    setMonday(getMonday(new Date()))
  }

  function goPrev() {
    const prev = new Date(monday)
    prev.setDate(prev.getDate() - 7)
    setMonday(prev)
  }

  function goNext() {
    const next = new Date(monday)
    next.setDate(next.getDate() + 7)
    setMonday(next)
  }

  const WOCHENTAG_LABELS: Record<string, string> = {
    montag: "Montag",
    dienstag: "Dienstag",
    mittwoch: "Mittwoch",
    donnerstag: "Donnerstag",
    freitag: "Freitag",
    samstag: "Samstag",
    sonntag: "Sonntag",
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Kalender"
        description="Wochenansicht aller Trainingseinheiten."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={goToday}>
              Heute
            </Button>
            <Button variant="outline" size="icon" onClick={goPrev}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-[220px] text-center text-sm font-medium">
              {formatWeekLabel(monday)}
            </span>
            <Button variant="outline" size="icon" onClick={goNext}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        }
      />

      {/* Legend */}
      {legendItems.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {legendItems.map((item) => (
            <Badge key={item.id} variant="outline" className="text-xs">
              {item.name}
            </Badge>
          ))}
        </div>
      )}

      {/* Calendar */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-6 text-sm text-muted-foreground">Laden...</p>
          ) : events.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">
              Keine Trainingsgruppen vorhanden. Erstellen Sie Gruppen unter Training.
            </p>
          ) : (
            <WeekView
              events={events}
              weekDates={weekDates}
              onEventClick={setSelectedEvent}
            />
          )}
        </CardContent>
      </Card>

      {/* Event Detail Dialog */}
      <Dialog
        open={selectedEvent !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedEvent(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selectedEvent?.name}</DialogTitle>
          </DialogHeader>
          {selectedEvent && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-[120px_1fr] gap-y-2">
                <span className="font-medium text-muted-foreground">Abteilung</span>
                <span>{selectedEvent.abteilung_name}</span>

                <span className="font-medium text-muted-foreground">Wochentag</span>
                <span>
                  {WOCHENTAG_LABELS[selectedEvent.wochentag.toLowerCase()] ??
                    selectedEvent.wochentag}
                </span>

                <span className="font-medium text-muted-foreground">Uhrzeit</span>
                <span>{selectedEvent.uhrzeit} Uhr</span>

                <span className="font-medium text-muted-foreground">Dauer</span>
                <span>{selectedEvent.dauer_minuten} Minuten</span>

                {selectedEvent.trainer && (
                  <>
                    <span className="font-medium text-muted-foreground">Trainer</span>
                    <span>{selectedEvent.trainer}</span>
                  </>
                )}

                {selectedEvent.ort && (
                  <>
                    <span className="font-medium text-muted-foreground">Ort</span>
                    <span>{selectedEvent.ort}</span>
                  </>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
