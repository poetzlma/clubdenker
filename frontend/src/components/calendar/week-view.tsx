import { useMemo } from "react"
import { cn } from "@/lib/utils"

const DAYS = [
  { key: "montag", label: "Montag" },
  { key: "dienstag", label: "Dienstag" },
  { key: "mittwoch", label: "Mittwoch" },
  { key: "donnerstag", label: "Donnerstag" },
  { key: "freitag", label: "Freitag" },
  { key: "samstag", label: "Samstag" },
  { key: "sonntag", label: "Sonntag" },
] as const

const START_HOUR = 7
const END_HOUR = 22
const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i)

// Colors mapped by abteilung_id for deterministic assignment
const ABTEILUNG_COLORS: Record<number, { bg: string; border: string; text: string }> = {
  1: { bg: "bg-blue-100 dark:bg-blue-900/40", border: "border-blue-400 dark:border-blue-600", text: "text-blue-800 dark:text-blue-200" },
  2: { bg: "bg-green-100 dark:bg-green-900/40", border: "border-green-400 dark:border-green-600", text: "text-green-800 dark:text-green-200" },
  3: { bg: "bg-orange-100 dark:bg-orange-900/40", border: "border-orange-400 dark:border-orange-600", text: "text-orange-800 dark:text-orange-200" },
  4: { bg: "bg-purple-100 dark:bg-purple-900/40", border: "border-purple-400 dark:border-purple-600", text: "text-purple-800 dark:text-purple-200" },
  5: { bg: "bg-red-100 dark:bg-red-900/40", border: "border-red-400 dark:border-red-600", text: "text-red-800 dark:text-red-200" },
  6: { bg: "bg-teal-100 dark:bg-teal-900/40", border: "border-teal-400 dark:border-teal-600", text: "text-teal-800 dark:text-teal-200" },
  7: { bg: "bg-pink-100 dark:bg-pink-900/40", border: "border-pink-400 dark:border-pink-600", text: "text-pink-800 dark:text-pink-200" },
  8: { bg: "bg-yellow-100 dark:bg-yellow-900/40", border: "border-yellow-400 dark:border-yellow-600", text: "text-yellow-800 dark:text-yellow-200" },
}

const DEFAULT_COLOR = { bg: "bg-gray-100 dark:bg-gray-800", border: "border-gray-400 dark:border-gray-600", text: "text-gray-800 dark:text-gray-200" }

function getColor(abteilungId: number) {
  return ABTEILUNG_COLORS[abteilungId] ?? DEFAULT_COLOR
}

export interface CalendarEvent {
  id: number
  name: string
  trainer: string | null
  ort: string | null
  wochentag: string
  uhrzeit: string
  dauer_minuten: number
  abteilung_id: number
  abteilung_name: string
  date: string // ISO date string for the specific day in the week
}

interface WeekViewProps {
  events: CalendarEvent[]
  weekDates: Date[]
  onEventClick: (event: CalendarEvent) => void
}

function formatDate(d: Date): string {
  const day = d.getDate().toString().padStart(2, "0")
  const month = (d.getMonth() + 1).toString().padStart(2, "0")
  return `${day}.${month}.`
}

function isToday(d: Date): boolean {
  const now = new Date()
  return (
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear()
  )
}

export function WeekView({ events, weekDates, onEventClick }: WeekViewProps) {
  // Group events by day key
  const eventsByDay = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {}
    for (const day of DAYS) {
      map[day.key] = []
    }
    for (const event of events) {
      const key = event.wochentag.toLowerCase()
      if (map[key]) {
        map[key].push(event)
      }
    }
    return map
  }, [events])

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[900px]">
        {/* Header row with day names and dates */}
        <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-border">
          <div className="p-2 text-xs font-medium text-muted-foreground" />
          {DAYS.map((day, i) => {
            const date = weekDates[i]
            const today = date ? isToday(date) : false
            return (
              <div
                key={day.key}
                className={cn(
                  "p-2 text-center text-sm font-medium border-l border-border",
                  today && "bg-accent"
                )}
              >
                <div className={cn(today && "font-bold")}>{day.label}</div>
                {date && (
                  <div className="text-xs text-muted-foreground">
                    {formatDate(date)}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Time grid */}
        <div className="relative">
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-border"
              style={{ height: 60 }}
            >
              {/* Time label */}
              <div className="p-1 text-right text-xs text-muted-foreground pr-2 pt-0 -translate-y-2">
                {hour.toString().padStart(2, "0")}:00
              </div>
              {/* Day columns */}
              {DAYS.map((day) => (
                <div
                  key={`${hour}-${day.key}`}
                  className="relative border-l border-border"
                />
              ))}
            </div>
          ))}

          {/* Overlay events on top of the grid */}
          <div className="absolute inset-0 grid grid-cols-[60px_repeat(7,1fr)] pointer-events-none">
            <div />
            {DAYS.map((day) => (
              <div key={day.key} className="relative border-l border-border">
                {eventsByDay[day.key]?.map((event) => {
                  const [hourStr, minStr] = event.uhrzeit.split(":")
                  const startHour = parseInt(hourStr, 10)
                  const startMin = parseInt(minStr, 10)

                  // Position relative to START_HOUR
                  const topMinutes = (startHour - START_HOUR) * 60 + startMin
                  const topPx = (topMinutes / 60) * 60 // 60px per hour
                  const heightPx = (event.dauer_minuten / 60) * 60

                  if (startHour < START_HOUR || startHour >= END_HOUR) return null

                  const color = getColor(event.abteilung_id)

                  return (
                    <div
                      key={event.id}
                      className={cn(
                        "absolute left-0.5 right-0.5 rounded border px-1.5 py-0.5 cursor-pointer pointer-events-auto overflow-hidden transition-opacity hover:opacity-80",
                        color.bg,
                        color.border,
                        color.text
                      )}
                      style={{
                        top: topPx,
                        height: Math.max(heightPx, 24),
                      }}
                      onClick={() => onEventClick(event)}
                      title={`${event.name} - ${event.trainer ?? ""} - ${event.ort ?? ""}`}
                    >
                      <div className="text-xs font-semibold truncate leading-tight">
                        {event.name}
                      </div>
                      {heightPx >= 40 && (
                        <div className="text-[10px] truncate leading-tight opacity-80">
                          {event.trainer ?? ""}
                        </div>
                      )}
                      {heightPx >= 56 && event.ort && (
                        <div className="text-[10px] truncate leading-tight opacity-70">
                          {event.ort}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export { DAYS }
