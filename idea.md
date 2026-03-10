# Sportverein als MCP-Server: Ein Agentic-First-Konzept für das KI-Zeitalter

**Ein Vereinsverwaltungssystem, das als MCP-Server konzipiert ist, ermöglicht es KI-Assistenten wie Claude oder ChatGPT, direkt auf Vereinsdaten zu agieren — Mitglieder anlegen, Beiträge einziehen, Trainings planen und Dokumente generieren, alles per natürlicher Sprache.** Der entscheidende Paradigmenwechsel: Die primäre Schnittstelle ist nicht mehr ein Web-Dashboard, sondern ein KI-Agent, der über das Model Context Protocol (MCP) auf eine strukturierte Tool-Bibliothek zugreift. Die Web-Oberfläche wird zur spezialisierten Ergänzung für visuelle Aufgaben — Dashboards, Kalenderansichten, Zahlungsübersichten — statt der Standardinteraktionsfläche. Dieses Konzept beschreibt die konkrete Architektur, Tool-Definitionen und Agentic Workflows für eine solche Lösung.

---

## Warum aktuelle Vereinssoftware ein Agentic-Redesign braucht

Die Vereinsverwaltung in Deutschland leidet unter einem strukturellen Problem: **Ehrenamtliche mit begrenzter Zeit** müssen komplexe Software bedienen, die für hauptamtliche Verwaltungen designt wurde. Lösungen wie easyVerein, Campai, ClubDesk oder SEWOBE bieten umfangreiche Features — Mitgliederverwaltung, SEPA-Lastschrift, SKR42-Buchhaltung, Spendenbescheinigungen — aber die Interaktion bleibt klassisch: Login, Menü navigieren, Formular ausfüllen, Button klicken. Die Kernworkflows eines Sportvereins umfassen Mitglieder-Onboarding, Beitragseinzug mit SEPA-Mandaten, Trainingsplanung, Kommunikation, Finanzbuchhaltung in vier steuerlichen Sphären und Meldungen an Landessportbund und Finanzamt.

Die größten Schmerzpunkte sind bezeichnend: **Excel-Chaos** bei Vereinen ohne zentrale Software, **Wissenssilos** bei einzelnen Ehrenamtlichen, steile Lernkurven bei komplexen Tools wie SEWOBE, und fragmentierte Werkzeuge für verschiedene Aufgaben. Eine KI-native Lösung adressiert genau diese Probleme — der Schatzmeister sagt „Erstelle die SEPA-Datei für den Quartalsbeitrag" statt sich durch fünf Menüebenen zu klicken. Wichtig: Von den marktführenden Lösungen bietet nur **easyVerein eine vollständige REST-API** (v2.0), ClubDesk hat gar keine API. Das zeigt, wie wenig die Branche auf die Integration mit KI-Systemen vorbereitet ist.

---

## MCP-Server-Architektur: Konkrete Tool- und Resource-Definitionen

Das Model Context Protocol definiert drei Primitive: **Tools** (vom LLM aufgerufen, um Aktionen auszuführen), **Resources** (Daten, die als Kontext bereitgestellt werden) und **Prompts** (wiederverwendbare Vorlagen). Ein Sportverein-MCP-Server würde über Streamable HTTP (für Remote-Zugriff mit OAuth 2.1) oder stdio (für lokale Nutzung) kommunizieren und folgende Capabilities anbieten.

### Tools: Die Aktionsschnittstelle für den KI-Agenten

Jedes Tool folgt dem Prinzip **eine atomare Aktion pro Tool** mit JSON-Schema für Input und optionalem Output-Schema. Die Tool-Annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`) signalisieren dem LLM das Risikoprofil jeder Aktion.

**Mitgliederverwaltung (6 Tools):**

| Tool | Beschreibung | Annotations |
|------|-------------|-------------|
| `mitglieder_suchen` | Volltextsuche über Mitglieder mit Filtern (Abteilung, Status, Altersgruppe, Beitrittsdatum) | readOnly: true |
| `mitglied_details` | Stammdaten eines Mitglieds abrufen (inkl. Beiträge, Mandate, Abteilungen, Anwesenheit) | readOnly: true |
| `mitglied_anlegen` | Neues Mitglied registrieren mit Stammdaten, Abteilungszuordnung, Beitragskategorie | destructive: false |
| `mitglied_aktualisieren` | Stammdaten ändern (Adresse, Kontakt, Bankverbindung, Status) | idempotent: true |
| `mitglied_kuendigen` | Austritt einleiten mit Kündigungsdatum und Prüfung der Kündigungsfrist lt. Satzung | **destructive: true** |
| `mitglied_abteilung_zuordnen` | Mitglied einer oder mehreren Abteilungen zuweisen/entfernen | idempotent: true |

Konkret sieht das Tool `mitglied_anlegen` so aus:

```json
{
  "name": "mitglied_anlegen",
  "description": "Legt ein neues Vereinsmitglied an. Berechnet automatisch den Rumpfbeitrag bei unterjährigem Eintritt. Erfordert mindestens Name und E-Mail.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "vorname": { "type": "string", "description": "Vorname des Mitglieds" },
      "nachname": { "type": "string", "description": "Nachname des Mitglieds" },
      "email": { "type": "string", "format": "email" },
      "geburtsdatum": { "type": "string", "format": "date", "description": "YYYY-MM-DD" },
      "abteilungen": {
        "type": "array",
        "items": { "type": "string", "enum": ["fussball", "tennis", "turnen", "schwimmen"] },
        "description": "Abteilungszuordnung(en)"
      },
      "iban": { "type": "string", "description": "IBAN für SEPA-Mandat (optional bei Anlage)" },
      "beitragskategorie": {
        "type": "string",
        "enum": ["erwachsene", "jugend", "familie", "passiv", "ehrenmitglied"],
        "description": "Bestimmt den Beitragssatz"
      }
    },
    "required": ["vorname", "nachname", "email"]
  },
  "annotations": {
    "destructiveHint": false,
    "idempotentHint": false,
    "openWorldHint": false
  }
}
```

**Beitragsverwaltung und Finanzen (8 Tools):**

| Tool | Beschreibung | Kritisch |
|------|-------------|----------|
| `beitraege_berechnen` | Berechnet fällige Beiträge für einen Zeitraum mit Rumpfbeiträgen und Altersstaffelung | readOnly |
| `sepa_xml_generieren` | Erzeugt SEPA-XML-Lastschriftdatei für Beitragseinzug mit Vorabankündigung | **HITL erforderlich** |
| `rechnung_erstellen` | Einzelrechnung oder Sammelrechnung generieren (PDF) | — |
| `zahlung_verbuchen` | Eingehende Zahlung einem Mitglied/einer Rechnung zuordnen | — |
| `mahnlauf_starten` | Identifiziert überfällige Zahlungen und generiert Mahnungen (3 Stufen) | **HITL erforderlich** |
| `spendenbescheinigung_erstellen` | Zuwendungsbestätigung nach amtlichem Muster generieren | — |
| `finanzbericht_erstellen` | EÜR, Beitragsstatistik oder Kassenstand nach steuerlichen Sphären | readOnly |
| `buchung_anlegen` | Buchungssatz in SKR42 mit korrekter Sphärenzuordnung anlegen | — |

**Veranstaltungen und Training (5 Tools):**

| Tool | Beschreibung |
|------|-------------|
| `training_planen` | Wiederkehrendes Training anlegen (Wochentag, Uhrzeit, Trainer, Halle, Abteilung) |
| `veranstaltung_anlegen` | Einmalige Veranstaltung mit Anmeldung, Kapazitätslimit, Preis |
| `anwesenheit_erfassen` | Anwesenheit für ein Training oder Event erfassen (Teilnehmerliste) |
| `raum_buchen` | Halle/Platz/Raum für einen Zeitraum reservieren |
| `termine_abfragen` | Termine filtern nach Datum, Abteilung, Trainer, Ort |

**Kommunikation und Dokumente (4 Tools):**

| Tool | Beschreibung | Kritisch |
|------|-------------|----------|
| `nachricht_senden` | E-Mail an einzelne Mitglieder oder Gruppen (Abteilung, Beitragsstatus) | **HITL bei Massenmails** |
| `newsletter_erstellen` | Newsletter-Entwurf aus Template mit personalisierten Platzhaltern | HITL vor Versand |
| `dokument_generieren` | SEPA-Mandat, Beitrittserklärung, Vertrag aus Vorlage erzeugen (PDF) | — |
| `protokoll_anlegen` | Sitzungsprotokoll erstellen und im Dokumentenarchiv ablegen | — |

**Meldewesen und Compliance (3 Tools):**

| Tool | Beschreibung |
|------|-------------|
| `verbandsmeldung_exportieren` | Bestandserhebung für Landessportbund/DOSB im geforderten Format |
| `gemeinnuetzigkeit_pruefen` | Status des Freistellungsbescheids prüfen, nächsten Prüfungstermin anzeigen |
| `datenschutz_auskunft` | DSGVO-Auskunft für ein Mitglied zusammenstellen (Art. 15 DSGVO) |

### Resources: Kontextdaten für den KI-Agenten

Resources stellen dem LLM strukturierten Kontext bereit, ohne dass es aktiv Tools aufrufen muss. Über URI-Templates werden sie parametriert:

```
sportverein://mitglieder/{mitglied_id}         → Stammdaten eines Mitglieds
sportverein://abteilungen                       → Liste aller Abteilungen mit Leitung
sportverein://finanzen/kassenstand              → Aktueller Kassenstand nach Sphären
sportverein://satzung                           → Aktuelle Vereinssatzung als Kontext
sportverein://beitragsordnung                   → Beitragsstruktur und -kategorien
sportverein://termine/woche/{kw}                → Alle Termine einer Kalenderwoche
sportverein://mitglieder/statistik              → Mitgliederstatistik (Zu-/Abgänge, Altersverteilung)
```

Der entscheidende Vorteil: Wenn ein Vereinsvorstand fragt „Darf Maria Schmidt ihren Beitrag auf Familie umstellen?", kann das LLM die **Satzung und Beitragsordnung als Resource-Kontext laden** und die Frage auf Basis der tatsächlichen Vereinsregeln beantworten.

### Prompts: Vorgefertigte Workflows

```
/jahresabschluss          → Führt durch EÜR-Erstellung, Sphärentrennung, DATEV-Export
/mitgliederversammlung    → Erstellt Einladung, Tagesordnung, sammelt Vollmachten
/neues_mitglied           → Geführter Onboarding-Prozess mit allen Pflichtfeldern
/quartalsbeitrag          → Berechnung, SEPA-Datei, Vorabankündigung, Versand
```

---

## Agentic Workflows: Autonome Agenten im Vereinsalltag

Über die interaktive Nutzung hinaus ermöglicht die MCP-Architektur **autonome Agenten**, die eigenständig Routineaufgaben erledigen. Diese Agenten nutzen das ReAct-Pattern (Reasoning + Acting): Sie analysieren die aktuelle Situation, entscheiden über die nächste Aktion, führen sie aus und passen ihr Vorgehen basierend auf dem Ergebnis an.

### Drei Agent-Typen nach Auslöser

**Cron-Agenten** (zeitgesteuert) laufen zu festen Zeiten und erledigen wiederkehrende Aufgaben. Ein **Beitrags-Agent** läuft zum Beispiel am 1. jedes Quartals: Er ruft `beitraege_berechnen` auf, prüft fehlende SEPA-Mandate, generiert die SEPA-XML-Datei, erstellt Vorabankündigungen per E-Mail und legt den gesamten Vorgang zur Freigabe durch den Schatzmeister vor. Der Agent handelt nicht eigenmächtig bei finanziellen Aktionen — er bereitet alles vor und wartet auf menschliche Bestätigung. Ein **Trainingsplan-Agent** erzeugt jeden Sonntag den Wochenplan, prüft Hallenverfügbarkeit, benachrichtigt Trainer über Änderungen und veröffentlicht den Plan.

**Event-Agenten** (ereignisgesteuert) reagieren auf Datenänderungen in Echtzeit. Wenn ein neues Mitglied über `mitglied_anlegen` registriert wird, startet ein **Onboarding-Agent**: Er generiert die Beitrittserklärung, erstellt das SEPA-Mandat, sendet die Willkommens-E-Mail mit Trainingszeiten der gewählten Abteilung und fügt das Mitglied zur relevanten Kommunikationsgruppe hinzu. Ein **Mahnwesen-Agent** wird aktiviert, wenn eine Zahlung **30 Tage überfällig** ist — er prüft den bisherigen Mahnverlauf, eskaliert die Mahnstufe und generiert die nächste Zahlungserinnerung.

**Monitor-Agenten** (überwachend) prüfen periodisch Bedingungen und handeln bei Bedarf. Ein **Compliance-Agent** prüft monatlich: Läuft der Freistellungsbescheid ab? Stehen Trainer-Lizenzen vor dem Ablauf? Ist die Verbandsmeldung fällig? Sind Aufbewahrungsfristen abgelaufen und Daten zu löschen? Ein **Engagement-Agent** identifiziert Mitglieder, die seit 60 Tagen kein Training besucht haben, und schlägt personalisierte Reaktivierungs-Nachrichten vor.

### Konkretes Beispiel: Der Quartalsbeitrags-Workflow

Dieser Workflow zeigt die Verkettung mehrerer Tool-Aufrufe durch einen autonomen Agenten:

```
Agent: Quartalsbeitrag Q2/2026 wird vorbereitet.

Schritt 1: beitraege_berechnen(zeitraum="2026-Q2")
→ Ergebnis: 247 Mitglieder, Gesamtbetrag €18.420, 3 Mitglieder ohne SEPA-Mandat

Schritt 2: mitglieder_suchen(filter="ohne_sepa_mandat")  
→ Ergebnis: Müller (ID 104), Weber (ID 221), Klein (ID 308)

Schritt 3: nachricht_senden(empfaenger=[104, 221, 308], 
           template="sepa_mandat_erinnerung")
→ [HITL: Warte auf Freigabe durch Schatzmeister]
→ Freigabe erteilt. E-Mails gesendet.

Schritt 4: sepa_xml_generieren(zeitraum="2026-Q2", 
           ausschluss=[104, 221, 308])
→ [HITL: SEPA-Datei bereit. Warte auf Freigabe für Bankupload]
→ Freigabe erteilt. Datei: sepa_q2_2026.xml

Schritt 5: nachricht_senden(empfaenger="alle_lastschrift", 
           template="vorabankuendigung_q2")
→ 244 Vorabankündigungen per E-Mail versendet.

Schritt 6: buchung_anlegen(betrag=18420, konto="4100", 
           sphäre="ideell", text="Mitgliedsbeiträge Q2/2026")
→ Buchung erfasst.

Agent: Quartalsbeitrag Q2/2026 abgeschlossen. Zusammenfassung an 
Schatzmeister gesendet.
```

### Human-in-the-Loop: Wann der Agent fragen muss

Die Sicherheitsarchitektur folgt dem Prinzip **„Würde ich wollen, dass der Agent das ohne Rückfrage tut?"** und klassifiziert jede Aktion nach Reversibilität und Auswirkung:

**Vollautonome Aktionen** (kein HITL nötig): Daten abfragen und anzeigen, Berichte und Statistiken generieren, Trainingsplan zusammenstellen, Geburtstagsnachrichten senden, Erinnerungen an bevorstehende Termine, Anwesenheit erfassen, Dokumente als Entwurf vorbereiten.

**Aktionen mit Freigabe** (HITL vor Ausführung): SEPA-Lastschriftdateien erzeugen und hochladen, Mahnungen versenden, Massen-E-Mails an Mitglieder, Mitgliedskündigungen verarbeiten, Beitragsänderungen über **€50**, Daten an externe Stellen übermitteln (Finanzamt, LSB), alle destruktiven Operationen.

**Nur manuell** (Agent darf nur vorbereiten): Vorstandsbeschlüsse, Satzungsänderungen einreichen, Steuerliche Einordnung kritischer Buchungen, Umgang mit Beschwerden oder Streitigkeiten, Vertragsunterschriften.

Technisch wird dies über Tool-Annotations implementiert. Tools mit `destructiveHint: true` oder `openWorldHint: true` lösen automatisch eine Bestätigungsaufforderung im Host (Claude Desktop, ChatGPT) aus. Zusätzlich führt ein **Audit-Log** jede Agent-Aktion mit Zeitstempel, ausführendem Tool, Parametern und Ergebnis, um vollständige Nachvollziehbarkeit zu gewährleisten — besonders relevant für die steuerliche Prüfung gemeinnütziger Vereine.

---

## Web-UI vs. KI: Eine klare Grenzziehung

Die zentrale Designfrage lautet nicht „Chat oder Dashboard?", sondern **„Chat first, Dashboard when visual."** Das Prinzip der progressiven Offenlegung gilt: Starte einfach im Chat, zeige Komplexität nur, wenn sie visuell erfasst werden muss.

### Was der KI-Agent besser kann als jedes Dashboard

Für **90% der täglichen Vereinsarbeit** ist ein Chat-Interface dem klassischen Dashboard überlegen: schnelle Abfragen („Wie viele Mitglieder hat die Tennisabteilung?"), einzelne Datensätze anlegen oder ändern, Workflows auslösen („Verschicke die Einladung zur Mitgliederversammlung"), Berichte in natürlicher Sprache anfordern, Regelbasierte Fragen beantworten („Kann ein 16-Jähriger in die Erwachsenen-Abteilung?"), und Dokumente generieren. Der Vorteil ist fundamental: **Kein Ehrenamtlicher muss eine Software lernen.** Er beschreibt, was er braucht, und der Agent erledigt den Rest.

### Wo eine Web-Oberfläche unverzichtbar bleibt

Fünf Bereiche erfordern eine visuelle Darstellung, weil das menschliche Gehirn visuelle Muster **60.000× schneller** verarbeitet als Text:

**Dashboard mit KPI-Karten und Trendcharts** zeigt auf einen Blick: aktive Mitglieder (Trend ↑↓), offene Forderungen, Kassenstand nach Sphären, Trainingsauslastung. Kein Chat-Output kann ein gut gestaltetes Dashboard ersetzen, wenn es darum geht, den Gesamtzustand des Vereins zu erfassen.

**Mitgliederliste als filterbare Tabelle** ermöglicht das Scannen und Vergleichen über hunderte Einträge — nach Name sortieren, nach Abteilung filtern, nach Beitragsstatus gruppieren, Mehrfachauswahl für Bulk-Aktionen. Der Agent kann zwar „zeige alle Mitglieder mit offenen Beiträgen" beantworten, aber das Ergebnis muss als interaktive Tabelle dargestellt werden.

**Kalenderansicht für Trainings und Events** ist visuell inhärent — Verfügbarkeiten erkennen, Überschneidungen sehen, per Drag-and-Drop verschieben. Der Agent kann Termine anlegen, aber die Monatsübersicht braucht ein visuelles Grid.

**Zahlungsübersicht mit Statusverteilung** — ein Tortendiagramm (bezahlt/offen/überfällig/gemahnt) und eine sortierbare Tabelle der offenen Posten sind für den Schatzmeister essentiell.

**Dokumentenvorschau und -bearbeitung** — generierte PDFs (SEPA-Mandate, Spendenbescheinigungen, Rechnungen) müssen visuell geprüft werden können, bevor sie versendet werden.

### Das Hybrid-Pattern: Nahtlose Übergänge

Der eleganteste Ansatz ist ein **Chat-Sidebar neben dem minimalen Dashboard**. Der Nutzer kann fragen: „Zeige mir alle überfälligen Zahlungen" — der Agent ruft `mitglieder_suchen(filter="zahlung_ueberfaellig")` auf und das Ergebnis öffnet sich als gefilterte Tabelle im Dashboard. Umgekehrt kann der Nutzer in der Tabellenansicht ein Mitglied auswählen und im Chat sagen: „Schicke diesem Mitglied eine Zahlungserinnerung." Der Kontext bleibt in beiden Richtungen erhalten.

---

## Technische Architektur: Ein Backend, zwei Interfaces

```
┌────────────────────────┐    ┌────────────────────────┐
│   Minimales Web-UI     │    │   MCP-Server-Layer     │
│   (React/Vue)          │    │   (Streamable HTTP)    │
│                        │    │                        │
│   • Dashboard (KPIs)   │    │   • 26 Tools           │
│   • Mitglieder-Tabelle │    │   • 7 Resource-URIs    │
│   • Kalender           │    │   • 4 Prompt-Templates │
│   • Zahlungsübersicht  │    │   • OAuth 2.1 Auth     │
│   • Dokumentenvorschau │    │   • Audit-Logging      │
└───────────┬────────────┘    └───────────┬────────────┘
            │                             │
            ▼                             ▼
┌──────────────────────────────────────────────────────┐
│              REST-API / GraphQL                       │
│              (Shared Auth + Autorisierung)            │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│              Business-Logic-Layer                      │
│   • Beitragsberechnung (Rumpfbeiträge, Formeln)      │
│   • SEPA-XML-Generierung (pain.008)                  │
│   • SKR42-Buchungslogik (4 Sphären)                  │
│   • Zuwendungsbescheinigung nach amtl. Muster        │
│   • Kündigungsfristen lt. Satzung                    │
│   • DSGVO-Löschfristen                               │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│              Datenbank + Event-Bus                     │
│   PostgreSQL (Mitglieder, Buchungen, Mandate...)     │
│   Event-Stream (für autonome Agenten-Trigger)        │
│   Dokumenten-Storage (S3/MinIO für PDFs)             │
└──────────────────────────────────────────────────────┘
```

Die entscheidende Designentscheidung: **Die Business-Logik kennt weder KI noch UI.** Sie bietet eine saubere API, die sowohl vom MCP-Server-Layer als auch vom Web-UI konsumiert wird. Das MCP-Server-Layer ist ein dünner Adapter, der API-Endpunkte auf MCP-Tools abbildet — derselbe Endpunkt `POST /api/mitglieder` wird sowohl vom Web-Formular als auch vom Tool `mitglied_anlegen` aufgerufen. Authorization erfolgt über dieselbe Berechtigungsschicht: Ein Abteilungsleiter sieht nur seine Abteilung, egal ob er über das Dashboard oder den Chat zugreift.

Für die **autonomen Agenten** dient ein Event-Bus (z.B. über PostgreSQL LISTEN/NOTIFY oder einen leichtgewichtigen Message-Broker) als Trigger-Infrastruktur. Wenn ein `INSERT` in die Mitglieder-Tabelle erfolgt, feuert ein Event, das den Onboarding-Agenten aktiviert. Cron-Agenten werden über einen simplen Scheduler (systemd-Timer, Kubernetes CronJob) gestartet und verbinden sich als MCP-Client mit dem Server.

### Implementierung mit FastMCP (Python)

```python
from fastmcp import FastMCP
from sportverein.services import MitgliederService, BeitragsService

mcp = FastMCP(name="sportverein", version="1.0.0")

@mcp.tool(annotations={"readOnlyHint": True})
def mitglieder_suchen(
    query: str = "",
    abteilung: str | None = None,
    status: str = "aktiv",
    limit: int = 50
) -> list[dict]:
    """Durchsucht die Mitgliederdatenbank. Filtert nach Abteilung, 
    Status (aktiv/passiv/gekuendigt) und Freitext (Name, E-Mail)."""
    return MitgliederService.suchen(
        query=query, abteilung=abteilung, 
        status=status, limit=limit
    )

@mcp.tool(annotations={"destructiveHint": True})
def sepa_xml_generieren(
    zeitraum: str,
    ausfuehrungsdatum: str,
    ausschluss_ids: list[int] = []
) -> dict:
    """Generiert eine SEPA-XML-Lastschriftdatei (pain.008.001.02) 
    für alle fälligen Beiträge im angegebenen Zeitraum. 
    ACHTUNG: Erfordert Freigabe vor Bankupload."""
    result = BeitragsService.sepa_generieren(
        zeitraum=zeitraum, 
        datum=ausfuehrungsdatum,
        ausschluss=ausschluss_ids
    )
    return {
        "datei": result.filename,
        "anzahl_lastschriften": result.count,
        "gesamtbetrag": str(result.total),
        "status": "bereit_zur_freigabe"
    }

@mcp.resource("sportverein://satzung")
def get_satzung() -> str:
    """Aktuelle Vereinssatzung als Volltext für kontextbasierte Fragen."""
    return SatzungService.aktuelle_version()

@mcp.prompt()
def quartalsbeitrag(quartal: str) -> str:
    """Geführter Workflow für den quartalsweisen Beitragseinzug."""
    return f"""Bitte führe den Beitragseinzug für {quartal} durch:
    1. Berechne alle fälligen Beiträge mit beitraege_berechnen
    2. Prüfe fehlende SEPA-Mandate mit mitglieder_suchen
    3. Generiere die SEPA-Datei mit sepa_xml_generieren
    4. Erstelle Vorabankündigungen mit nachricht_senden
    Frage mich vor jeder finanziellen Aktion um Bestätigung."""
```

---

## DSGVO, Gemeinnützigkeit und regulatorische Anforderungen

Ein agentic-first System muss die regulatorische Komplexität deutscher Vereinsverwaltung vollständig abbilden. Die **DSGVO gilt uneingeschränkt** für jeden Verein — die Verarbeitung von Mitgliederdaten ist über Art. 6(1)(b) (Vertragserfüllung durch Satzung) gerechtfertigt, aber Newsletter, Fotos und Gesundheitsdaten erfordern explizite Einwilligung. Der MCP-Server muss ein `datenschutz_auskunft`-Tool bereitstellen, das auf Anfrage alle gespeicherten Daten eines Mitglieds nach Art. 15 DSGVO zusammenstellt.

Die **Gemeinnützigkeit** (§§51-68 AO) erfordert, dass jede Buchung korrekt einer der vier steuerlichen Sphären zugeordnet wird: ideeller Bereich (Beiträge, Spenden), Zweckbetrieb (Sportveranstaltungen nach §65 AO), Vermögensverwaltung (Mieteinnahmen, Zinsen) und wirtschaftlicher Geschäftsbetrieb (Werbung, Merchandise). Der Agent muss bei `buchung_anlegen` die Sphärenzuordnung vorschlagen können — ein hervorragender Anwendungsfall für KI, da die Abgrenzung oft unklar ist und der Agent die Satzung als Resource-Kontext heranziehen kann. Ab 2025 gilt der **SKR42 als verpflichtender Kontenrahmen**, was in der Buchungslogik abgebildet sein muss.

Für **Auftragsverarbeitung** (AVV) mit dem SaaS-Anbieter und die Integration mit LLM-Providern (Anthropic, OpenAI) gelten besondere Anforderungen: Mitgliederdaten, die an das LLM übermittelt werden, müssen minimiert und die AVV-Pflichten mit dem LLM-Anbieter geklärt sein. Eine datenschutzfreundliche Architektur sendet **nur die für die aktuelle Anfrage relevanten Daten** an das LLM, nicht den gesamten Datenbestand.

---

## Von der Theorie zur Umsetzung: Empfohlene Roadmap

**Phase 1 (MVP — 3 Monate):** MCP-Server mit den 6 Mitgliederverwaltungs-Tools, dem Beitragsberechnungs-Tool und den Kommunikations-Tools. Minimales Web-Dashboard mit Mitgliederliste und Kassenstand. Anbindung an Claude Desktop via stdio für den lokalen Einsatz durch den Vereinsvorstand.

**Phase 2 (Finanzen — 2 Monate):** SEPA-Lastschrift-Integration, SKR42-Buchungslogik, Spendenbescheinigungen. Zahlungsübersicht im Web-UI. Erster Cron-Agent für Beitragseinzug mit HITL.

**Phase 3 (Autonomie — 2 Monate):** Event-getriebene Agenten (Onboarding, Mahnwesen), Monitor-Agent für Compliance, Kalenderansicht im Web-UI. Streamable HTTP für Remote-Zugriff mit OAuth 2.1.

**Phase 4 (Ökosystem — fortlaufend):** Verbandsmeldung-Export, DATEV-Schnittstelle, E-Rechnung (XRechnung/ZUGFeRD), Multi-Verein-Fähigkeit. Veröffentlichung als Open-Source-MCP-Server, den jeder Verein mit seinem LLM-Anbieter der Wahl verbinden kann.

---s‚

## Fazit: Der Verein als API, der Agent als Sachbearbeiter

Das agentic-first Paradigma löst das Kernproblem der Vereinsverwaltung: **Es eliminiert die Software-Lernkurve für Ehrenamtliche.** Statt einer weiteren SaaS-Plattform mit eigenem Login und eigener Oberfläche wird der Verein zu einer strukturierten Datenquelle mit 26 Tools, die jeder KI-Assistent nutzen kann. Die Satzung wird zum Resource-Kontext, der dem Agenten ermöglicht, vereinsspezifische Regeln korrekt anzuwenden. Autonome Agenten übernehmen Routineaufgaben — von der Beitragsberechnung bis zur Compliance-Überwachung — mit eingebauten Sicherheitsmechanismen für kritische Aktionen.

Drei Erkenntnisse verdienen besondere Betonung. Erstens: **Die Web-UI schrumpft auf fünf Seiten** (Dashboard, Mitgliederliste, Zahlungen, Kalender, Dokumente), weil alles andere besser per Chat funktioniert. Zweitens: **Die größte Hebelwirkung liegt bei den autonomen Agenten**, nicht beim interaktiven Chat — ein Mahnwesen-Agent, der selbstständig dreistufige Erinnerungen verschickt, spart dem Schatzmeister mehr Zeit als jedes Dashboard. Drittens: Die **regulatorische Komplexität** (SKR42, vier Sphären, Gemeinnützigkeit, DSGVO) ist kein Hindernis, sondern ein Argument für KI — ein Agent, der die Satzung als Kontext hat und steuerliche Zuordnungen vorschlägt, macht weniger Fehler als ein Ehrenamtlicher, der einmal im Quartal die SEWOBE-Oberfläche öffnet.

Der Sportverein der Zukunft braucht keine bessere Software. Er braucht einen besseren Sachbearbeiter — einen, der nie Urlaub hat, die Satzung auswendig kennt und um 23 Uhr noch die SEPA-Datei vorbereitet.