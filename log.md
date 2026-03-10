# Implementation & Testing Log

## 2026-03-10

### P0 Features Completed

#### 1. DSGVO Data Deletion (DONE)
- New service: `services/datenschutz.py` with `delete_member_data()` and `enforce_pending_deletions()`
- Anonymizes personal data (name -> "Geloescht", email -> placeholder, phone/address/notes -> null)
- New API: `DELETE /api/mitglieder/{id}/dsgvo-loeschen`
- New MCP tool: `datenschutz_mitglied_loeschen`
- Migration: `1a7bd51899af` adds `geloescht_am` column
- Tests: 12 service + 4 API tests

#### 2. Skonto Calculation Logic (DONE)
- Service: `calculate_skonto()` + auto-apply on payment
- API: `GET /api/finanzen/rechnungen/{id}/skonto`
- Tests: 8 new tests

#### 3. E-Rechnung UI Buttons (DONE)
- Invoice table: DropdownMenu with PDF/ZUGFeRD download, Versenden dialog
- Batch toolbar: ZIP export + batch send

#### 4. Eingangsrechnungen UI (DONE)
- New tab in Finanzen with status workflow table
- Status badges, contextual actions, filtering

#### 5. Dashboard Wired to Real API (DONE)
- Vorstand, Schatzmeister, Spartenleiter views fetch from `/api/dashboard/*`
- Loading/error states, data mapping

#### 6. Ehrenamt UI (DONE)
- New "Ehrenamt" tab in Finanzen
- Freibetrag summary cards with progress bars and >80% warnings
- Table with year/category filters

### P1 Features In Progress
- [ ] DATEV CSV Export (agent running)
- [ ] Compliance Monitor Agent (agent running)

### Loop 3: Extended API Testing

**Backend tests:** 457 passed, 3 skipped

#### Additional API Endpoints Tested
| Endpoint | Status | Result |
|----------|--------|--------|
| GET /api/training/gruppen | 200 | 8 groups with trainer names |
| GET /api/audit | 200 | Shows DSGVO deletion audit entries |
| GET /api/finanzen/vereinsstammdaten | 200 | Returns club master data |
| GET /api/setup/abteilungen | exists | Route registered |
| GET /api/setup/beitragskategorien | exists | Route registered |
| POST /api/agents/beitragseinzug | 422 | Needs request body (expected) |

#### Route Mapping Notes (for frontend devs)
- Stammdaten is at `/api/finanzen/vereinsstammdaten` NOT `/api/setup/stammdaten`
- Audit logs at `/api/audit` NOT `/api/audit/logs`
- No root `/api/dashboard` endpoint, only sub-routes (stats, vorstand, schatzmeister, spartenleiter/{abt})

### Completed Commits
1. `4524d57` - Initial feature batch (training, invoicing, dashboards, setup, MCP tools)
2. `9b9ba68` - P0: DSGVO deletion, Skonto logic, E-Rechnung UI
3. `a34e7e4` - Dashboard wiring + Eingangsrechnungen UI + Ehrenamt backend
4. `237f0d7` - Ehrenamt UI tab

### Next Up
- [ ] DATEV Export (in progress)
- [ ] Compliance Monitor (in progress)
- [ ] Calendar page
- [ ] Trainer license tracking
- [ ] Documents page
