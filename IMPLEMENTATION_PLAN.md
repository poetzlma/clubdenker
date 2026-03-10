# Implementation Plan: Sportverein MCP Server

## Decisions Summary

| Decision | Choice |
|----------|--------|
| Backend | Python 3.12+, FastMCP, FastAPI |
| Database | SQLite (via aiosqlite) — no Docker needed. PostgreSQL-ready for production later |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic |
| Frontend | React 19, TypeScript, shadcn/ui, Tailwind CSS |
| Frontend tooling | Vite, npm |
| Monorepo | `backend/` + `frontend/` in one repo |
| Code language | English code, German user-facing strings |
| Auth | Bearer token (rotatable via admin UI), OAuth 2.1 deferred |
| Testing | pytest (backend), Vitest (frontend), full unit + integration |
| Agents | Deferred to Phase 3 |
| Styling | shadcn/ui admin dashboard pattern: sidebar nav, KPI cards, charts, data tables |

---

## Monorepo Structure

```
sportverein/
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── src/
│   │   └── sportverein/
│   │       ├── __init__.py
│   │       ├── main.py                  # FastAPI + FastMCP app entrypoint
│   │       ├── config.py                # Settings (env-based)
│   │       ├── auth/
│   │       │   ├── __init__.py
│   │       │   ├── models.py            # AdminUser, ApiToken DB models
│   │       │   ├── service.py           # Token generation, validation, rotation
│   │       │   ├── dependencies.py      # FastAPI deps (get_current_user, require_admin)
│   │       │   └── router.py            # /auth/* endpoints
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── base.py              # SQLAlchemy Base, common mixins
│   │       │   ├── mitglied.py          # Mitglied, Abteilung, MitgliedAbteilung
│   │       │   ├── beitrag.py           # Beitragskategorie, Beitrag, Zahlung
│   │       │   ├── finanzen.py          # Buchung, SepaMandat, Rechnung
│   │       │   ├── kommunikation.py     # Nachricht, NachrichtEmpfaenger
│   │       │   └── veranstaltung.py     # Training, Veranstaltung, Anwesenheit
│   │       ├── services/
│   │       │   ├── __init__.py
│   │       │   ├── mitglieder.py        # Member CRUD + search
│   │       │   ├── beitraege.py         # Fee calculation, pro-rata, age tiers
│   │       │   ├── finanzen.py          # SKR42 bookkeeping, SEPA XML generation
│   │       │   ├── kommunikation.py     # Email sending, templates
│   │       │   └── dokumente.py         # PDF generation (SEPA mandate, receipts)
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── router.py            # Main API router
│   │       │   ├── mitglieder.py        # /api/mitglieder/*
│   │       │   ├── beitraege.py         # /api/beitraege/*
│   │       │   ├── finanzen.py          # /api/finanzen/*
│   │       │   ├── kommunikation.py     # /api/kommunikation/*
│   │       │   └── dashboard.py         # /api/dashboard/* (KPIs, stats)
│   │       ├── mcp/
│   │       │   ├── __init__.py
│   │       │   ├── server.py            # FastMCP server setup
│   │       │   ├── tools_mitglieder.py  # 6 member tools
│   │       │   ├── tools_beitraege.py   # 8 finance tools
│   │       │   ├── tools_kommunikation.py # 4 communication tools
│   │       │   └── resources.py         # MCP resources (satzung, beitragsordnung, etc.)
│   │       └── db/
│   │           ├── __init__.py
│   │           ├── session.py           # Async session factory
│   │           └── seed.py              # Dev seed data
│   └── tests/
│       ├── conftest.py                  # Fixtures (async DB, test client, auth tokens)
│       ├── test_services/
│       │   ├── test_mitglieder.py
│       │   ├── test_beitraege.py
│       │   └── test_finanzen.py
│       ├── test_api/
│       │   ├── test_mitglieder.py
│       │   ├── test_beitraege.py
│       │   └── test_dashboard.py
│       └── test_mcp/
│           ├── test_tools_mitglieder.py
│           └── test_tools_beitraege.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                   # API client (fetch wrapper with auth)
│   │   │   └── utils.ts                 # cn() helper, formatters
│   │   ├── hooks/
│   │   │   ├── use-auth.ts
│   │   │   └── use-api.ts               # Generic data fetching hook
│   │   ├── components/
│   │   │   ├── ui/                      # shadcn/ui components (button, card, table, etc.)
│   │   │   ├── layout/
│   │   │   │   ├── sidebar.tsx          # Collapsible sidebar nav
│   │   │   │   ├── header.tsx           # Top bar with user menu
│   │   │   │   └── app-layout.tsx       # Shell combining sidebar + header + content
│   │   │   ├── dashboard/
│   │   │   │   ├── kpi-cards.tsx        # Active members, revenue, open fees, etc.
│   │   │   │   ├── member-trend-chart.tsx
│   │   │   │   └── recent-activity.tsx
│   │   │   ├── mitglieder/
│   │   │   │   ├── member-table.tsx     # Filterable, sortable, paginated
│   │   │   │   ├── member-form.tsx      # Create/edit member dialog
│   │   │   │   └── member-detail.tsx    # Detail view with tabs
│   │   │   ├── finanzen/
│   │   │   │   ├── payment-overview.tsx # Status pie chart + table
│   │   │   │   ├── booking-table.tsx
│   │   │   │   └── sepa-generator.tsx   # SEPA workflow UI
│   │   │   └── admin/
│   │   │       └── token-management.tsx # Generate/rotate API tokens
│   │   └── pages/
│   │       ├── dashboard.tsx
│   │       ├── mitglieder.tsx
│   │       ├── finanzen.tsx
│   │       ├── kalender.tsx             # Placeholder for Phase 3
│   │       ├── dokumente.tsx            # Placeholder for Phase 3
│   │       ├── admin.tsx
│   │       └── login.tsx
│   └── __tests__/
│       ├── dashboard.test.tsx
│       └── member-table.test.tsx
├── .env.example
├── CLAUDE.md
├── IMPLEMENTATION_PLAN.md
└── idea.md
```

---

## Phase 1: Core MCP Server + Member Management

### Step 1: Project Scaffolding
- [ ] Initialize monorepo with `backend/` and `frontend/`
- [ ] `backend/pyproject.toml` with dependencies: fastmcp, fastapi, uvicorn, sqlalchemy[asyncio], aiosqlite, alembic, pydantic-settings, python-jose, passlib, pytest, pytest-asyncio, httpx
- [ ] `frontend/` via Vite React-TS template, install shadcn/ui + Tailwind
- [ ] `.env.example` with all config vars (DATABASE_URL defaults to sqlite+aiosqlite:///./sportverein.db)
- [ ] `CLAUDE.md` with build/run/test commands

### Step 2: Database Models + Migrations
- [ ] SQLAlchemy 2.0 async models: `Mitglied`, `Abteilung`, `MitgliedAbteilung`, `BeitragsKategorie`, `SepaMandat`
- [ ] `AdminUser` and `ApiToken` models for auth
- [ ] Alembic setup with initial migration
- [ ] Seed script with realistic test data (50 members, 4 departments)
- [ ] **Tests:** Model creation, relationships, constraints

### Step 3: Business Logic (Services Layer)
- [ ] `MitgliederService`: CRUD, search with filters (department, status, age group, join date), full-text search
- [ ] `BeitraegeService`: Fee calculation with pro-rata for mid-year joins, age-based tiers, category rates
- [ ] Auth service: Token generation (secrets.token_urlsafe), hashing, validation, rotation
- [ ] **Tests:** All service methods with edge cases (pro-rata calculation, search filters, token rotation)

### Step 4: REST API
- [ ] FastAPI app with auth middleware (Bearer token)
- [ ] `/api/mitglieder` — CRUD + search + bulk operations
- [ ] `/api/dashboard` — KPI aggregations (member count, trends, account balance)
- [ ] `/api/auth/login` — Admin login, returns token
- [ ] `/api/auth/tokens` — List, create, rotate, revoke API tokens
- [ ] **Tests:** All endpoints with auth, validation errors, edge cases

### Step 5: MCP Server Layer
- [ ] FastMCP server with Streamable HTTP transport
- [ ] 6 member tools: `mitglieder_suchen`, `mitglied_details`, `mitglied_anlegen`, `mitglied_aktualisieren`, `mitglied_kuendigen`, `mitglied_abteilung_zuordnen`
- [ ] MCP resources: `sportverein://mitglieder/{id}`, `sportverein://abteilungen`, `sportverein://satzung`, `sportverein://beitragsordnung`
- [ ] Bearer token auth for MCP connections
- [ ] **Tests:** Each tool end-to-end against test DB

### Step 6: Frontend — Layout + Dashboard
- [ ] App shell: collapsible sidebar (icons + labels), top header with user menu
- [ ] Sidebar nav items: Dashboard, Mitglieder, Finanzen, Kalender (disabled), Dokumente (disabled), Admin
- [ ] Login page with token input
- [ ] Dashboard page: 4 KPI cards (Mitglieder aktiv, Neue diesen Monat, Kassenstand, Offene Beiträge), member trend line chart, recent activity list
- [ ] Dark/light mode toggle
- [ ] **Tests:** Component rendering, navigation

### Step 7: Frontend — Mitglieder Page
- [ ] Data table with columns: Name, E-Mail, Abteilung(en), Status, Beitragskategorie, Eintrittsdatum
- [ ] Column sorting, text search, filters (department, status, category)
- [ ] Pagination (server-side)
- [ ] Create member dialog (form with validation)
- [ ] Edit member dialog
- [ ] Member detail sheet/panel with tabs: Stammdaten, Abteilungen, Beiträge
- [ ] Cancel membership action with confirmation
- [ ] **Tests:** Table filtering, form validation, CRUD flows

---

## Phase 2: Finance + SEPA + Documents

### Step 8: Finance Models + Services
- [ ] Models: `Buchung` (SKR42 with sphere assignment), `Rechnung`, `Zahlung`, `Spendenbescheinigung`
- [ ] `FinanzenService`: Create booking with sphere validation (ideell, zweckbetrieb, vermoegensverwaltung, wirtschaftlich)
- [ ] `BeitraegeService` extension: Generate fee run for a period, identify overdue payments, 3-level dunning
- [ ] SEPA XML generation: pain.008.001.02 format, pre-notification text
- [ ] Invoice PDF generation (simple template)
- [ ] Donation receipt (Zuwendungsbestätigung) per official pattern
- [ ] **Tests:** SEPA XML schema validation, fee calculations, sphere assignment logic

### Step 9: Finance REST API + MCP Tools
- [ ] `/api/finanzen/buchungen` — CRUD bookings
- [ ] `/api/finanzen/sepa` — Generate SEPA XML, list previous runs
- [ ] `/api/finanzen/rechnungen` — Invoices
- [ ] `/api/finanzen/beitragslaeufe` — Fee runs
- [ ] `/api/finanzen/kassenstand` — Balance by sphere
- [ ] 8 MCP finance tools: `beitraege_berechnen`, `sepa_xml_generieren`, `rechnung_erstellen`, `zahlung_verbuchen`, `mahnlauf_starten`, `spendenbescheinigung_erstellen`, `finanzbericht_erstellen`, `buchung_anlegen`
- [ ] 4 MCP communication tools: `nachricht_senden`, `newsletter_erstellen`, `dokument_generieren`, `protokoll_anlegen`
- [ ] **Tests:** All tools and endpoints

### Step 10: Frontend — Finanzen Page
- [ ] Payment status overview: pie/donut chart (paid/open/overdue/dunned) + stats cards
- [ ] Bookings table with sphere column (color-coded badges)
- [ ] SEPA generation workflow: select period → preview → generate → download XML
- [ ] Fee run view: list of calculated fees per member
- [ ] **Tests:** Chart rendering, SEPA flow, table interactions

### Step 11: Frontend — Admin Page
- [ ] API token management: table of tokens (name, created, last used, status)
- [ ] Create new token with name + expiry
- [ ] Rotate token (generates new, invalidates old)
- [ ] Revoke token with confirmation
- [ ] **Tests:** Token CRUD flows

---

## Quality Gates

Every step must pass before proceeding to the next:
1. All unit tests pass (`pytest` / `vitest`)
2. No type errors (`mypy` / `tsc --noEmit`)
3. Linter clean (`ruff` / `eslint`)
4. API endpoints return correct responses (tested via httpx)
5. MCP tools callable and return expected shapes
6. Frontend pages render without errors

After all steps complete, a QA pass validates:
- Full member lifecycle: create → edit → assign department → cancel
- Full finance lifecycle: calculate fees → generate SEPA → book payment
- Auth: login → use token → rotate → old token rejected
- Dashboard reflects real data
- All tables filter, sort, paginate correctly
- Responsive layout works at common breakpoints

---

## Key Technical Decisions

**SEPA XML**: Use `sepaxml` Python library for pain.008 generation rather than hand-rolling XML.

**PDF Generation**: `weasyprint` or `reportlab` for server-side PDF generation.

**SKR42 Spheres**: Enum-based with validation — every booking must be assigned to exactly one of the 4 tax spheres.

**Pro-rata fees**: Calculate based on remaining months in the billing period from join date. Formula: `annual_fee * remaining_months / 12`.

**Search**: SQLite `LIKE` for member search. Can be upgraded to PostgreSQL `tsvector` later if needed.

**MCP ↔ REST**: MCP tools call the same service layer as REST endpoints. No logic duplication. The MCP layer is a thin adapter.
