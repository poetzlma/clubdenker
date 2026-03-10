import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { Protokoll, ProtokollTyp } from "@/types/dokumente"
import { PROTOKOLL_TYP_LABELS } from "@/types/dokumente"

interface ProtokollDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  protokoll: Protokoll | null
}

export function ProtokollDetailDialog({
  open,
  onOpenChange,
  protokoll,
}: ProtokollDetailDialogProps) {
  if (!protokoll) return null

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString("de-DE", {
        weekday: "long",
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    } catch {
      return dateStr
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{protokoll.titel}</DialogTitle>
          <DialogDescription>
            {formatDate(protokoll.datum)}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Meta info */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div>
              <span className="font-medium text-muted-foreground">Typ: </span>
              <Badge variant="outline">
                {PROTOKOLL_TYP_LABELS[protokoll.typ as ProtokollTyp] ?? protokoll.typ}
              </Badge>
            </div>
            {protokoll.erstellt_von && (
              <div>
                <span className="font-medium text-muted-foreground">
                  Erstellt von:{" "}
                </span>
                {protokoll.erstellt_von}
              </div>
            )}
          </div>

          {protokoll.teilnehmer && (
            <>
              <Separator />
              <div>
                <h3 className="mb-1 text-sm font-semibold">Teilnehmer</h3>
                <p className="text-sm whitespace-pre-wrap">
                  {protokoll.teilnehmer}
                </p>
              </div>
            </>
          )}

          <Separator />

          {/* Inhalt */}
          <div>
            <h3 className="mb-1 text-sm font-semibold">
              Inhalt / Tagesordnung
            </h3>
            <div className="rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
              {protokoll.inhalt}
            </div>
          </div>

          {/* Beschluesse */}
          {protokoll.beschluesse && (
            <>
              <Separator />
              <div>
                <h3 className="mb-1 text-sm font-semibold">Beschluesse</h3>
                <div className="rounded-md border p-4 text-sm whitespace-pre-wrap">
                  {protokoll.beschluesse}
                </div>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
