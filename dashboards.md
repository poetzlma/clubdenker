# VereinsOS Dashboard — Design Specification
### Bauanleitung für den Nachbau · Stand März 2026

---

## 1. Designphilosophie & Ästhetik

### Gesamtcharakter
Das Dashboard ist **dark, dicht, professionell** — kein Consumer-App-Look, sondern ein Admin-Tool das Kompetenz ausstrahlt. Die Ästhetik orientiert sich an modernen Developer-Tools (Linear, Vercel, Raycast): minimaler Chrome, maximale Informationsdichte, keine dekorativen Elemente die nichts bedeuten.

### Kernprinzipien
- **Kontext schlägt Navigation** — die wichtigste Information der aktuellen Rolle steht immer oben
- **Farbe bedeutet etwas** — jede Sparte hat eine eigene Farbe, die konsistent durch alle Charts, Badges und Akzente läuft
- **Live-Indikatoren sind sparsam** — nur der Puls-Dot und die Uhr sind wirklich animiert, alles andere ist ruhig
- **Kein Whitespace-Padding-Overload** — Cards sind kompakt, Abstände sind 12px (klein) oder 20px (groß), nie mehr

---

## 2. Design Tokens (CSS-Variablen / Style-System)

### Farben

```css
/* Hintergründe */
--bg-base:        #0f1117;   /* Seitengrund */
--bg-card:        rgba(255,255,255,0.04);  /* Card-Hintergrund */
--bg-hover:       rgba(255,255,255,0.06);
--bg-active:      rgba(255,255,255,0.10);

/* Borders */
--border-subtle:  rgba(255,255,255,0.07);
--border-card:    rgba(255,255,255,0.08);
--border-strong:  rgba(255,255,255,0.12);

/* Text */
--text-primary:   #f9fafb;
--text-secondary: #e5e7eb;
--text-muted:     #9ca3af;
--text-faint:     #6b7280;

/* Semantische Farben */
--color-success:  #10b981;
--color-warning:  #f59e0b;
--color-danger:   #ef4444;
--color-info:     #3b82f6;
--color-purple:   #a855f7;

/* Sparten-Farben (konsistent überall) */
--sparte-fussball:     #3b82f6;   /* Blau */
--sparte-tennis:       #f59e0b;   /* Amber */
--sparte-fitness:      #10b981;   /* Grün */
--sparte-leichtathletik: #a855f7; /* Lila */
```

### Schrift

```css
font-family: 'DM Sans', system-ui, sans-serif;
/* Monospace für Zahlen/Uhrzeit: */
font-family: 'DM Mono', monospace;

/* Größen */
--text-xs:   10px;
--text-sm:   11px;
--text-base: 12px;
--text-md:   13px;
--text-lg:   16px;
--text-xl:   22px;
--text-2xl:  28px;
--text-3xl:  36px;

/* Wichtig: Zahlen immer mit font-variant-numeric: tabular-nums */
```

### Spacing & Radius

```css
--gap-xs:   4px;
--gap-sm:   8px;
--gap-md:   12px;
--gap-lg:   20px;
--gap-xl:   24px;
--gap-2xl:  32px;

--radius-sm:  4px;
--radius-md:  8px;
--radius-lg:  12px;
```

---

## 3. Layout-Struktur (Gesamtseite)

```
┌──────────────────────────────────────────────────────────────┐
│  TOP NAV (sticky, 56px hoch, blur-backdrop)                  │
│  [Logo] [View Switcher: Vorstand | Schatzmeister | Sparten]  │
│                                  [Puls-Dot + Uhrzeit] [Info] │
├──────────────────────────────────────────────────────────────┤
│  PAGE HEADER (24px oben, 16px unten padding)                 │
│  Seitentitel (22px bold)    Datum (12px muted)               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CONTENT AREA (padding: 24px 32px)                           │
│  → Wechselt je nach aktivem View (siehe Section 4–6)        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Top Navigation
- **Position:** `sticky top:0`, `z-index: 100`
- **Hintergrund:** `rgba(15,17,23,0.92)` + `backdrop-filter: blur(12px)` → Glaseffekt beim Scrollen
- **Border-Bottom:** `1px solid rgba(255,255,255,0.07)`
- **Höhe:** 56px
- **Layout:** 3-spaltig: Logo links · View-Switcher Mitte · Status rechts

**Logo-Block (links):**
- 32×32px Square, `border-radius: 8px`, `background: linear-gradient(135deg, #3b82f6, #6366f1)`
- Buchstabe "V" in weiß, 16px, bold
- Vereinsname 13px/700, Untertitel 10px muted in Caps + Spacing

**View-Switcher (Mitte):**
- Container: `background: rgba(255,255,255,0.05)`, `border-radius: 10px`, `padding: 3px`, `border: 1px solid rgba(255,255,255,0.07)`
- Aktiver Tab: `background: rgba(255,255,255,0.1)`, Text weiß, 600 weight
- Inaktiver Tab: transparenter Hintergrund, Text muted, 400 weight
- Jeder Tab hat ein Icon-Glyph (◈ ◇ ◉) + Label

**Status-Block (rechts):**
- Puls-Dot: animierter grüner Kreis (siehe Animation-Section)
- Uhrzeit in DM Mono, `font-variant-numeric: tabular-nums`, Sekunden sichtbar
- Vertikaler Divider: 1px, 16px hoch
- Vereinsname + Mitgliederzahl

---

## 4. Wiederverwendbare Komponenten

### 4.1 KPI Card

```
┌─────────────────────────────┐
│▓▓▓▓▓░░░░░░░░░░░░░░░░░  ← 2px Gradient-Top-Border (Akzentfarbe)
│                             │
│ LABEL (11px CAPS muted)     │
│ 36px Bold Zahl              │
│ ↑ 1.8%  sub-Text (12px)    │
└─────────────────────────────┘
```

- **Hintergrund:** `rgba(255,255,255,0.04)`
- **Border:** `1px solid rgba(255,255,255,0.08)`
- **Radius:** 12px
- **Padding:** 16–20px horizontal, 16–20px vertikal (large variant: 20px 24px)
- **Top-Akzentlinie:** `position: absolute`, `top: 0`, `height: 2px`, `background: linear-gradient(90deg, {farbe}80, transparent)` → subtiler Farbeinschlag
- **Trend-Badge:** grüner/roter Chip mit Pfeil, `font-size: 12px`, `border-radius: 4px`

### 4.2 Section Header

Einfache Zeile über jedem Chart-Block:
- Links: Label 13px, 600 weight, `color: #d1d5db`
- Rechts (optional): Action-Link 11px muted, cursor pointer

### 4.3 Progress Bar

```
[▓▓▓▓▓▓▓▓░░░░]  ← 6px hoch, border-radius: 3px
```
- Track: `rgba(255,255,255,0.08)`
- Fill: Spartenfarbe oder Gradient bei >85% (`#f59e0b → #ef4444`)
- Transition: `width 0.6s ease`

### 4.4 Mahnstufen-Badge

```
M1  ← amber    M2  ← rot    M3  ← dunkelrot
```
- `font-size: 11px`, `font-weight: 700`
- Jede Stufe hat eigene Vorder- und Hintergrundfarbe (siehe Tokens)
- `border-radius: 4px`, `padding: 2px 7px`

### 4.5 Sparten-Chip

Kleines Farbchip für Tabellenzeilen:
- `font-size: 11px`, Spartenfarbe als Text
- Hintergrund: `{spartenfarbe}18` (sehr transparent)
- `border-radius: 4px`, `padding: 2px 6px`

### 4.6 Aktions-Karte (Alert-ähnlich)

```
┌──────────────────────────────────────────┐
│ 🔔  Text der Aktion / des Alerts         │
└──────────────────────────────────────────┘
```
Drei Varianten:
- **action** (blau): `background: rgba(59,130,246,0.1)`, `border: rgba(59,130,246,0.2)`
- **warn** (amber): `background: rgba(245,158,11,0.08)`, `border: rgba(245,158,11,0.15)`
- **ok** (grün): `background: rgba(16,185,129,0.06)`, `border: rgba(16,185,129,0.1)`

### 4.7 Puls-Dot (Live-Indikator)

```css
/* Zwei überlagerte Kreise: äußerer pulsiert weg, innerer bleibt */
.pulse-outer {
  position: absolute; inset: 0;
  border-radius: 50%;
  background: #10b981;
  opacity: 0.4;
  animation: pulse 2s ease-in-out infinite;
}
.pulse-inner {
  position: absolute; inset: 2px;
  border-radius: 50%;
  background: #10b981;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.4; }
  50%       { transform: scale(2.2); opacity: 0; }
}
```

---

## 5. View 1 — Vorstand (Strategischer Überblick)

### Grid-Layout (von oben nach unten)

```
┌──────────┬──────────┬──────────┬──────────┐
│ KPI      │ KPI      │ KPI      │ KPI      │  → 4-spaltig, gap 12px
│ Mitglieder│ Kasse   │ Offene  │ Compliance│
└──────────┴──────────┴──────────┴──────────┘

┌──────────────────────────┬───────────────┐
│ Mitgliederentwicklung    │ Sparten-      │  → 2fr / 1fr
│ Stacked Area Chart       │ gesundheit    │
│ 12 Monate                │ Progress Bars │
└──────────────────────────┴───────────────┘

┌──────────────────────┬────────────────────┐
│ Cashflow Bar Chart   │ Offene Aktionen    │  → 1.5fr / 1fr
│ 6 Monate             │ Alert-Karten       │
└──────────────────────┴────────────────────┘
```

### Chart 1: Mitgliederentwicklung (Stacked Area)
- **Typ:** `AreaChart` mit 4 gestackten `Area`-Komponenten (stackId="1")
- **Daten:** 12 Monatspunkte, je Sparte ein Wert + Gesamttotal
- **Farben:** Spartenfarben mit `linearGradient` Fill (30% → 0% opacity von oben nach unten)
- **Achsen:** Y-Axis Domain `[550, 750]`, beide Achsen ohne Linien (`axisLine={false} tickLine={false}`)
- **Höhe:** 180px
- **Besonderheit:** Die Mitgliederzahl im KPI-Card tickt live (alle 3 Sekunden ±1 mit 15% Wahrscheinlichkeit → simuliert realtime)

### Chart 2: Spartengesundheit (Progress Bars, kein Chart)
- Für jede Sparte: Name + Prozentzahl + Progress Bar + "genutzt von Budget"-Text
- Die Farbe der Bar = Spartenfarbe
- Warnung wenn > 85%: Bar wechselt auf Amber→Rot-Gradient

### Chart 3: Cashflow (Grouped Bar Chart)
- **Typ:** `BarChart`, zwei `Bar`-Komponenten nebeneinander
- Einnahmen: `#10b981` (grün), Ausgaben: `#ef4444` mit `opacity: 0.7`
- `barGap={2}`, Radius oben: `[3,3,0,0]`
- Y-Achse: Format `Xk` (Tausender)
- Höhe: 140px

### Offene Aktionen
- Hardcodierte Alert-Karten (3–5 Einträge)
- Sortierung: action > warn > ok
- Kein Chart, reine Text-Karten mit Icon + Beschreibung

---

## 6. View 2 — Schatzmeister (Finanzoperationen)

### Grid-Layout

```
┌──────────────────────────────────────────────────┐
│ SEPA HERO-BLOCK (volle Breite, blauer Akzent)   │  → 1 Spalte
│ Titel + Betrag + Fortschrittsbalken + 2 Buttons  │
└──────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┬──────────┐
│ KPI Kasse│ KPI      │ KPI Off. │ KPI      │  → 4-spaltig
│ Ideell   │ Zweckbet.│ Forder.  │ Überw.   │
└──────────┴──────────┴──────────┴──────────┘

┌──────────────────────────┬───────────────┐
│ Offene Posten (Tabelle)  │ Budget Burn   │  → 1.5fr / 1fr
│                          │ Horizontal Bar│
└──────────────────────────┴───────────────┘

┌──────────────────────────────────────────────────┐
│ Liquiditätschart (Area, volle Breite)            │
└──────────────────────────────────────────────────┘
```

### SEPA Hero-Block
- **Hintergrund:** `linear-gradient(135deg, rgba(59,130,246,0.15), rgba(59,130,246,0.05))`
- **Border:** `1px solid rgba(59,130,246,0.25)`
- **Layout:** 2-spaltig (Text links, Buttons rechts)
- **Titel:** 12px CAPS blau, "SEPA Q2/2026 — Bereit zur Freigabe"
- **Betrag:** 32px bold weiß
- **Sub-Text:** Anzahl ready / total + Ausnahmen
- **Progress Bar:** darunter, zeigt Readiness
- **Buttons:** Primär (blau solid "Freigabe erteilen →") + Sekundär (transparent mit blauem Border)

### Offene Posten Tabelle
Spalten: Mitglied · Sparte · Betrag · Tage · Mahnstufe · Action

- **Sparte:** als Farbchip (Sparten-Chip Komponente)
- **Betrag:** `font-variant-numeric: tabular-nums`
- **Tage:** Farbe je nach Alter — >45d rot, sonst amber
- **Mahnstufe:** Mahnstufen-Badge Komponente
- **Action:** "Mahnen →" als Text-Link rechts
- Header-Row: 11px CAPS muted, `border-bottom: 1px solid rgba(255,255,255,0.06)`
- Zeilen: `border-bottom: 1px solid rgba(255,255,255,0.04)`

### Budget Burn (Horizontal Bar Chart)
- **Typ:** `BarChart` mit `layout="vertical"`, `barSize={12}`
- Y-Axis: Spartenname (90px width), X-Axis: Beträge in k
- Jeder Bar bekommt die Spartenfarbe via `<Cell>` Komponente
- Radius: `[0,3,3,0]` (rechts abgerundet)
- Darunter: kleine 2×2 Grid mit Prozentwerten je Sparte

### Liquiditätschart (Doppel-Area)
- Einnahmen: grüne Area, Ausgaben: rote Area (nicht gestackt, überlagert)
- Beide mit `linearGradient` Fill
- Höhe: 130px
- Rechts oben: "EÜR generieren →" Action-Link

---

## 7. View 3 — Spartenleiter

### Sparten-Switcher (ganz oben)

```
[Fußball]  [Tennis]  [Fitness]  [Leichtathletik]
```
- Aktiver Button: `border-color: {spartenfarbe}`, `background: {spartenfarbe}20`, Text in Spartenfarbe
- Inaktiver Button: `border: rgba(255,255,255,0.1)`, Text muted
- **Wichtig:** Alle Charts und KPIs reagieren auf den aktiven Sparten-State

### Grid-Layout

```
[ Sparten-Switcher ]

┌──────────┬──────────┬──────────┬──────────┐
│ Mitglieder│ Ø Anw.  │ Budget   │ Risiko   │  → 4 KPI Cards
└──────────┴──────────┴──────────┴──────────┘

┌──────────────────────┬─────────────────────┐
│ Anwesenheit Heatmap  │ Trainings nächste  │  → 1fr / 1fr
│ (GitHub-Style)       │ Woche               │
└──────────────────────┴─────────────────────┘

┌──────────────────────┬─────────────────────┐
│ Risiko-Mitglieder    │ Budget Donut        │  → 1fr / 1fr
└──────────────────────┴─────────────────────┘
```

### Anwesenheits-Heatmap (GitHub-Contribution-Style)
- **7 Zeilen** (Mo–So), **12 Spalten** (Wochen)
- Jede Zelle: 20×20px, `border-radius: 3px`, `border: 1px solid rgba(255,255,255,0.06)`
- **4 Füllstufen:** transparent → 20% → 50% → 85% der Spartenfarbe
  ```
  Stufe 0 (keine Daten/WE): rgba(255,255,255,0.03)
  Stufe 1 (wenig):           rgba(59,130,246,0.20)
  Stufe 2 (mittel):          rgba(59,130,246,0.50)
  Stufe 3 (viel):            rgba(59,130,246,0.85)
  ```
- Wochenende-Zeilen (Sa/So): immer Stufe 0
- Legende darunter: "Wenig ■ ■ ■ Viel" mit 14×14px Farbboxen
- **Zeilenbezeichnungen:** 24px breit, 10px muted, rechts-aligned

### Trainings-Wochenübersicht
Für jedes Training eine Zeile als Card:
- **Layout:** 4-spaltig → Wochentag (30px) · Uhrzeit (50px) · Name+Trainer (flex) · Auslastung (auto)
- **Auslastungsfarbe:** >90% rot · >70% amber · sonst grün
- Angemeldete/Max als "14/18", darunter Prozentzahl
- Card-Style: `background: rgba(255,255,255,0.03)`, `border: 1px solid rgba(255,255,255,0.06)`

### Risiko-Mitglieder
Cards mit rotem Akzent:
- `background: rgba(239,68,68,0.05)`, `border: 1px solid rgba(239,68,68,0.12)`
- Name (13px bold) + "Letztes Training: Datum" (11px muted)
- Rechts: Anzahl Tage in Rot + optional "Beitrag offen" Amber-Badge

### Budget Donut (Pie Chart)
- **Typ:** `PieChart` mit `Pie`, `innerRadius: 52`, `outerRadius: 72`
- 3 Segmente: Genutzt (Spartenfarbe, voll) · Committed (Spartenfarbe 50% opacity) · Frei (rgba weiß 0.08)
- Darunter 3-spaltiges Grid: Betrag + Label je Segment
- Kein Recharts-Label direkt im Donut → externes Label-Grid ist sauberer

---

## 8. Chart-Styling (gilt global für alle Recharts)

### Custom Tooltip
Einheitlicher Tooltip für alle Charts:
```jsx
background:    #1f2937
border:        1px solid rgba(255,255,255,0.1)
border-radius: 8px
padding:       10px 14px
font-size:     12px
Header:        color #9ca3af, font-weight 600
Values:        color = jeweilige Chart-Farbe, bold, tabular-nums
```

### Achsen (CartesianGrid, XAxis, YAxis)
```jsx
CartesianGrid: strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)"
XAxis/YAxis:   tick={{ fill: "#6b7280", fontSize: 11 }}
               axisLine={false} tickLine={false}
```

### Gradient-Fills (für Area Charts)
```jsx
<defs>
  <linearGradient id="gradientId" x1="0" y1="0" x2="0" y2="1">
    <stop offset="5%"  stopColor={farbe} stopOpacity={0.3} />
    <stop offset="95%" stopColor={farbe} stopOpacity={0}   />
  </linearGradient>
</defs>
```

---

## 9. Animations & Interaktionen

### Puls-Dot (einzige echte Animation)
```css
@keyframes pulse {
  0%, 100% { transform: scale(1);   opacity: 0.4; }
  50%       { transform: scale(2.2); opacity: 0;   }
}
```

### State-Transitions (CSS)
- Tab-Buttons: `transition: all 0.15s`
- Progress Bars: `transition: width 0.6s ease`
- Cards: kein Hover-Effekt (zu busy bei Datendichte), nur Buttons haben Cursor-Pointer

### Live Clock
React-State mit `setInterval(1000ms)`, zeigt `HH:MM:SS` in DM Mono.

### Live Mitgliederzähler
React-State, alle 3 Sekunden Event: `Math.random() > 0.85` → ±1 Mitglied.
Simuliert WebSocket-Daten-Push.

---

## 10. Datenschicht & Mock-Daten Struktur

### Mitgliedertrend
```typescript
type TrendDataPoint = {
  m: string;           // Monatsname "Jan"–"Dez"
  total: number;       // Gesamtmitglieder
  Fußball: number;
  Tennis: number;
  Fitness: number;
  Leichtathletik: number;
}
// 12 Einträge (rollierend letztes Jahr)
```

### Cashflow
```typescript
type CashflowPoint = {
  m: string;    // Monat
  ein: number;  // Einnahmen (EUR)
  aus: number;  // Ausgaben (EUR)
}
// 6 Einträge (letztes Halbjahr)
```

### Offene Posten
```typescript
type OffenerPosten = {
  name: string;
  sparte: "Fußball" | "Tennis" | "Fitness" | "Leichtathletik";
  betrag: number;
  tage: number;  // Überfälligkeitstage
  stufe: 1 | 2 | 3;  // Mahnstufe
}
```

### Trainingsplan
```typescript
type Training = {
  tag: string;        // "Mo"–"Fr"
  zeit: string;       // "18:30"
  gruppe: string;     // Gruppenname
  trainer: string;
  angemeldet: number;
  max: number;
}
```

### Risiko-Mitglieder
```typescript
type RisikoMitglied = {
  name: string;
  letztes: string;    // Datum des letzten Trainings
  tage: number;       // Tage seit letztem Training
  beitrag: "ok" | "offen";
}
```

---

## 11. Technischer Setup (Minimal)

```bash
npm create vite@latest vereins-dashboard -- --template react
cd vereins-dashboard
npm install recharts
# DM Sans + DM Mono via Google Fonts (im CSS-Import)
```

**App.jsx Grundstruktur:**
```jsx
// State: activeView = "vorstand" | "schatzmeister" | "spartenleiter"
// State: activeSparte = "Fußball" | "Tennis" | "Fitness" | "Leichtathletik"
// State: liveMitglieder (tickt jede 3s)
// State: time (tickt jede 1s)

// Top-Level Layout:
// <TopNav /> (sticky)
// <PageHeader title={...} />
// <ContentArea>
//   {activeView === "vorstand" && <VorstandDashboard />}
//   {activeView === "schatzmeister" && <SchatzmeisterDashboard />}
//   {activeView === "spartenleiter" && <SpartenleiterdDashboard />}
// </ContentArea>
```

**Komponenten-Dateien empfohlen:**
```
src/
├── components/
│   ├── KpiCard.jsx
│   ├── ProgressBar.jsx
│   ├── SectionHeader.jsx
│   ├── MahnstuftBadge.jsx
│   ├── SpartenChip.jsx
│   ├── AktionsKarte.jsx
│   ├── PulseDot.jsx
│   ├── LiveClock.jsx
│   └── ChartTooltip.jsx
├── views/
│   ├── VorstandDashboard.jsx
│   ├── SchatzmeisterDashboard.jsx
│   └── SpartenleiterdDashboard.jsx
├── data/
│   └── mockData.js     ← alle Arrays ausgelagert
├── constants/
│   └── design.js       ← SPARTEN_COLORS, TOKENS etc.
└── App.jsx
```

---

## 12. Wichtigste Implementierungshinweise

1. **Alle Farb-Konstanten zentral** in `constants/design.js` — nie inline hardcoden außer in der KpiCard-Top-Border (die bekommt die Farbe als Prop)

2. **ResponsiveContainer** von Recharts immer mit `width="100%"` und fixer `height` (nie `height="100%"` — bricht in Flex-Containern)

3. **Sparten-Switcher State** in `SpartenleiterdDashboard` lokal halten — andere Views brauchen ihn nicht

4. **Heatmap ist kein Chart** — einfaches CSS-Grid mit 7 Zeilen × 12 Spalten, jede Zelle ein `div` mit bedingter Hintergrundfarbe. Kein Recharts nötig.

5. **SEPA Hero-Block** ist eine normale Card mit `position: relative` — kein spezieller Component-Typ. Der Primär-Button hat `onClick` der einen HITL-Workflow triggern würde (in der Demo kein Handler nötig)

6. **Custom Tooltip** als separate Komponente definieren und an alle Charts via `content={<ChartTooltip />}` übergeben — so ist er überall gleich

7. **font-variant-numeric: tabular-nums** überall wo Zahlen stehen die sich ändern (Uhrzeit, Beträge, Zähler) — verhindert Layout-Shifts wenn Ziffern wechseln

---

*VereinsOS Design Spec v1.0 · Für Wiederverwendung und Anpassung freigegeben*