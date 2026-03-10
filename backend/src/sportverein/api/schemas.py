"""Pydantic response/request schemas for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class AdminResponse(BaseModel):
    id: int
    email: str
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: AdminResponse


class TokenCreateRequest(BaseModel):
    name: str
    expires_in_hours: int | None = None


class TokenCreateResponse(BaseModel):
    token: str
    id: int
    name: str


class TokenResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Member schemas
# ---------------------------------------------------------------------------


class AbteilungResponse(BaseModel):
    id: int
    name: str
    beschreibung: str | None = None

    model_config = {"from_attributes": True}


class MitgliedAbteilungResponse(BaseModel):
    abteilung_id: int
    abteilung_name: str
    beitrittsdatum: date


class MitgliedResponse(BaseModel):
    id: int
    mitgliedsnummer: str
    vorname: str
    nachname: str
    email: str
    telefon: str | None = None
    geburtsdatum: date
    strasse: str | None = None
    plz: str | None = None
    ort: str | None = None
    eintrittsdatum: date
    austrittsdatum: date | None = None
    status: str
    beitragskategorie: str
    notizen: str | None = None
    abteilungen: list[MitgliedAbteilungResponse] = []

    model_config = {"from_attributes": True}


class MitgliedListResponse(BaseModel):
    items: list[MitgliedResponse]
    total: int
    page: int
    page_size: int


class KuendigenRequest(BaseModel):
    austrittsdatum: date | None = None


# ---------------------------------------------------------------------------
# Dashboard schemas
# ---------------------------------------------------------------------------


class DashboardStats(BaseModel):
    total_active: int
    total_passive: int
    new_this_month: int
    by_department: dict[str, int]
    financial_summary: dict[str, Any] = {}


class ActivityItem(BaseModel):
    type: str
    description: str
    timestamp: str


class RecentActivityResponse(BaseModel):
    items: list[ActivityItem]
