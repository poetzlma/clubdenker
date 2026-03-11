# Missing Features — VereinsOS

Stand: 10.03.2026 · Automatisch auditiert gegen alle Spec-Dokumente

## Legende

- **Quelle**: Welches Spec-Dokument die Anforderung definiert
- **Status**: ❌ Fehlt komplett · ⚠️ Teilweise · ✅ Fertig
- **Prio**: P0 = rechtlich notwendig · P1 = MVP-kritisch · P2 = wichtig · P3 = nice-to-have

---

## 1. Rechnungswesen (Quelle: `rechnung_facts.md`)

### P0 — Rechtlich notwendig

| # | Feature | Spec § | Status | Details |
|---|---------|--------|--------|---------|
| 1 | **E-Rechnung Empfang** (XRechnung/ZUGFeRD Parser) | §5 | ❌ | Ab 01.01.2025 Pflicht für Empfang. Kein XML-Parser vorhanden. |
| 2 | **ZUGFeRD-Export** (PDF + eingebettetes XML) | §5 | ❌ | Pflicht für B2B ab 2028. Model-Feld `format` existiert, keine Generierung. |
| 3 | **Löschsperre Enforcement** | §9 | ⚠️ | `loeschdatum` wird berechnet, aber API verhindert Löschung nicht aktiv. |
| 4 | **Skonto-Felder** | §6 | ❌ | `skonto_prozent`, `skonto_frist_tage` fehlen im Model. |
| 5 | **Versand-Kanal Tracking** | §12 | ❌ | Kein `versand_kanal` Enum, kein Versandprotokoll. |

### P1 — Wichtig für Produktivbetrieb

| # | Feature | Spec § | Status | Details |
|---|---------|--------|--------|---------|
| 6 | **DATEV-Export** (Buchungen + Rechnungen → CSV) | §13 | ❌ | Kein Export-Format für Steuerberater. |
| 7 | **MT940/CAMT Kontoauszug-Import** | §13 | ❌ | Keine automatische Zahlungszuordnung über Bankdaten. |
| 8 | **Batch-Rechnungsversand** (E-Mail mit PDF) | §12 | ❌ | SMTP-Service existiert, kein UI für Massenversand. |
| 9 | **Rechnungs-ZIP-Export** pro Jahr | §9, §14 | ⚠️ | API-Endpoint `/export?jahr=` existiert, kein Frontend-Button. |
| 10 | **XRechnung-Export** (reines XML) | §5 | ❌ | EN 16931 Schema nicht implementiert. |

### P2 — Sinnvolle Erweiterungen

| # | Feature | Spec § | Status | Details |
|---|---------|--------|--------|---------|
| 11 | **Eingehende Rechnungen** (Erfassung + Prüfung) | §4.2 | ❌ | Kein Model für Eingangsrechnungen (Trainer, Hallenmiete, Equipment). |
| 12 | **Kursgebühr ↔ Veranstaltungs-Verknüpfung** | §4.1C | ⚠️ | Template existiert, kein Event-Link. |
| 13 | **Sponsoring-Vertragsverknüpfung** | §4.1E | ⚠️ | Template existiert, kein Contract-Tracking. |
| 14 | **Familienrechnung** (mehrere Mitglieder, eine RE) | §15 | ❌ | Kein Familien-Gruppierungskonzept. |
| 15 | **Gemischte Rechnung Warnung** (mehrere Steuersätze) | §15 | ❌ | Keine UI-Warnung bei Mixed-Rate-Positionen. |

---

## 2. Finanzen allgemein (Quelle: `additional_features.md`, `idea.md`)

### P1

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 16 | **Spartenleiter Row-Level Security** | additional_features §Phase3 | ⚠️ | Rolle existiert, kein RLS auf API-Ebene. |
| 17 | **Compliance Monitor Agent** (monatlich) | idea.md §Agents | ❌ | Prüft Zweckbetriebs-Umsatzgrenze €45k, Gemeinnützigkeit. |
| 18 | **Engagement Monitor Agent** | idea.md §Agents | ❌ | Inaktive Mitglieder erkennen + Alert. |

### P2

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 19 | **PayPal/Stripe Webhook** | rechnung_facts §6.2 | ❌ | Online-Zahlungswege. Phase 6. |
| 20 | **Dokumenten-Storage** (S3/MinIO) | rechnung_facts §13 | ❌ | PDFs nur lokal. |

---

## 3. Training & Veranstaltungen (Quelle: `additional_features.md`, `dashboards.md`)

### P1

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 21 | **Hallenplanung / Kalender-UI** | additional_features §Phase3 | ❌ | Sidebar-Item disabled. Kein Drag-Drop-Kalender. |
| 22 | **QR-Code Anwesenheit** | additional_features §Phase3 | ❌ | Kein QR-Generator/Scanner für Check-in. |
| 23 | **Mobile Anwesenheitserfassung** | dashboards.md | ⚠️ | Desktop funktioniert, kein Mobile-optimiertes Layout. |

### P2

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 24 | **Lizenz-/Qualifikations-Tracking** | additional_features §Phase3 | ❌ | Trainer-Lizenzen, Erste-Hilfe-Scheine mit Ablaufdatum. |
| 25 | **Raumbuchung MCP-Tool** | idea.md §MCP-Tools | ❌ | `raum_buchen` Tool nicht implementiert. |

---

## 4. Mitglieder & Kommunikation (Quelle: `idea.md`, `additional_features.md`)

### P2

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 26 | **Self-Service-Portal** (Mitglieder) | additional_features §Phase6 | ❌ | Stammdaten selbst ändern, Rechnungen einsehen, Kündigung beantragen. |
| 27 | **Mitglieder-Analytics** (Churn, Saisonalität) | additional_features §Phase5 | ❌ | Kein Frühwarnsystem für Austritt. |
| 28 | **Protokoll-Archiv** (Beschlüsse + KI-Suche) | additional_features §Phase5 | ❌ | Kein Sitzungsprotokoll-Management. |

### P3

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 29 | **DFBnet/click-TT Sync** | additional_features §Phase4 | ❌ | Verbandsmeldung automatisieren. |
| 30 | **Spielbetrieb** (Teams, Spiele, Pässe) | additional_features §Phase4 | ❌ | Mannschafts- und Spielverwaltung. |
| 31 | **Fördermittel-Management** | additional_features §Phase5 | ❌ | LSB-Anträge, Verwendungsnachweise. |
| 32 | **Multi-Mandanten** | additional_features §Phase6 | ❌ | Mehrere Vereine in einer Instanz. |

---

## 5. Design & UX (Quelle: `design.md`, `dashboards.md`)

### P2

| # | Feature | Quelle | Status | Details |
|---|---------|--------|--------|---------|
| 33 | **ARIA Labels für Icon-Only Sidebar** | design.md §Accessibility | ⚠️ | Collapsed Sidebar hat keine Screen-Reader-Labels. |
| 34 | **Responsive Tables** (Mobile) | design.md §Atoms | ⚠️ | Desktop-optimiert, auf Mobile unlesbar. |

---

## Zusammenfassung nach Priorität

| Prio | Anzahl | Wichtigste Items |
|------|--------|-----------------|
| **P0** | 5 | E-Rechnung Empfang/Export, Löschsperre, Skonto, Versandprotokoll |
| **P1** | 8 | DATEV, MT940, Batch-Versand, Kalender, Compliance Agent |
| **P2** | 13 | Eingangsrechnungen, Self-Service, Analytics, Lizenz-Tracking |
| **P3** | 8 | DFBnet, Spielbetrieb, Fördermittel, Multi-Mandanten |

### Empfohlene Reihenfolge

**Sprint 1 (P0):** E-Rechnung ZUGFeRD-Export + Empfang, Löschsperre Enforcement, Skonto-Felder
**Sprint 2 (P1):** DATEV-Export, Batch-Rechnungsversand, Rechnungs-ZIP Frontend-Button
**Sprint 3 (P1):** Hallenplanung Kalender-UI, MT940 Import, Compliance Monitor Agent
**Sprint 4 (P2):** Eingangsrechnungen, Self-Service-Portal, Lizenz-Tracking
**Backlog (P3):** DFBnet, Spielbetrieb, Multi-Mandanten, Fördermittel
