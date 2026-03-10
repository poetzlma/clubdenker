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


# ---------------------------------------------------------------------------
# Finance schemas
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Audit schemas
# ---------------------------------------------------------------------------


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    details: str | None = None
    ip_address: str | None = None

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# DSGVO schemas
# ---------------------------------------------------------------------------


class EinwilligungRequest(BaseModel):
    consent: bool


class DsgvoAuskunftResponse(BaseModel):
    personal_data: dict[str, Any]
    departments: list[dict[str, Any]]
    invoices: list[dict[str, Any]]
    payments: list[dict[str, Any]]
    sepa_mandates: list[dict[str, Any]]
    audit_log: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Finance schemas
# ---------------------------------------------------------------------------


class BuchungCreate(BaseModel):
    buchungsdatum: date
    betrag: float
    beschreibung: str
    konto: str
    gegenkonto: str
    sphare: str
    mitglied_id: int | None = None


class BuchungResponse(BaseModel):
    id: int
    buchungsdatum: date
    betrag: float
    beschreibung: str
    konto: str
    gegenkonto: str
    sphare: str
    mitglied_id: int | None = None

    model_config = {"from_attributes": True}


class BuchungListResponse(BaseModel):
    items: list[BuchungResponse]
    total: int
    page: int
    page_size: int


class RechnungCreate(BaseModel):
    mitglied_id: int
    betrag: float
    beschreibung: str
    faelligkeitsdatum: date
    rechnungsdatum: date | None = None


class RechnungResponse(BaseModel):
    id: int
    rechnungsnummer: str
    mitglied_id: int
    betrag: float
    beschreibung: str
    rechnungsdatum: date
    faelligkeitsdatum: date
    status: str

    model_config = {"from_attributes": True}


class RechnungListResponse(BaseModel):
    items: list[RechnungResponse]
    total: int
    page: int
    page_size: int


class ZahlungCreate(BaseModel):
    betrag: float
    zahlungsart: str = "ueberweisung"
    referenz: str | None = None


class ZahlungResponse(BaseModel):
    id: int
    rechnung_id: int
    betrag: float
    zahlungsdatum: date
    zahlungsart: str
    referenz: str | None = None

    model_config = {"from_attributes": True}


class SepaRequest(BaseModel):
    rechnungen_ids: list[int]


class SepaResponse(BaseModel):
    xml: str
    count: int


class KassenstandSphare(BaseModel):
    sphare: str
    betrag: float


class KassenstandResponse(BaseModel):
    by_sphere: list[KassenstandSphare]
    total: float


class MahnungResponse(BaseModel):
    id: int
    rechnungsnummer: str
    mitglied_id: int
    betrag: float
    beschreibung: str
    rechnungsdatum: date
    faelligkeitsdatum: date
    status: str

    model_config = {"from_attributes": True}


class BeitragslaufRequest(BaseModel):
    billing_year: int
