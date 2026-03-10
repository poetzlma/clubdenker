import { useState, useEffect, useCallback } from "react"
import { Plus, Pencil, Trash2 } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip"
import api from "@/lib/api"
import type { Abteilung, BeitragsKategorie } from "@/types/setup"
import type { Kostenstelle } from "@/types/finance"
import { VereinsstammdatenForm } from "@/components/admin/vereinsstammdaten-form"

// --- Mock data ---

const MOCK_ABTEILUNGEN: Abteilung[] = [
  { id: 1, name: "Fussball", beschreibung: "Fußballabteilung", mitglieder_count: 95, created_at: "2024-01-01" },
  { id: 2, name: "Tennis", beschreibung: "Tennisabteilung", mitglieder_count: 53, created_at: "2024-01-01" },
  { id: 3, name: "Fitness", beschreibung: "Fitnessbereich", mitglieder_count: 49, created_at: "2024-01-01" },
  { id: 4, name: "Leichtathletik", beschreibung: "Leichtathletikabteilung", mitglieder_count: 34, created_at: "2024-01-01" },
  { id: 5, name: "Schwimmen", beschreibung: "Schwimmabteilung", mitglieder_count: 28, created_at: "2024-01-01" },
]

const MOCK_KATEGORIEN: BeitragsKategorie[] = [
  { id: 1, name: "Erwachsene", jahresbeitrag: 120, beschreibung: "Vollbeitrag ab 18 Jahre", created_at: "2024-01-01" },
  { id: 2, name: "Jugend", jahresbeitrag: 60, beschreibung: "Ermäßigter Beitrag bis 18 Jahre", created_at: "2024-01-01" },
  { id: 3, name: "Familie", jahresbeitrag: 180, beschreibung: "Familienbeitrag (2+ Mitglieder)", created_at: "2024-01-01" },
  { id: 4, name: "Passiv", jahresbeitrag: 40, beschreibung: "Fördermitglied ohne aktive Teilnahme", created_at: "2024-01-01" },
  { id: 5, name: "Ehrenmitglied", jahresbeitrag: 0, beschreibung: "Beitragsfreies Ehrenmitglied", created_at: "2024-01-01" },
]

const MOCK_KOSTENSTELLEN: Kostenstelle[] = [
  { id: 1, name: "Fussball Spielbetrieb", beschreibung: "Laufende Kosten Fußball", budget: 15000, freigabelimit: 500, ausgegeben: 8200, verfuegbar: 6800 },
  { id: 2, name: "Tennis Platzpflege", beschreibung: "Platzwartung Tennis", budget: 8000, freigabelimit: 300, ausgegeben: 3100, verfuegbar: 4900 },
  { id: 3, name: "Vereinsheim", beschreibung: "Betriebskosten Vereinsheim", budget: 12000, freigabelimit: 1000, ausgegeben: 9800, verfuegbar: 2200 },
]

// --- Helpers ---

function formatCurrency(value: number): string {
  return value.toLocaleString("de-DE", { style: "currency", currency: "EUR" })
}

// --- Abteilungen Section ---

function AbteilungenTab() {
  const [items, setItems] = useState<Abteilung[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Abteilung | null>(null)
  const [deleting, setDeleting] = useState<Abteilung | null>(null)
  const [formName, setFormName] = useState("")
  const [formBeschreibung, setFormBeschreibung] = useState("")

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<Abteilung[]>("/api/setup/abteilungen")
      setItems(data)
    } catch {
      setItems(MOCK_ABTEILUNGEN)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  function openCreate() {
    setEditing(null)
    setFormName("")
    setFormBeschreibung("")
    setDialogOpen(true)
  }

  function openEdit(item: Abteilung) {
    setEditing(item)
    setFormName(item.name)
    setFormBeschreibung(item.beschreibung ?? "")
    setDialogOpen(true)
  }

  function openDelete(item: Abteilung) {
    setDeleting(item)
    setDeleteDialogOpen(true)
  }

  async function handleSave() {
    const payload = { name: formName, beschreibung: formBeschreibung || undefined }
    try {
      if (editing) {
        await api.put(`/api/setup/abteilungen/${editing.id}`, payload)
      } else {
        await api.post("/api/setup/abteilungen", payload)
      }
    } catch {
      // mock fallback: update locally
      if (editing) {
        setItems((prev) => prev.map((i) => i.id === editing.id ? { ...i, name: payload.name, beschreibung: payload.beschreibung ?? null } : i))
      } else {
        const newItem: Abteilung = { id: Date.now(), name: formName, beschreibung: formBeschreibung || null, mitglieder_count: 0, created_at: new Date().toISOString() }
        setItems((prev) => [...prev, newItem])
      }
    }
    setDialogOpen(false)
    fetchData()
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/setup/abteilungen/${deleting.id}`)
    } catch {
      setItems((prev) => prev.filter((i) => i.id !== deleting.id))
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>Abteilungen</CardTitle>
          <CardDescription>Verwalten Sie die Abteilungen des Vereins.</CardDescription>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Neue Abteilung
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Laden...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Abteilungen vorhanden. Erstellen Sie die erste Abteilung.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Beschreibung</TableHead>
                <TableHead className="text-right">Mitglieder</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>{item.beschreibung ?? "—"}</TableCell>
                  <TableCell className="text-right">{item.mitglieder_count ?? 0}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(item)} aria-label={`${item.name} bearbeiten`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => openDelete(item)}
                                disabled={(item.mitglieder_count ?? 0) > 0}
                                aria-label={`${item.name} löschen`}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </span>
                          </TooltipTrigger>
                          {(item.mitglieder_count ?? 0) > 0 && (
                            <TooltipContent>
                              {item.mitglieder_count} Mitglieder zugeordnet
                            </TooltipContent>
                          )}
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Abteilung bearbeiten" : "Neue Abteilung"}</DialogTitle>
            <DialogDescription>
              {editing ? "Bearbeiten Sie die Abteilungsdaten." : "Erstellen Sie eine neue Abteilung."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="abt-name">Name</Label>
              <Input id="abt-name" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="z.B. Fussball" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="abt-beschreibung">Beschreibung</Label>
              <Input id="abt-beschreibung" value={formBeschreibung} onChange={(e) => setFormBeschreibung(e.target.value)} placeholder="Optionale Beschreibung" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Abbrechen</Button>
            <Button onClick={handleSave} disabled={!formName.trim()}>Speichern</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Abteilung löschen</DialogTitle>
            <DialogDescription>
              Möchten Sie die Abteilung &quot;{deleting?.name}&quot; wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Abbrechen</Button>
            <Button variant="destructive" onClick={handleDelete}>Löschen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

// --- Beitragskategorien Section ---

function BeitragskategorienTab() {
  const [items, setItems] = useState<BeitragsKategorie[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<BeitragsKategorie | null>(null)
  const [deleting, setDeleting] = useState<BeitragsKategorie | null>(null)
  const [formName, setFormName] = useState("")
  const [formJahresbeitrag, setFormJahresbeitrag] = useState("")
  const [formBeschreibung, setFormBeschreibung] = useState("")

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<BeitragsKategorie[]>("/api/setup/beitragskategorien")
      setItems(data)
    } catch {
      setItems(MOCK_KATEGORIEN)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  function openCreate() {
    setEditing(null)
    setFormName("")
    setFormJahresbeitrag("")
    setFormBeschreibung("")
    setDialogOpen(true)
  }

  function openEdit(item: BeitragsKategorie) {
    setEditing(item)
    setFormName(item.name)
    setFormJahresbeitrag(item.jahresbeitrag.toString())
    setFormBeschreibung(item.beschreibung ?? "")
    setDialogOpen(true)
  }

  function openDelete(item: BeitragsKategorie) {
    setDeleting(item)
    setDeleteDialogOpen(true)
  }

  async function handleSave() {
    const payload = {
      name: formName,
      jahresbeitrag: parseFloat(formJahresbeitrag) || 0,
      beschreibung: formBeschreibung || undefined,
    }
    try {
      if (editing) {
        await api.put(`/api/setup/beitragskategorien/${editing.id}`, payload)
      } else {
        await api.post("/api/setup/beitragskategorien", payload)
      }
    } catch {
      if (editing) {
        setItems((prev) => prev.map((i) => i.id === editing.id ? { ...i, ...payload, beschreibung: payload.beschreibung ?? null } : i))
      } else {
        const newItem: BeitragsKategorie = { id: Date.now(), name: formName, jahresbeitrag: payload.jahresbeitrag, beschreibung: formBeschreibung || null, created_at: new Date().toISOString() }
        setItems((prev) => [...prev, newItem])
      }
    }
    setDialogOpen(false)
    fetchData()
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/setup/beitragskategorien/${deleting.id}`)
    } catch {
      setItems((prev) => prev.filter((i) => i.id !== deleting.id))
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>Beitragskategorien</CardTitle>
          <CardDescription>Verwalten Sie die Beitragskategorien und Jahresbeiträge.</CardDescription>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Neue Kategorie
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Laden...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Beitragskategorien vorhanden. Erstellen Sie die erste Kategorie.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Jahresbeitrag</TableHead>
                <TableHead>Beschreibung</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.jahresbeitrag)}/Jahr</TableCell>
                  <TableCell>{item.beschreibung ?? "—"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(item)} aria-label={`${item.name} bearbeiten`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => openDelete(item)} aria-label={`${item.name} löschen`}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Kategorie bearbeiten" : "Neue Beitragskategorie"}</DialogTitle>
            <DialogDescription>
              {editing ? "Bearbeiten Sie die Kategoriedaten." : "Erstellen Sie eine neue Beitragskategorie."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="kat-name">Name</Label>
              <Input id="kat-name" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="z.B. Erwachsene" disabled={!!editing} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kat-jahresbeitrag">Jahresbeitrag (EUR)</Label>
              <Input id="kat-jahresbeitrag" type="number" step="0.01" min="0" value={formJahresbeitrag} onChange={(e) => setFormJahresbeitrag(e.target.value)} placeholder="0,00" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kat-beschreibung">Beschreibung</Label>
              <Input id="kat-beschreibung" value={formBeschreibung} onChange={(e) => setFormBeschreibung(e.target.value)} placeholder="Optionale Beschreibung" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Abbrechen</Button>
            <Button onClick={handleSave} disabled={!formName.trim()}>Speichern</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Beitragskategorie löschen</DialogTitle>
            <DialogDescription>
              Möchten Sie die Kategorie &quot;{deleting?.name}&quot; wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Abbrechen</Button>
            <Button variant="destructive" onClick={handleDelete}>Löschen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

// --- Kostenstellen Section ---

function KostenstellenTab() {
  const [items, setItems] = useState<Kostenstelle[]>([])
  const [abteilungen, setAbteilungen] = useState<Abteilung[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Kostenstelle | null>(null)
  const [deleting, setDeleting] = useState<Kostenstelle | null>(null)
  const [formName, setFormName] = useState("")
  const [formBeschreibung, setFormBeschreibung] = useState("")
  const [formAbteilung, setFormAbteilung] = useState("")
  const [formBudget, setFormBudget] = useState("")
  const [formFreigabelimit, setFormFreigabelimit] = useState("")

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [kData, aData] = await Promise.all([
        api.get<Kostenstelle[]>("/api/finanzen/kostenstellen"),
        api.get<Abteilung[]>("/api/setup/abteilungen"),
      ])
      setItems(kData)
      setAbteilungen(aData)
    } catch {
      setItems(MOCK_KOSTENSTELLEN)
      setAbteilungen(MOCK_ABTEILUNGEN)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  function openCreate() {
    setEditing(null)
    setFormName("")
    setFormBeschreibung("")
    setFormAbteilung("")
    setFormBudget("")
    setFormFreigabelimit("")
    setDialogOpen(true)
  }

  function openEdit(item: Kostenstelle) {
    setEditing(item)
    setFormName(item.name)
    setFormBeschreibung(item.beschreibung ?? "")
    setFormAbteilung("")
    setFormBudget(item.budget.toString())
    setFormFreigabelimit(item.freigabelimit.toString())
    setDialogOpen(true)
  }

  function openDelete(item: Kostenstelle) {
    setDeleting(item)
    setDeleteDialogOpen(true)
  }

  async function handleSave() {
    const payload = {
      name: formName,
      beschreibung: formBeschreibung || undefined,
      abteilung: formAbteilung || undefined,
      budget: parseFloat(formBudget) || 0,
      freigabelimit: parseFloat(formFreigabelimit) || 0,
    }
    try {
      if (editing) {
        await api.put(`/api/finanzen/kostenstellen/${editing.id}`, payload)
      } else {
        await api.post("/api/finanzen/kostenstellen", payload)
      }
    } catch {
      if (editing) {
        setItems((prev) => prev.map((i) => i.id === editing.id ? { ...i, name: payload.name, beschreibung: payload.beschreibung ?? "", budget: payload.budget, freigabelimit: payload.freigabelimit } : i))
      } else {
        const newItem: Kostenstelle = { id: Date.now(), name: formName, beschreibung: formBeschreibung || "", budget: payload.budget, freigabelimit: payload.freigabelimit, ausgegeben: 0, verfuegbar: payload.budget }
        setItems((prev) => [...prev, newItem])
      }
    }
    setDialogOpen(false)
    fetchData()
  }

  async function handleDelete() {
    if (!deleting) return
    try {
      await api.delete(`/api/finanzen/kostenstellen/${deleting.id}`)
    } catch {
      setItems((prev) => prev.filter((i) => i.id !== deleting.id))
    }
    setDeleteDialogOpen(false)
    setDeleting(null)
    fetchData()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="space-y-1">
          <CardTitle>Kostenstellen</CardTitle>
          <CardDescription>Verwalten Sie die Kostenstellen und Budgets.</CardDescription>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus className="mr-2 h-4 w-4" />
          Neue Kostenstelle
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">Laden...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Keine Kostenstellen vorhanden. Erstellen Sie die erste Kostenstelle.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Beschreibung</TableHead>
                <TableHead className="text-right">Budget</TableHead>
                <TableHead className="text-right">Freigabelimit</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>{item.beschreibung || "—"}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.budget)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.freigabelimit)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(item)} aria-label={`${item.name} bearbeiten`}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => openDelete(item)} aria-label={`${item.name} löschen`}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Kostenstelle bearbeiten" : "Neue Kostenstelle"}</DialogTitle>
            <DialogDescription>
              {editing ? "Bearbeiten Sie die Kostenstellendaten." : "Erstellen Sie eine neue Kostenstelle."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="kst-name">Name</Label>
              <Input id="kst-name" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="z.B. Fussball Spielbetrieb" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kst-beschreibung">Beschreibung</Label>
              <Input id="kst-beschreibung" value={formBeschreibung} onChange={(e) => setFormBeschreibung(e.target.value)} placeholder="Optionale Beschreibung" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="kst-abteilung">Abteilung</Label>
              <Select value={formAbteilung} onValueChange={setFormAbteilung}>
                <SelectTrigger id="kst-abteilung">
                  <SelectValue placeholder="Abteilung wählen" />
                </SelectTrigger>
                <SelectContent>
                  {abteilungen.map((a) => (
                    <SelectItem key={a.id} value={a.name}>{a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="kst-budget">Budget (EUR)</Label>
                <Input id="kst-budget" type="number" step="0.01" min="0" value={formBudget} onChange={(e) => setFormBudget(e.target.value)} placeholder="0,00" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kst-freigabelimit">Freigabelimit (EUR)</Label>
                <Input id="kst-freigabelimit" type="number" step="0.01" min="0" value={formFreigabelimit} onChange={(e) => setFormFreigabelimit(e.target.value)} placeholder="0,00" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Abbrechen</Button>
            <Button onClick={handleSave} disabled={!formName.trim()}>Speichern</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Kostenstelle löschen</DialogTitle>
            <DialogDescription>
              Möchten Sie die Kostenstelle &quot;{deleting?.name}&quot; wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Abbrechen</Button>
            <Button variant="destructive" onClick={handleDelete}>Löschen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

// --- Main Page ---

export function VereinsSetupPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Vereins-Setup"
        description="Grundeinstellungen des Vereins verwalten."
      />

      <Tabs defaultValue="abteilungen">
        <TabsList>
          <TabsTrigger value="abteilungen">Abteilungen</TabsTrigger>
          <TabsTrigger value="beitragskategorien">Beitragskategorien</TabsTrigger>
          <TabsTrigger value="kostenstellen">Kostenstellen</TabsTrigger>
          <TabsTrigger value="stammdaten">Stammdaten</TabsTrigger>
        </TabsList>

        <TabsContent value="abteilungen">
          <AbteilungenTab />
        </TabsContent>

        <TabsContent value="beitragskategorien">
          <BeitragskategorienTab />
        </TabsContent>

        <TabsContent value="kostenstellen">
          <KostenstellenTab />
        </TabsContent>

        <TabsContent value="stammdaten">
          <VereinsstammdatenForm />
        </TabsContent>
      </Tabs>
    </div>
  )
}
