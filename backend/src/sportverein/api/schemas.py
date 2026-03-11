"""Pydantic response/request schemas for the REST API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

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
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AbteilungCreate(BaseModel):
    name: str
    beschreibung: str | None = None


class AbteilungUpdate(BaseModel):
    name: str | None = None
    beschreibung: str | None = None


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
# Vorstand Dashboard schemas
# ---------------------------------------------------------------------------


class VorstandKPIs(BaseModel):
    active_members: int
    total_balance: float
    open_fees_count: int
    open_fees_amount: float
    compliance_score: float


class MemberTrendPoint(BaseModel):
    month: str
    total: int
    by_department: dict[str, int]


class CashflowPoint(BaseModel):
    month: str
    income: float
    expenses: float


class OpenAction(BaseModel):
    type: str
    title: str
    detail: str
    severity: str


class VorstandDashboardResponse(BaseModel):
    kpis: VorstandKPIs
    member_trend: list[MemberTrendPoint]
    cashflow: list[CashflowPoint]
    open_actions: list[OpenAction]


# ---------------------------------------------------------------------------
# Schatzmeister Dashboard schemas
# ---------------------------------------------------------------------------


class SepaHero(BaseModel):
    ready_count: int
    total_count: int
    total_amount: float
    exceptions: int


class FinanceKPIs(BaseModel):
    balance_ideell: float
    balance_zweckbetrieb: float
    balance_vermoegensverwaltung: float
    balance_wirtschaftlich: float
    open_receivables: float
    pending_transfers: int


class OffenerPosten(BaseModel):
    member_name: str
    department: str
    amount: float
    days_overdue: int
    dunning_level: int


class BudgetBurnItem(BaseModel):
    name: str
    budget: float
    spent: float
    percentage: float
    department_color: str


class LiquidityPoint(BaseModel):
    month: str
    income: float
    expenses: float


class SchatzmeisterDashboardResponse(BaseModel):
    sepa_hero: SepaHero
    kpis: FinanceKPIs
    open_items: list[OffenerPosten]
    budget_burn: list[BudgetBurnItem]
    liquidity: list[LiquidityPoint]


# ---------------------------------------------------------------------------
# Spartenleiter Dashboard schemas
# ---------------------------------------------------------------------------


class SpartenleiterKPIs(BaseModel):
    member_count: int
    avg_attendance_pct: float
    budget_utilization_pct: float
    risk_count: int


class HeatmapRow(BaseModel):
    day: int
    cells: list[int]


class TrainingItem(BaseModel):
    group: str
    trainer: str
    registered: int
    max_participants: int
    weekday: str
    time: str


class RiskMember(BaseModel):
    member_id: int
    name: str
    reason: str


class BudgetDonut(BaseModel):
    used: float
    committed: float
    free: float


class SpartenleiterDashboardResponse(BaseModel):
    kpis: SpartenleiterKPIs
    attendance_heatmap: list[HeatmapRow]
    training_schedule: list[TrainingItem]
    risk_members: list[RiskMember]
    budget_donut: BudgetDonut


# ---------------------------------------------------------------------------
# Finance schemas
# ---------------------------------------------------------------------------


class RechnungTemplatePositionResponse(BaseModel):
    beschreibung: str
    menge: float
    einheit: str
    einzelpreis_netto: float | None = None
    steuersatz: float
    steuerbefreiungsgrund: str | None = None
    platzhalter: dict[str, str] | None = None


class RechnungTemplateResponse(BaseModel):
    id: str
    name: str
    beschreibung: str
    rechnungstyp: str
    sphaere: str | None = None
    empfaenger_typ: str | None = None
    steuerhinweis_text: str | None = None
    zahlungsziel_tage: int
    positionen: list[RechnungTemplatePositionResponse]


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


class RechnungspositionCreate(BaseModel):
    beschreibung: str
    menge: float = 1.0
    einheit: str = "x"
    einzelpreis_netto: float
    steuersatz: float = 0.0
    steuerbefreiungsgrund: str | None = None
    kostenstelle_id: int | None = None


class RechnungspositionResponse(BaseModel):
    id: int
    rechnung_id: int
    position_nr: int
    beschreibung: str
    menge: float
    einheit: str
    einzelpreis_netto: float
    steuersatz: float
    steuerbefreiungsgrund: str | None = None
    gesamtpreis_netto: float
    gesamtpreis_steuer: float
    gesamtpreis_brutto: float
    kostenstelle_id: int | None = None

    model_config = {"from_attributes": True}


class RechnungCreate(BaseModel):
    mitglied_id: int | None = None
    betrag: float | None = None
    beschreibung: str = ""
    faelligkeitsdatum: date | None = None
    rechnungsdatum: date | None = None
    rechnungstyp: str = "sonstige"
    empfaenger_typ: str = "mitglied"
    empfaenger_name: str | None = None
    empfaenger_strasse: str | None = None
    empfaenger_plz: str | None = None
    empfaenger_ort: str | None = None
    empfaenger_ust_id: str | None = None
    leistungsdatum: date | None = None
    leistungszeitraum_von: date | None = None
    leistungszeitraum_bis: date | None = None
    sphaere: str | None = None
    steuerhinweis_text: str | None = None
    zahlungsziel_tage: int = 14
    positionen: list[RechnungspositionCreate] = []
    format: str = "pdf"
    skonto_prozent: float | None = None
    skonto_frist_tage: int | None = None


class RechnungResponse(BaseModel):
    id: int
    rechnungsnummer: str
    mitglied_id: int | None = None
    betrag: float
    beschreibung: str
    rechnungsdatum: date
    faelligkeitsdatum: date
    status: str
    rechnungstyp: str | None = None
    mahnstufe: int = 0
    empfaenger_typ: str | None = None
    empfaenger_name: str | None = None
    empfaenger_strasse: str | None = None
    empfaenger_plz: str | None = None
    empfaenger_ort: str | None = None
    empfaenger_ust_id: str | None = None
    summe_netto: float | None = None
    summe_steuer: float | None = None
    bezahlt_betrag: float | None = None
    offener_betrag: float | None = None
    leistungsdatum: date | None = None
    leistungszeitraum_von: date | None = None
    leistungszeitraum_bis: date | None = None
    sphaere: str | None = None
    steuerhinweis_text: str | None = None
    zahlungsziel_tage: int | None = None
    verwendungszweck: str | None = None
    storno_von_id: int | None = None
    loeschdatum: date | None = None
    gestellt_am: datetime | None = None
    bezahlt_am: datetime | None = None
    format: str | None = None
    skonto_prozent: float | None = None
    skonto_frist_tage: int | None = None
    skonto_betrag: float | None = None
    versand_kanal: str | None = None
    versendet_am: datetime | None = None
    versendet_an: str | None = None
    positionen: list[RechnungspositionResponse] = []

    model_config = {"from_attributes": True}


class RechnungListResponse(BaseModel):
    items: list[RechnungResponse]
    total: int
    page: int
    page_size: int


class StornoRequest(BaseModel):
    grund: str | None = None


class VersandRequest(BaseModel):
    kanal: str
    empfaenger: str


class ZahlungCreate(BaseModel):
    betrag: float
    zahlungsart: str = "ueberweisung"
    referenz: str | None = None
    apply_skonto: bool = False


class ZahlungResponse(BaseModel):
    id: int
    rechnung_id: int
    betrag: float
    zahlungsdatum: date
    zahlungsart: str
    referenz: str | None = None

    model_config = {"from_attributes": True}


class SkontoInfoResponse(BaseModel):
    skonto_betrag: float
    zahlbetrag: float
    skonto_frist_bis: date | None = None
    skonto_verfuegbar: bool
    skonto_prozent: float


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


# ---------------------------------------------------------------------------
# BeitragsKategorie schemas
# ---------------------------------------------------------------------------


class BeitragsKategorieResponse(BaseModel):
    id: int
    name: str
    jahresbeitrag: float
    beschreibung: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BeitragsKategorieCreate(BaseModel):
    name: str
    jahresbeitrag: float
    beschreibung: str | None = None


class BeitragsKategorieUpdate(BaseModel):
    jahresbeitrag: float | None = None
    beschreibung: str | None = None


# ---------------------------------------------------------------------------
# Kostenstelle schemas
# ---------------------------------------------------------------------------


class KostenstelleCreate(BaseModel):
    name: str
    beschreibung: str | None = None
    abteilung_id: int | None = None
    budget: float | None = None
    freigabelimit: float | None = None


class KostenstelleUpdate(BaseModel):
    name: str | None = None
    beschreibung: str | None = None
    abteilung_id: int | None = None
    budget: float | None = None
    freigabelimit: float | None = None


class KostenstelleResponse(BaseModel):
    id: int
    name: str
    beschreibung: str | None = None
    abteilung_id: int | None = None
    budget: float | None = None
    freigabelimit: float | None = None

    model_config = {"from_attributes": True}


class KostenstelleBudgetResponse(BaseModel):
    kostenstelle_id: int
    name: str
    budget: float
    spent: float
    remaining: float
    freigabelimit: float | None = None


# ---------------------------------------------------------------------------
# Leistungsverrechnung schemas
# ---------------------------------------------------------------------------


class AllocationItem(BaseModel):
    kostenstelle_id: int
    anteil: float
    beschreibung: str | None = None


class LeistungsverrechnungRequest(BaseModel):
    buchung_id: int
    allocations: list[AllocationItem]


class LeistungsverrechnungResponse(BaseModel):
    parent_buchung_id: int
    children: list[BuchungResponse]


# ---------------------------------------------------------------------------
# Agent schemas
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Training schemas
# ---------------------------------------------------------------------------


class TrainingsgruppeCreate(BaseModel):
    name: str
    abteilung_id: int
    wochentag: str
    uhrzeit: str
    trainer: str | None = None
    dauer_minuten: int = 90
    max_teilnehmer: int | None = None
    ort: str | None = None


class TrainingsgruppeUpdate(BaseModel):
    name: str | None = None
    abteilung_id: int | None = None
    wochentag: str | None = None
    uhrzeit: str | None = None
    trainer: str | None = None
    dauer_minuten: int | None = None
    max_teilnehmer: int | None = None
    ort: str | None = None
    aktiv: bool | None = None


class TrainingsgruppeResponse(BaseModel):
    id: int
    name: str
    abteilung_id: int
    trainer: str | None = None
    wochentag: str
    uhrzeit: str
    dauer_minuten: int
    max_teilnehmer: int | None = None
    ort: str | None = None
    aktiv: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnwesenheitRecord(BaseModel):
    mitglied_id: int
    anwesend: bool = True
    notiz: str | None = None


class AnwesenheitCreate(BaseModel):
    trainingsgruppe_id: int
    datum: date
    teilnehmer: list[AnwesenheitRecord]


class AnwesenheitResponse(BaseModel):
    id: int
    trainingsgruppe_id: int
    mitglied_id: int
    datum: date
    anwesend: bool
    notiz: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AnwesenheitHeatmapRow(BaseModel):
    day: int
    cells: list[int]


class AnwesenheitStatistik(BaseModel):
    heatmap: list[AnwesenheitHeatmapRow]
    total_sessions: int
    total_present: int
    avg_attendance_pct: float


class MitgliedAnwesenheitResponse(BaseModel):
    mitglied_id: int
    wochen: int
    total_eintraege: int
    anwesend: int
    abwesend: int
    anwesenheit_pct: float


# ---------------------------------------------------------------------------
# Trainer License schemas
# ---------------------------------------------------------------------------


class TrainerLizenzCreate(BaseModel):
    mitglied_id: int
    lizenztyp: str
    bezeichnung: str
    ausstellungsdatum: date
    ablaufdatum: date
    lizenznummer: str | None = None
    ausstellende_stelle: str | None = None


class TrainerLizenzResponse(BaseModel):
    id: int
    mitglied_id: int
    lizenztyp: str
    bezeichnung: str
    ausstellungsdatum: date
    ablaufdatum: date
    lizenznummer: str | None = None
    ausstellende_stelle: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TrainerLizenzListResponse(BaseModel):
    items: list[TrainerLizenzResponse]
    total: int


class BeitragseinzugRequest(BaseModel):
    year: int
    month: int


class BeitragseinzugResponse(BaseModel):
    year: int
    month: int
    fees_calculated: int
    invoices_created: int
    sepa_ready: int
    missing_mandate: list[dict[str, Any]]
    sepa_xml: str | None = None


class MahnwesenReportItem(BaseModel):
    mahnstufe: int
    action: str
    count: int
    rechnungen: list[dict[str, Any]]


class MahnwesenResponse(BaseModel):
    total_overdue: int
    report: list[MahnwesenReportItem]


class AufwandMonitorResponse(BaseModel):
    year: int
    warnings: list[dict[str, Any]]
    count: int


class ComplianceFinding(BaseModel):
    category: str
    severity: str
    message: str
    affected_count: int


class ComplianceMonitorResponse(BaseModel):
    findings: list[ComplianceFinding]
    total: int
    critical_count: int
    warning_count: int
    info_count: int


# ---------------------------------------------------------------------------
# Ehrenamt (volunteer compensation) schemas
# ---------------------------------------------------------------------------


class AufwandsentschaedigungCreate(BaseModel):
    mitglied_id: int
    betrag: float
    datum: date
    typ: str  # "uebungsleiter" or "ehrenamt"
    beschreibung: str


class AufwandsentschaedigungResponse(BaseModel):
    id: int
    mitglied_id: int
    mitglied_name: str
    betrag: float
    datum: date
    typ: str
    beschreibung: str
    created_at: datetime | None = None


class AufwandsentschaedigungListResponse(BaseModel):
    items: list[AufwandsentschaedigungResponse]
    total: int


class FreibetragSummary(BaseModel):
    mitglied_id: int
    mitglied_name: str
    typ: str
    total: float
    limit: float
    remaining: float
    percent: float
    warning: bool


class FreibetragSummaryResponse(BaseModel):
    year: int
    items: list[FreibetragSummary]


# ---------------------------------------------------------------------------
# EÜR (Einnahmen-Überschuss-Rechnung) schemas
# ---------------------------------------------------------------------------


class EuerZeitraum(BaseModel):
    von: str
    bis: str


class EuerSumme(BaseModel):
    einnahmen: float
    ausgaben: float
    ergebnis: float


class EuerSphareItem(BaseModel):
    sphare: str
    einnahmen: float
    ausgaben: float
    ergebnis: float


class EuerMonatItem(BaseModel):
    monat: str
    einnahmen: float
    ausgaben: float
    ergebnis: float


class EuerKostenstelleItem(BaseModel):
    kostenstelle: str
    einnahmen: float
    ausgaben: float
    ergebnis: float


class EuerReportResponse(BaseModel):
    jahr: int
    zeitraum: EuerZeitraum
    gesamt: EuerSumme
    nach_sphare: list[EuerSphareItem]
    nach_monat: list[EuerMonatItem]
    nach_kostenstelle: list[EuerKostenstelleItem]


# ---------------------------------------------------------------------------
# SEPA Mandat schemas
# ---------------------------------------------------------------------------


class SepaMandatCreate(BaseModel):
    mitglied_id: int
    iban: str
    bic: str | None = None
    kontoinhaber: str
    mandatsreferenz: str
    unterschriftsdatum: date
    gueltig_ab: date
    gueltig_bis: date | None = None


class SepaMandatUpdate(BaseModel):
    iban: str | None = None
    bic: str | None = None
    kontoinhaber: str | None = None
    mandatsreferenz: str | None = None
    unterschriftsdatum: date | None = None
    gueltig_ab: date | None = None
    gueltig_bis: date | None = None


class SepaMandatResponse(BaseModel):
    id: int
    mitglied_id: int
    mitglied_name: str | None = None
    iban: str
    bic: str | None = None
    kontoinhaber: str
    mandatsreferenz: str
    unterschriftsdatum: date
    gueltig_ab: date
    gueltig_bis: date | None = None
    aktiv: bool

    model_config = {"from_attributes": True}


class SepaMandatListResponse(BaseModel):
    items: list[SepaMandatResponse]
    total: int


# ---------------------------------------------------------------------------
# Vereinsstammdaten schemas
# ---------------------------------------------------------------------------


class VereinsstammdatenCreate(BaseModel):
    name: str
    strasse: str
    plz: str
    ort: str
    steuernummer: str | None = None
    ust_id: str | None = None
    iban: str
    bic: str | None = None
    registergericht: str | None = None
    registernummer: str | None = None
    freistellungsbescheid_datum: date | None = None
    freistellungsbescheid_az: str | None = None


class VereinsstammdatenUpdate(BaseModel):
    name: str | None = None
    strasse: str | None = None
    plz: str | None = None
    ort: str | None = None
    steuernummer: str | None = None
    ust_id: str | None = None
    iban: str | None = None
    bic: str | None = None
    registergericht: str | None = None
    registernummer: str | None = None
    freistellungsbescheid_datum: date | None = None
    freistellungsbescheid_az: str | None = None


class VereinsstammdatenResponse(BaseModel):
    id: int
    name: str
    strasse: str
    plz: str
    ort: str
    steuernummer: str | None = None
    ust_id: str | None = None
    iban: str
    bic: str | None = None
    registergericht: str | None = None
    registernummer: str | None = None
    freistellungsbescheid_datum: date | None = None
    freistellungsbescheid_az: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Eingangsrechnung (incoming e-invoice) schemas
# ---------------------------------------------------------------------------


class EingangsrechnungResponse(BaseModel):
    id: int
    rechnungsnummer: str
    aussteller_name: str
    aussteller_strasse: str | None = None
    aussteller_plz: str | None = None
    aussteller_ort: str | None = None
    aussteller_steuernr: str | None = None
    aussteller_ust_id: str | None = None
    rechnungsdatum: date
    faelligkeitsdatum: date | None = None
    leistungsdatum: date | None = None
    summe_netto: float
    summe_steuer: float
    summe_brutto: float
    waehrung: str = "EUR"
    status: str
    kostenstelle_id: int | None = None
    sphaere: str | None = None
    quell_format: str | None = None
    notiz: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class EingangsrechnungDetailResponse(EingangsrechnungResponse):
    quell_xml: str | None = None
    updated_at: datetime | None = None


class EingangsrechnungListResponse(BaseModel):
    items: list[EingangsrechnungResponse]
    total: int
    page: int
    page_size: int


class EingangsrechnungUploadResponse(BaseModel):
    rechnung: EingangsrechnungResponse
    warnungen: list[str] = []


class EingangsrechnungStatusUpdate(BaseModel):
    status: str
    notiz: str | None = None


# ---------------------------------------------------------------------------
# Protokoll schemas
# ---------------------------------------------------------------------------


class ProtokollCreate(BaseModel):
    titel: str
    datum: str
    inhalt: str
    typ: Literal["vorstandssitzung", "mitgliederversammlung", "abteilungssitzung", "sonstige"] = (
        "sonstige"
    )
    erstellt_von: str | None = None
    teilnehmer: str | None = None
    beschluesse: str | None = None


class ProtokollUpdate(BaseModel):
    titel: str | None = None
    datum: str | None = None
    inhalt: str | None = None
    typ: str | None = None
    erstellt_von: str | None = None
    teilnehmer: str | None = None
    beschluesse: str | None = None


class ProtokollResponse(BaseModel):
    id: int
    titel: str
    datum: str
    inhalt: str
    typ: str
    erstellt_von: str | None = None
    teilnehmer: str | None = None
    beschluesse: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProtokollListResponse(BaseModel):
    items: list[ProtokollResponse]
    total: int
    page: int
    page_size: int
