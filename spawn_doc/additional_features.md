# Agentic Vereinsverwaltung — Implementierungs-Roadmap
### Mehrsparten-Sportverein (300–1.000 Mitglieder) | Vorstand & Spartenleiter als primäre User

---

## Architektur-Prinzipien (gelten für alle Phasen)

- **MCP-First**: Jedes Feature wird zuerst als MCP-Tool gebaut, die Web-UI ist ein Consumer dieser Tools
- **Rollenmodell von Anfang an**: Vorstand → Spartenleiter → Mannschaftsverantwortlicher — nie nachträglich einbauen
- **HITL bei destruktiven Aktionen**: Finanzielle Aktionen > €50, Massenmails, Kündigungen immer mit Freigabe
- **Verbandsportale als externe Source-of-Truth**: DFBnet, click-TT nicht ersetzen, nur anbinden
- **DSGVO & SKR42 von Tag 1**: Keine technischen Schulden bei Compliance

---

## Phase 1 — MVP: Kern-Verwaltung (Monate 1–3)

> **Ziel:** Der Vorstand kann den Verein vollständig verwalten. Kein Excel mehr für Mitglieder und Beiträge.

### 1.1 Datenmodell & Backend

- [ ] Datenbankschema: `mitglieder`, `abteilungen`, `mitgliedschaft` (n:m), `beitragskategorien`
- [ ] Authentifizierung & Rollenmodell (Vorstand / Spartenleiter / Lese-Zugriff)
- [ ] REST-API mit OpenAPI-Spec (Basis für MCP-Adapter und Web-UI)
- [ ] Audit-Log-Tabelle (wer hat was wann geändert)
- [ ] DSGVO-Grundlage: Einwilligungsmanagement, Löschfristen-Flags

### 1.2 MCP-Server (Phase 1 Tools)

| Tool | Beschreibung | HITL |
|------|-------------|------|
| `mitglied_anlegen` | Neues Mitglied mit Stammdaten + Abteilungszuordnung | Nein |
| `mitglied_aktualisieren` | Adresse, Bankverbindung, Beitragskategorie ändern | Nein |
| `mitglied_suchen` | Volltextsuche, Filter nach Abteilung/Status/Alter | Nein |
| `mitglied_details` | Vollständiges Profil inkl. Beitragshistorie | Nein |
| `mitglied_kuendigen` | Austritt mit Kündigungsfrist-Prüfung lt. Satzung | **Ja** |
| `beitraege_berechnen` | Fällige Beiträge inkl. Rumpfbeiträge + Kombinationsrabatte | Nein |
| `nachricht_senden` | E-Mail an Mitglied oder Gruppe | **Ja (Massen)** |
| `dokument_generieren` | Beitrittserklärung, SEPA-Mandat als PDF | Nein |
| `datenschutz_auskunft` | DSGVO Art. 15 Auskunft für ein Mitglied | Nein |

**MCP Resources (Phase 1):**
```
sportverein://satzung
sportverein://beitragsordnung
sportverein://abteilungen
sportverein://mitglieder/statistik
```

### 1.3 Web-UI (Phase 1)

- [ ] **Mitgliederliste** — filterbare Tabelle (Tanstack Table), Spalten konfigurierbar
- [ ] **Mitgliederprofil** — Stammdaten, Abteilungen, Beitragshistorie, Dokumente
- [ ] **Schnell-Onboarding-Formular** — für Neumitglieder am Infostand (ohne KI, Formular-basiert)
- [ ] **Chat-Sidebar** — Claude/GPT via MCP, kontextbewusst je nach aktueller Seite

### 1.4 Erster Cron-Agent: Beitragseinzug

```
Monatlich (1. des Monats):
1. beitraege_berechnen() → Übersicht fälliger Beiträge
2. Mitglieder ohne SEPA-Mandat identifizieren → Erinnerung senden [HITL]
3. SEPA-XML vorbereiten → Schatzmeister zur Freigabe vorlegen [HITL]
4. Nach Freigabe: Vorabankündigungen versenden
5. Buchungsvorschlag für SKR42 generieren [HITL]
```

### 1.5 Definition of Done Phase 1

- Alle Mitgliederdaten aus Excel migriert
- Beitragseinzug läuft ohne Excel
- Vorstand kann alle Abfragen per Chat stellen
- DSGVO-Auskunft auf Anfrage in < 2 Minuten

---

## Phase 2 — Finanzen & Multi-Sparten (Monate 4–5)

> **Ziel:** Schatzmeister hat vollständige Kontrolle. Jede Sparte kennt ihr Budget. Kein Finanzamt-Stress.

### 2.1 Kostenstellenrechnung

- [ ] Kostenstellen-Tabelle: eine pro Sparte + Gesamtverein + Infrastruktur
- [ ] Buchungen immer mit Kostenstelle + steuerlicher Sphäre (ideell / Zweckbetrieb / Vermögensverwaltung / wirtschaftlicher Geschäftsbetrieb)
- [ ] Interne Leistungsverrechnung (Hallenbelegung → Schlüsselung auf Sparten)
- [ ] Spartenbudgets mit Freigabelimits (konfigurierbar je Sparte)

### 2.2 Neue MCP-Tools (Finanzen)

| Tool | Beschreibung | HITL |
|------|-------------|------|
| `sepa_xml_generieren` | SEPA pain.008, Vorabankündigung inklusive | **Ja** |
| `rechnung_erstellen` | Einzelrechnung / Sammelrechnung als PDF | Nein |
| `zahlung_verbuchen` | Zahlung Mitglied/Rechnung zuordnen | Nein |
| `buchung_anlegen` | SKR42-Buchungssatz, Sphäre + Kostenstelle | Nein |
| `mahnlauf_starten` | 3-stufige Mahnung, überfällige Identifikation | **Ja** |
| `spendenbescheinigung` | Zuwendungsbestätigung nach amtl. Muster | Nein |
| `finanzbericht` | EÜR, Kassenbericht, Beitragsstatistik je Sparte | Nein |
| `budget_pruefen` | Restbudget einer Kostenstelle abfragen | Nein |
| `aufwandsentschaedigung` | Übungsleiter-/Ehrenamtspauschale tracken + Grenzen prüfen | Nein |

### 2.3 Kombinationsbeiträge

- [ ] Beitragsformel-Engine: `Grundbeitrag + Σ(Spartenbeiträge) × Rabattfaktor`
- [ ] Rabattstaffelungen: Jugend, Familie (2+ Mitglieder gleicher Adresse), Mehrsparten
- [ ] Rumpfbeitrags-Berechnung bei unterjährigem Eintritt / Austritt
- [ ] Beitragskategorie-Wechsel mit Stichtagsberechnung

### 2.4 Web-UI (Phase 2)

- [ ] **Finanz-Dashboard** — Kassenstand je Sphäre, offene Posten, Spartenbudgets als Balken
- [ ] **Zahlungsübersicht** — Status-Tabelle (bezahlt / offen / überfällig / gemahnt), Bulk-Aktionen
- [ ] **Buchungsjournal** — filterbares Log aller Buchungen mit Kostenstellenansicht

### 2.5 Neue Agenten

**Mahnwesen-Agent** (Event-getrieben, Trigger: Zahlung 30 Tage überfällig):
```
1. Mahnhistorie prüfen (Stufe 1/2/3)
2. Nächste Mahnung generieren
3. Bei Stufe 3: Vorstand benachrichtigen + Empfehlung [HITL]
```

**Aufwandsentschädigungs-Monitor** (monatlich):
```
1. Alle Ehrenamtlichen mit §3-Nr.26 / §3-Nr.26a-Zahlungen abfragen
2. Hochrechnung auf Jahresende
3. Warnung wenn > 80% der Steuerfreigrenze erreicht
```

---

## Phase 3 — Spartenleiter & Ressourcen (Monate 6–7)

> **Ziel:** Spartenleiter sind self-sufficient. Vorstand hat Überblick ohne Micromanagement.

### 3.1 Rollenmodell schärfen

- [ ] Spartenleiter-Rolle: Schreibzugriff nur auf eigene Sparte, Budget nur bis Freigabelimit
- [ ] Mannschaftsverantwortlicher-Rolle: nur Anwesenheit + interne Kommunikation
- [ ] Row-Level Security in DB: Datenbankabfragen respektieren Spartenkontext automatisch
- [ ] MCP-Server gibt je nach Token nur die erlaubten Tools zurück (`capabilities` per Rolle)

### 3.2 Training & Anwesenheit

- [ ] Trainings-Tabelle mit Wiederholungsregeln (RRULE-Standard)
- [ ] Anwesenheitserfassung: QR-Code je Training → Mitglied scannt per Smartphone
- [ ] Abwesenheitsmeldung: Mitglied meldet sich selbst ab (einfaches Link-Formular)
- [ ] Anwesenheitsstatistik je Mitglied + Sparte für Jahresbericht

### 3.3 Neue MCP-Tools (Betrieb)

| Tool | Beschreibung |
|------|-------------|
| `training_planen` | Wiederkehrendes Training, Trainer, Halle, Abteilung |
| `anwesenheit_erfassen` | Teilnehmerliste für ein Training |
| `abwesenheit_melden` | Mitglied meldet Fehlen für Termin |
| `ressource_buchen` | Halle/Platz/Raum reservieren |
| `ressource_konflikte` | Überschneidungen prüfen vor Buchung |
| `trainer_uebersicht` | Lizenzstatus, Qualifikationen je Trainer |

### 3.4 Hallenplanung (Web-UI, visuell zwingend)

- [ ] **Belegungskalender** — Wochenansicht, Spalten = Hallen/Plätze, farbcodiert nach Sparte
- [ ] Drag-and-Drop für Trainingsverschiebung
- [ ] Konflikt-Highlighting (rot wenn Überschneidung)
- [ ] Export als PDF für Aushang

### 3.5 Lizenz- und Zertifikat-Tracking

- [ ] Tabelle: `qualifikationen` (Mitglied, Typ, Ausstellungsdatum, Ablaufdatum, Dokument)
- [ ] Typen: Übungsleiter C/B/A, Trainer C/B/A, Erste-Hilfe, Sportabzeichen-Prüfer, etc.
- [ ] Monitor-Agent (monatlich): Ablauf in < 90 Tagen → Betroffener + Spartenleiter benachrichtigen

### 3.6 Spartenleiter Mobile-View

- [ ] Responsive Web-UI, optimiert für Smartphone
- [ ] Schnellzugriff: „Training heute" → Anwesenheit erfassen in < 30 Sekunden
- [ ] Push-Benachrichtigungen für Abwesenheitsmeldungen der Spieler

---

## Phase 4 — Verbandsanbindung & Spielbetrieb (Monate 8–9)

> **Ziel:** Kein manuelles Doppelpflegen zwischen Vereinssoftware und DFBnet/click-TT.

### 4.1 Sync-Layer Architektur

```
Vereinssoftware (Master)          Verbandsportal (extern)
────────────────────────          ──────────────────────
Mitgliedsdaten              →     Passantrag-Vorbereitung
Passnummer speichern        ←     Nach Passbeantragung
Spielberechtigung-Status    ←     Polling / Webhook
Spielplan importieren       ←     Saisonbeginn
Aufstellung vorbereiten     →     DFBnet-Upload-Hilfe
```

- [ ] Passnummer-Feld in Mitgliederprofil (DFBnet-ID, click-TT-ID)
- [ ] Spielberechtigung-Status als cached Feld (täglich aktualisiert)
- [ ] Spielplan-Import (CSV/API je nach Verband)

### 4.2 Neue MCP-Tools (Spielbetrieb)

| Tool | Beschreibung |
|------|-------------|
| `pass_status_pruefen` | Spielberechtigung eines Mitglieds lt. Verbandsportal |
| `aufstellung_vorbereiten` | Aufstellung für Spiel, prüft automatisch Sperren + Berechtigung |
| `spielplan_abfragen` | Nächste Spiele einer Mannschaft |
| `spielbericht_vorbereiten` | Formular für DFBnet/click-TT vorausfüllen |
| `passantrag_vorbereiten` | Daten für Passbeantragung zusammenstellen |

### 4.3 Agenten für Spielbetrieb

**Pre-Game-Agent** (Trigger: 48h vor Spieltermin):
```
1. Aufstellung aus Anwesenheitsmeldungen ableiten
2. Spielberechtigungen aller Spieler prüfen
3. Sperren-Status abfragen
4. Mannschaftsverantwortlichem Vorschlag-Aufstellung senden [HITL]
5. Fahrtkoordination-Hinweis wenn Auswärtsspiel
```

---

## Phase 5 — Strategische Vorstandsfeatures (Monate 10–12)

> **Ziel:** Vorstand trifft datenbasierte Entscheidungen. Fördermittel werden nicht liegen gelassen.

### 5.1 Mitgliederentwicklungs-Analytics

- [ ] Churn-Analyse: Wann kündigen Mitglieder? Welche Sparte hat höchste Abgangsrate?
- [ ] Altersverteilung je Sparte — Nachwuchsproblem früh erkennen
- [ ] Saisonalität: Eintritts- und Austrittsmuster (Neujahr, Sommer, etc.)
- [ ] Prognose: Mitgliederzahl in 12 Monaten bei aktuellem Trend

### 5.2 Fördermittelmanagement

- [ ] Fördermittel-Tabelle: Geber, Betrag, Zweck, Laufzeit, Verwendungsnachweis-Deadline
- [ ] Buchungen können Fördermittelposition zugeordnet werden
- [ ] Monitor-Agent: Verwendungsnachweis fällig in < 60 Tagen → Vorstand + Schatzmeister

**MCP-Tools:**

| Tool | Beschreibung |
|------|-------------|
| `foerdermittel_anlegen` | Neue Förderung mit Bedingungen erfassen |
| `foerdermittel_abrechnen` | Verwendungsnachweis-Bericht generieren |
| `foerdermittel_uebersicht` | Alle aktiven Förderungen mit Status |

### 5.3 Sponsoring-Verwaltung

- [ ] Sponsorenverträge: Laufzeit, Betrag, Gegenleistung (Trikot / Bande / Website / Veranstaltung)
- [ ] Steuerliche Einordnung: Sponsoring → wirtschaftlicher Geschäftsbetrieb (USt-pflichtig!)
- [ ] Monitor-Agent: Vertrag läuft in 90 Tagen ab → Verlängerungsangebot vorbereiten

### 5.4 Beschluss-Archiv

- [ ] Protokoll-Tabelle mit Tags (Finanzen, Personal, Infrastruktur, Satzung, ...)
- [ ] Beschlüsse als separate Entität mit Abstimmungsergebnis
- [ ] Volltextsuche über alle Protokolle per KI-Agent
- [ ] Resource: `sportverein://beschluesse` → Agent kann historische Entscheidungen erklären

**Beispiel-Abfrage via Chat:**
> „Was hat der Vorstand in den letzten 2 Jahren zu Hallenmiete beschlossen?"

### 5.5 Jahresabschluss-Agent (Cron, 31. Januar)

```
1. EÜR aller vier steuerlichen Sphären generieren
2. Beitragsstatistik für Jahresbericht zusammenstellen
3. Verwendungsnachweise aller abgelaufenen Fördermittel prüfen
4. Verbandsmeldung (DOSB/LSB) vorbereiten
5. Aufwandsentschädigungen: Jahresübersicht für Lohnsteuerbescheinigungen
6. Vollständigen Bericht für Mitgliederversammlung als PDF generieren [HITL]
```

---

## Phase 6 — Plattform & Ökosystem (ab Monat 13)

> **Ziel:** Andere Vereine können die Lösung nutzen. Multi-Mandanten-Fähigkeit.

### 6.1 Multi-Mandanten-Architektur

- [ ] Tenant-Isolation auf Datenbankebene (Schema per Verein oder Row-Level)
- [ ] Vereins-Konfiguration: Satzung, Beitragsordnung, Spartenstruktur individuell
- [ ] White-Label-Option für Verbände (LSB bietet es Mitgliedsvereinen an)

### 6.2 Mitglieder-Self-Service-Portal

- [ ] Mitglied kann eigene Stammdaten aktualisieren (Adresse, IBAN)
- [ ] Abwesenheitsmeldungen self-service
- [ ] Beitragsübersicht + Zahlungshistorie einsehen
- [ ] Austritt beantragen (löst Workflow aus, Spartenleiter wird informiert)

### 6.3 E-Rechnung (gesetzlich ab 2027 verpflichtend)

- [ ] XRechnung / ZUGFeRD-Format für alle B2B-Rechnungen
- [ ] Automatische Generierung bei Rechnungsstellung

### 6.4 Open Source MCP-Server

- [ ] MCP-Server als eigenständiges Open-Source-Paket veröffentlichen
- [ ] Jeder Verein kann beliebigen LLM-Provider anbinden (Anthropic, OpenAI, lokales Modell)
- [ ] Dokumentation: „Verbinde deinen Verein mit Claude Desktop in 15 Minuten"

---

## Feature-Matrix nach Phase

| Feature | P1 | P2 | P3 | P4 | P5 | P6 |
|---------|----|----|----|----|----|----|
| Mitgliederverwaltung | ✅ | | | | | |
| SEPA-Beitragseinzug | ✅ | | | | | |
| MCP-Server (Basis) | ✅ | | | | | |
| Chat-Sidebar Web-UI | ✅ | | | | | |
| SKR42-Buchhaltung | | ✅ | | | | |
| Multi-Sparten-Budget | | ✅ | | | | |
| Kombinationsbeiträge | | ✅ | | | | |
| Mahnwesen-Agent | | ✅ | | | | |
| Aufwandsentschädigungen | | ✅ | | | | |
| Rollenmodell vollständig | | | ✅ | | | |
| Hallenplanung (visuell) | | | ✅ | | | |
| Anwesenheit + QR-Code | | | ✅ | | | |
| Lizenz-Tracking | | | ✅ | | | |
| Spartenleiter Mobile | | | ✅ | | | |
| DFBnet/click-TT Sync | | | | ✅ | | |
| Spielbericht-Vorbereitung | | | | ✅ | | |
| Pre-Game-Agent | | | | ✅ | | |
| Mitglieder-Analytics | | | | | ✅ | |
| Fördermittel | | | | | ✅ | |
| Sponsoring | | | | | ✅ | |
| Beschluss-Archiv (KI-Suche) | | | | | ✅ | |
| Jahresabschluss-Agent | | | | | ✅ | |
| Multi-Mandanten | | | | | | ✅ |
| Self-Service-Portal | | | | | | ✅ |
| E-Rechnung (XRechnung) | | | | | | ✅ |
| Open Source MCP Release | | | | | | ✅ |

---

## Tech Stack Referenz

```‚‚‚
Frontend:     Vite + React 19 + shadcn/ui + Tanstack (Router, Query, Table)
Charts:       Recharts
MCP-Server:   FastMCP (Python) oder @modelcontextprotocol/sdk (TypeScript)
API:          FastAPI (Python) oder Hono (TypeScript) mit OpenAPI
Datenbank:    PostgreSQL + Prisma ORM
Auth:         Better Auth oder Lucia (OAuth 2.1 für MCP Remote)
Dokumente:    WeasyPrint (PDF) + Jinja2-Templates
SEPA:         python-sepaxml (pain.008.001.02)
Scheduler:    pg-cron (Datenbankebene) oder systemd-Timer
Storage:      MinIO (self-hosted S3 für Dokumente)
Hosting:      Hetzner VPS (DSGVO-konform, Deutschland)
```

---

*Erstellt: März 2026 — Agentic Vereinsverwaltung Konzept v1.0*
