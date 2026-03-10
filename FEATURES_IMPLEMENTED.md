# Implemented Features

> Legend: **MCP** = manageable via ChatGPT/MCP chat | **UI** = available in web frontend | **API** = REST endpoint exists
> Markers: YES = implemented | NO = not implemented | PARTIAL = partially implemented

---

## 1. Mitgliederverwaltung (Member Management)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Mitglied anlegen (create member) | YES `mitglied_anlegen` | YES | YES |
| Mitglied suchen/filtern (search by name, status, department, category) | YES `mitglieder_suchen` | YES | YES |
| Mitglied-Details anzeigen | YES `mitglied_details` | YES | YES |
| Mitglied aktualisieren | YES `mitglied_aktualisieren` | YES | YES |
| Mitglied kuendigen | YES `mitglied_kuendigen` | YES | YES |
| Abteilungszuordnung (assign/remove department) | YES `mitglied_abteilung_zuordnen` | YES | YES |
| Mitgliederstatistik (active, passive, new, by dept) | YES via dashboards | YES | YES |
| Schnell-Onboarding (info booth registration) | NO | YES | YES |
| Auto-Mitgliedsnummer-Vergabe | YES (automatic) | YES | YES |

## 2. Abteilungen (Departments)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Abteilungen auflisten | YES `vereins_setup_abteilungen` | YES | YES |
| Abteilung anlegen | YES `vereins_setup_abteilungen` | YES | YES |
| Abteilung bearbeiten | YES `vereins_setup_abteilungen` | YES | YES |
| Abteilung loeschen | YES `vereins_setup_abteilungen` | YES | YES |

## 3. Beitragswesen (Fee Management)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Beitragskategorien verwalten (CRUD) | YES `vereins_setup_beitragskategorien` | YES | YES |
| Beitraege berechnen (single member or all) | YES `beitraege_berechnen` | NO | YES |
| Pro-rata Berechnung (mid-year join) | YES (automatic) | NO | YES |
| Kombi-Rabatte (Jugend 50%, Multi-Abt. 10%, Familie 20%) | YES (automatic) | NO | YES |
| Beitragslauf starten (batch fee generation) | YES `beitragseinzug_starten` | YES | YES |

## 4. Rechnungswesen (Invoicing)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Rechnung erstellen (with line items/positions) | YES `rechnung_erstellen` | YES | YES |
| Rechnung anzeigen/filtern | YES `rechnungen_auflisten` | YES | YES |
| Rechnung stellen (entwurf to gestellt) | YES `rechnung_stellen` | YES | YES |
| Rechnung stornieren | YES `rechnung_stornieren` | YES | YES |
| Zahlung verbuchen | YES `zahlung_verbuchen` | YES | YES |
| Rechnung PDF generieren | YES `rechnung_pdf_generieren` | YES | YES |
| ZUGFeRD 2.1 XML generieren | YES `rechnung_zugferd_xml` | NO | NO |
| Skonto-Felder | YES | NO | YES |
| Versand-Tracking (Kanal, Datum, Status) | NO | NO | YES |
| 7 Rechnungstypen (Beitrag, Kurs, Halle, Sponsoring, Sonstige, Storno, Mahnung) | YES | YES | YES |
| 10 Status-Stufen (Entwurf to Bezahlt/Storniert/Abgeschrieben) | YES | YES | YES |

## 5. Mahnwesen (Dunning)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Mahnkandidaten ermitteln (3 Mahnstufen) | YES `mahnlauf_starten` | NO | YES |
| Mahnwesen-Analyse (auto dunning level assignment) | YES `mahnwesen_agent` | NO | YES |
| Mahnung erstellen | NO | NO | YES |

## 6. SEPA-Lastschrift (Direct Debit)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| SEPA-Mandat anlegen | YES `sepa_mandate_verwalten` | YES | YES |
| SEPA-Mandat bearbeiten | YES `sepa_mandate_verwalten` | NO | YES |
| SEPA-Mandate auflisten | YES `sepa_mandate_verwalten` | YES | YES |
| SEPA-Mandat deaktivieren | YES `sepa_mandate_verwalten` | NO | YES |
| SEPA-XML generieren (pain.008.001.02) | YES `sepa_xml_generieren` | YES | YES |

## 7. Buchfuehrung (Accounting)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Buchung anlegen (with 4-sphere system) | YES `buchung_anlegen` | NO | YES |
| Buchungsjournal anzeigen/filtern | NO | YES | YES |
| Kassenstand nach Sphaeren | YES `finanzbericht_erstellen` | YES | YES |
| Gesamtsaldo | YES | YES | YES |
| Leistungsverrechnung (cross-cost-center split) | YES `leistungsverrechnung` | NO | NO |
| EUER-Bericht (Einnahme-Ueberschuss-Rechnung) | YES `finanzen_euer` | YES | NO |

## 8. Kostenstellen (Cost Centers)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Kostenstelle anlegen | YES `kostenstellen_verwalten` | YES | YES |
| Kostenstelle bearbeiten | YES `kostenstellen_verwalten` | YES | YES |
| Kostenstelle loeschen | YES `kostenstellen_verwalten` | YES | YES |
| Budget-Pruefung (budget vs. spent vs. remaining) | YES `budget_pruefen` | YES | YES |
| Freigabelimit | YES | NO | YES |

## 9. Eingangsrechnungen (Incoming Invoices)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Eingangsrechnung anlegen | NO | NO | YES |
| Eingangsrechnung pruefen (XRechnung/ZUGFeRD parse) | YES `eingangsrechnung_pruefen` | NO | NO |
| Eingangsrechnungen auflisten | NO | NO | YES |

## 10. Ehrenamt (Volunteer Compensation)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Aufwandsentschaedigung verwalten (create/check/list) | YES `aufwandsentschaedigung` | NO | NO |
| Freibetraege pruefen (par. 3 Nr.26/26a EStG) | YES `aufwand_monitor` | NO | NO |
| Warnung bei mehr als 80% Limit | YES `aufwand_monitor` | NO | NO |

## 11. Spendenbescheinigungen (Donation Receipts)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Spendenbescheinigung erstellen | YES `spendenbescheinigung_erstellen` | NO | NO |

## 12. Training und Anwesenheit (Training and Attendance)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Trainingsgruppen verwalten (CRUD) | YES `training_verwalten` | YES | YES |
| Anwesenheit erfassen | YES `anwesenheit_erfassen` | YES | YES |
| Anwesenheits-Heatmap (pro Abteilung) | YES `anwesenheit_statistik` | YES | YES |
| Mitglied-Anwesenheitsquote | NO | NO | YES |

## 13. Dashboards (Role-based)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Vorstand-Dashboard (KPIs, Trend, Cashflow, Aktionen) | YES `dashboard_vorstand` | YES | YES |
| Schatzmeister-Dashboard (SEPA, Offene Posten, Budget) | YES `dashboard_schatzmeister` | YES | YES |
| Spartenleiter-Dashboard (Training, Heatmap, Risiko) | YES `dashboard_spartenleiter` | YES | YES |

## 14. DSGVO / Datenschutz (Data Privacy)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Datenauskunft (Art. 15 DSGVO, full export) | YES `datenschutz_auskunft` | NO | YES |
| Einwilligung setzen | NO | NO | YES |
| Loeschfrist planen | YES `datenschutz_loeschfrist_planen` | NO | YES |
| Ausstehende Loeschungen anzeigen | YES `datenschutz_ausstehende_loeschungen` | NO | YES |

## 15. Audit und Compliance

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Audit-Log (alle Aktionen protokolliert) | NO | YES | YES |
| Audit-Log filtern (Aktion, Entity, User, Datum) | NO | YES | YES |
| Letzte Aktivitaeten | NO | YES | YES |

## 16. Vereinsstammdaten (Club Master Data)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Stammdaten anzeigen/bearbeiten (Name, Adresse, Steuer-Nr, IBAN etc.) | NO | YES | YES |

## 17. Kommunikation (Communication)

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Nachricht senden (an Mitglied/Gruppe) | YES `nachricht_senden` | NO | NO |
| Newsletter erstellen | YES `newsletter_erstellen` | NO | NO |
| Dokument generieren (Bescheinigung, Brief) | YES `dokument_generieren` | NO | NO |
| Protokoll anlegen (Sitzungsprotokoll) | YES `protokoll_anlegen` | NO | NO |

## 18. Authentication

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Email/Passwort Login | NO | YES | YES |
| API-Token Login | NO | YES | YES |
| Token erstellen/rotieren/widerrufen | NO | YES | YES |

## 19. Chat / AI-Sidebar

| Feature | MCP | UI | API |
|---|:---:|:---:|:---:|
| Chat-Sidebar (Kontext-basiert) | n/a | YES | YES |
| Seitenkontext wird mitgesendet | n/a | YES | YES |

## 20. MCP Resources (Read-only context for AI)

| Resource | Description |
|---|---|
| `abteilungen_resource` | List of all departments |
| `satzung_resource` | Club bylaws template |
| `beitragsordnung_resource` | Fee regulations template |

---

## MCP Coverage Summary

| Area | MCP Tools | Chat-First Ready? |
|---|---|---|
| Mitglieder | 9 tools | YES - Full CRUD + search + DSGVO |
| Beitraege und Einzug | 3 tools | YES - Calculate, collect, generate SEPA |
| Rechnungen | 8 tools | YES - Create, list, issue, cancel, pay, PDF, ZUGFeRD |
| Mahnwesen | 2 tools | YES - Identify + auto-assign levels |
| Buchfuehrung | 4 tools | YES - Book, report, EUER, cross-allocate |
| Kostenstellen | 2 tools | YES - Full CRUD + budget check |
| Ehrenamt | 2 tools | YES - Manage + monitor limits |
| Training | 5 tools | YES - Groups + attendance + stats + member rate |
| Dashboards | 3 tools | YES - All 3 role views |
| Setup | 2 tools | YES - Departments + fee categories |
| Kommunikation | 4 tools | YES - Messages, newsletter, docs, minutes |
| Eingangsrechnung | 3 tools | YES - Parse + list + status management |
| Spenden | 1 tool | YES - Create receipts |
| DSGVO | 4 tools | YES - Export, consent, deletion schedule, pending |
| SEPA-Mandate | 1 tool | YES - Full CRUD via sepa_mandate_verwalten |
| Audit-Log | 1 tool | YES - Query with filters |
| Stammdaten | 2 tools | YES - View + update |
| Auth/Tokens | 0 tools | NO - Not in MCP (by design) |

**Total: 56 MCP tools + 3 MCP resources**

All feature areas are now chat-first ready (except Auth which is intentionally excluded).
