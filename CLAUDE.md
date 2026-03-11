# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Klubdenker — KI-gestützte Vereinsverwaltung with MCP server, REST API, and React frontend. See `spawn_doc/idea.md` for the concept and `spawn_doc/IMPLEMENTATION_PLAN.md` for the build plan.

## Work Strategy

**Maximize parallelism.** Use subagents aggressively:
- Spawn multiple agents in parallel for independent tasks (e.g., backend models + frontend scaffolding simultaneously)
- Use background agents for long-running tasks (tests, installs) while continuing other work
- Use Explore agents for codebase research, Plan agents for architecture decisions
- After completing a major step, spawn a QA agent to test while you start the next step
- Never do sequentially what can be done in parallel

**Iterate until done.** Do not stop after writing code. Run tests, fix failures, re-run. Loop until green. If a QA agent finds issues, fix them immediately and re-validate.

**Self-validate every step.** After each implementation step:
1. Run the relevant test suite
2. Fix any failures
3. Run type checks (mypy / tsc)
4. Run linters (ruff / eslint)
5. Only move to the next step when everything passes

## Build & Run Commands

### Backend
```bash
cd backend
pip install -e ".[dev]"          # Install with dev dependencies
pytest                            # Run all tests
pytest tests/test_services/       # Run service tests only
pytest -x -q                      # Stop on first failure, quiet output
ruff check src/ tests/            # Lint
ruff format src/ tests/           # Format
mypy src/                         # Type check
uvicorn sportverein.main:app --reload  # Run dev server
alembic upgrade head              # Run migrations
alembic revision --autogenerate -m "description"  # New migration
python -m sportverein.db.seed     # Seed dev data
```

### Frontend
```bash
cd frontend
npm install                       # Install dependencies
npm run dev                       # Dev server (Vite)
npm run build                     # Production build
npm run test                      # Vitest
npm run lint                      # ESLint
npx tsc --noEmit                  # Type check
```

### Database
SQLite — no Docker needed. DB file created automatically at `backend/sportverein.db`.
Can swap to PostgreSQL later by changing `DATABASE_URL` in `.env`.

## Architecture

```
MCP Server (FastMCP)  ──┐
                        ├──→ Service Layer ──→ SQLAlchemy Models ──→ PostgreSQL
REST API (FastAPI)    ──┘
React Frontend ──→ REST API
```

- **Service layer** contains all business logic. Both MCP tools and REST endpoints call services — never duplicate logic.
- **MCP layer** (`backend/src/sportverein/mcp/`) is a thin adapter mapping tools to service calls.
- **API layer** (`backend/src/sportverein/api/`) is a thin adapter mapping HTTP endpoints to service calls.
- **Models** (`backend/src/sportverein/models/`) are SQLAlchemy 2.0 async models.

## Code Conventions

- **English** code (variables, functions, classes, comments)
- **German** user-facing strings (UI labels, error messages, tool descriptions, MCP resource names)
- Domain terms stay German in code when they are proper nouns: `Mitglied`, `Beitrag`, `Abteilung`, `Buchung`, `Satzung`
- Use async/await throughout the backend
- Pydantic models for all API request/response schemas
- SQLAlchemy 2.0 style (mapped_column, not Column)

## Key Domain Concepts

- **4 tax spheres** (Sphären): ideell, zweckbetrieb, vermoegensverwaltung, wirtschaftlich — every booking must be assigned to exactly one
- **SKR42**: Chart of accounts for German nonprofits — use as enum/reference data
- **SEPA XML**: pain.008.001.02 format for direct debit collection
- **Pro-rata fees**: `annual_fee * remaining_months / 12` for mid-year joins
- **Beitragskategorien**: erwachsene, jugend, familie, passiv, ehrenmitglied

## Auth

Phase 1-2: Bearer token auth. Tokens stored hashed in DB. Admin can create/rotate/revoke tokens via UI and API. MCP connections authenticate with the same bearer tokens.

## Frontend Style

- shadcn/ui admin dashboard pattern: collapsible sidebar, KPI cards, charts, data tables
- Dark/light mode support
- Sidebar nav: Dashboard, Mitglieder, Finanzen, Kalender (disabled), Dokumente (disabled), Admin
- Use shadcn/ui components exclusively — no custom CSS unless absolutely necessary
