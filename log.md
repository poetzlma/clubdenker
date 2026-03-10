# Implementation & Testing Log

## 2026-03-10

### P0 Features Completed

#### 1. DSGVO Data Deletion (DONE)
- New service: `services/datenschutz.py` with `delete_member_data()` and `enforce_pending_deletions()`
- Anonymizes personal data (name -> "Geloescht", email -> placeholder, phone/address/notes -> null)
- Keeps record for audit trail (no hard-delete)
- New API: `DELETE /api/mitglieder/{id}/dsgvo-loeschen`
- New MCP tool: `datenschutz_mitglied_loeschen`
- New migration: `1a7bd51899af` adds `geloescht_am` column
- Tests: 12 service tests + 4 API tests, all passing

#### 2. Skonto Calculation Logic (DONE)
- New service method: `calculate_skonto(rechnung_id, reference_date)` in `services/finanzen.py`
- Formula: `summe_netto * skonto_prozent / 100` when within deadline
- Modified `record_payment()` to accept `apply_skonto` flag
- Creates Skonto-Abzug booking (SKR42 account 4730) when applied
- New API: `GET /api/finanzen/rechnungen/{id}/skonto`
- Updated `zahlung_verbuchen` MCP tool with `apply_skonto` parameter
- Tests: 8 new tests covering all skonto scenarios

#### 3. E-Rechnung UI Buttons (DONE)
- New component: `frontend/src/components/finanzen/versand-dialog.tsx` (send via Email/Post/Portal)
- Invoice table: added DropdownMenu with PDF download, ZUGFeRD-XML download, Versenden
- Row selection with checkboxes for batch operations
- Batch toolbar: "Export Jahr als ZIP" button + "Ausgewaehlte versenden" for multi-send
- Backend endpoints already existed, no backend changes needed

### Loop 1: Testing & Bug Hunting

**Backend tests:** 457 passed, 3 skipped
**Frontend tests:** 7 files, 40 tests passed
**Frontend TSC:** Clean

#### Bugs Found & Fixed
1. **BUG: `mitglieder.geloescht_am` column missing** -- DSGVO agent added the field to the model but the migration wasn't applied to the running DB. Ran `alembic upgrade head` to fix. API returned 500 before, now returns 200.

#### Bugs Found (Not Yet Fixed)
2. **BUG: Dashboard frontend doesn't fetch from API** -- Frontend dashboard views (`vorstand-view.tsx`, `schatzmeister-view.tsx`, `spartenleiter-view.tsx`) do not call any `/api/dashboard/*` endpoints. They use hardcoded/mock data. Backend endpoints all work correctly.

#### API Endpoints Tested
| Endpoint | Status | Result |
|----------|--------|--------|
| GET /api/mitglieder | 200 | 51 members, paginated |
| GET /api/dashboard/stats | 200 | Active/passive counts, department breakdown |
| GET /api/dashboard/vorstand | 200 | KPIs, member trend, compliance score |
| GET /api/dashboard/schatzmeister | 200 | SEPA hero, balances by sphere, open items |
| GET /api/finanzen/rechnungen | 200 | 4 invoices |
| GET /api/finanzen/buchungen | 200 | 0 bookings |
| GET /api/training/gruppen | 200 | 8 training groups |

### Next Up (P1)
- [ ] Wire dashboard frontend to real API endpoints
- [ ] Eingangsrechnungen UI (backend 80% done, frontend 0%)
- [ ] Batch Invoice Versand improvements
- [ ] DATEV Export
- [ ] Compliance Monitor Agent
