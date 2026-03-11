from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Date, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sportverein.models.base import Base, TimestampMixin


class Sphare(str, enum.Enum):
    ideell = "ideell"
    zweckbetrieb = "zweckbetrieb"
    vermoegensverwaltung = "vermoegensverwaltung"
    wirtschaftlich = "wirtschaftlich"


class RechnungTyp(str, enum.Enum):
    mitgliedsbeitrag = "mitgliedsbeitrag"
    kursgebuehr = "kursgebuehr"
    hallenmiete = "hallenmiete"
    sponsoring = "sponsoring"
    sonstige = "sonstige"
    storno = "storno"
    mahnung = "mahnung"


class RechnungStatus(str, enum.Enum):
    entwurf = "entwurf"
    gestellt = "gestellt"
    faellig = "faellig"
    mahnung_1 = "mahnung_1"
    mahnung_2 = "mahnung_2"
    mahnung_3 = "mahnung_3"
    bezahlt = "bezahlt"
    teilbezahlt = "teilbezahlt"
    storniert = "storniert"
    abgeschrieben = "abgeschrieben"

    # Legacy aliases for backward compatibility
    offen = "entwurf"
    ueberfaellig = "faellig"


class EmpfaengerTyp(str, enum.Enum):
    mitglied = "mitglied"
    sponsor = "sponsor"
    extern = "extern"


class RechnungFormat(str, enum.Enum):
    pdf = "pdf"
    zugferd = "zugferd"
    xrechnung = "xrechnung"


class VersandKanal(str, enum.Enum):
    email_pdf = "email_pdf"
    email_zugferd = "email_zugferd"
    post = "post"
    portal = "portal"
    manuell = "manuell"


class Zahlungsart(str, enum.Enum):
    lastschrift = "lastschrift"
    ueberweisung = "ueberweisung"
    bar = "bar"


class Buchung(Base):
    """Booking / transaction entry."""

    __tablename__ = "buchungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    buchungsdatum: Mapped[date] = mapped_column(Date)
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    beschreibung: Mapped[str] = mapped_column(String(500))
    konto: Mapped[str] = mapped_column(String(20))
    gegenkonto: Mapped[str] = mapped_column(String(20))
    sphare: Mapped[Sphare] = mapped_column(Enum(Sphare))
    mitglied_id: Mapped[int | None] = mapped_column(ForeignKey("mitglieder.id"), default=None)
    kostenstelle_id: Mapped[int | None] = mapped_column(
        ForeignKey("kostenstellen.id"), default=None
    )
    parent_buchung_id: Mapped[int | None] = mapped_column(ForeignKey("buchungen.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Kostenstelle(TimestampMixin, Base):
    """Cost center."""

    __tablename__ = "kostenstellen"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    beschreibung: Mapped[str | None] = mapped_column(String(500), default=None)
    abteilung_id: Mapped[int | None] = mapped_column(ForeignKey("abteilungen.id"), default=None)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    freigabelimit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)


class Rechnung(Base):
    """Invoice — legally compliant per German §14 UStG."""

    __tablename__ = "rechnungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    rechnungsnummer: Mapped[str] = mapped_column(String(30), unique=True)
    mitglied_id: Mapped[int | None] = mapped_column(ForeignKey("mitglieder.id"), nullable=True)

    # -- Type & status -------------------------------------------------------
    rechnungstyp: Mapped[RechnungTyp] = mapped_column(
        Enum(RechnungTyp), default=RechnungTyp.sonstige
    )
    status: Mapped[RechnungStatus] = mapped_column(
        Enum(RechnungStatus), default=RechnungStatus.entwurf
    )
    mahnstufe: Mapped[int] = mapped_column(default=0)
    format: Mapped[RechnungFormat] = mapped_column(Enum(RechnungFormat), default=RechnungFormat.pdf)

    # -- Empfaenger (recipient) ----------------------------------------------
    empfaenger_typ: Mapped[EmpfaengerTyp] = mapped_column(
        Enum(EmpfaengerTyp), default=EmpfaengerTyp.mitglied
    )
    empfaenger_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    empfaenger_strasse: Mapped[str | None] = mapped_column(String(200), nullable=True)
    empfaenger_plz: Mapped[str | None] = mapped_column(String(10), nullable=True)
    empfaenger_ort: Mapped[str | None] = mapped_column(String(100), nullable=True)
    empfaenger_ust_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # -- Amounts (§14 UStG requires net, tax, gross) -------------------------
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # = summe_brutto
    summe_netto: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    summe_steuer: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    bezahlt_betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    offener_betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    # -- Description & service dates -----------------------------------------
    beschreibung: Mapped[str] = mapped_column(String(500))
    leistungsdatum: Mapped[date | None] = mapped_column(nullable=True)
    leistungszeitraum_von: Mapped[date | None] = mapped_column(nullable=True)
    leistungszeitraum_bis: Mapped[date | None] = mapped_column(nullable=True)

    # -- Dates ---------------------------------------------------------------
    rechnungsdatum: Mapped[date] = mapped_column(Date)
    faelligkeitsdatum: Mapped[date] = mapped_column(Date)
    zahlungsziel_tage: Mapped[int] = mapped_column(default=14)
    gestellt_am: Mapped[datetime | None] = mapped_column(nullable=True)
    bezahlt_am: Mapped[datetime | None] = mapped_column(nullable=True)

    # -- Tax sphere & hints --------------------------------------------------
    sphaere: Mapped[str | None] = mapped_column(String(30), nullable=True)
    steuerhinweis_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- Payment & SEPA reference -------------------------------------------
    verwendungszweck: Mapped[str | None] = mapped_column(String(140), nullable=True)

    # -- Storno (cancellation) reference ------------------------------------
    storno_von_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)

    # -- DSGVO: retention period --------------------------------------------
    loeschdatum: Mapped[date | None] = mapped_column(nullable=True)

    # -- Skonto (cash discount) ---------------------------------------------
    skonto_prozent: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    skonto_frist_tage: Mapped[int | None] = mapped_column(nullable=True)
    skonto_betrag: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # -- Versand (dispatch tracking) ----------------------------------------
    versand_kanal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    versendet_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    versendet_an: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # -- Timestamps ----------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(default=None, onupdate=func.now())

    # -- Relationships -------------------------------------------------------
    zahlungen: Mapped[list[Zahlung]] = relationship(back_populates="rechnung")
    positionen: Mapped[list[Rechnungsposition]] = relationship(
        back_populates="rechnung", cascade="all, delete-orphan"
    )

    @property
    def summe_brutto(self) -> Decimal:
        """Alias: summe_brutto == betrag."""
        return self.betrag

    @summe_brutto.setter
    def summe_brutto(self, value: Decimal) -> None:
        self.betrag = value


class Rechnungsposition(Base):
    """Invoice line item."""

    __tablename__ = "rechnungspositionen"

    id: Mapped[int] = mapped_column(primary_key=True)
    rechnung_id: Mapped[int] = mapped_column(ForeignKey("rechnungen.id"))
    position_nr: Mapped[int] = mapped_column()
    beschreibung: Mapped[str] = mapped_column(Text)
    menge: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("1"))
    einheit: Mapped[str] = mapped_column(String(20), default="x")
    einzelpreis_netto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    steuersatz: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    steuerbefreiungsgrund: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gesamtpreis_netto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    gesamtpreis_steuer: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    gesamtpreis_brutto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    kostenstelle_id: Mapped[int | None] = mapped_column(
        ForeignKey("kostenstellen.id"), nullable=True
    )

    rechnung: Mapped[Rechnung] = relationship(back_populates="positionen")


class Zahlung(Base):
    """Payment against an invoice."""

    __tablename__ = "zahlungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    rechnung_id: Mapped[int] = mapped_column(ForeignKey("rechnungen.id"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    zahlungsdatum: Mapped[date] = mapped_column(Date)
    zahlungsart: Mapped[Zahlungsart] = mapped_column(Enum(Zahlungsart))
    referenz: Mapped[str | None] = mapped_column(String(100), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    rechnung: Mapped[Rechnung] = relationship(back_populates="zahlungen")


class EingangsrechnungStatus(str, enum.Enum):
    eingegangen = "eingegangen"
    geprueft = "geprueft"
    freigegeben = "freigegeben"
    bezahlt = "bezahlt"
    abgelehnt = "abgelehnt"


class EingangsrechnungFormat(str, enum.Enum):
    xrechnung = "xrechnung"
    zugferd = "zugferd"
    manuell = "manuell"


class Eingangsrechnung(Base):
    """Incoming invoice (E-Rechnung) — XRechnung / ZUGFeRD."""

    __tablename__ = "eingangsrechnungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    rechnungsnummer: Mapped[str] = mapped_column(String(50))  # external invoice number
    aussteller_name: Mapped[str] = mapped_column(String(200))
    aussteller_strasse: Mapped[str | None] = mapped_column(String(200), nullable=True)
    aussteller_plz: Mapped[str | None] = mapped_column(String(10), nullable=True)
    aussteller_ort: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aussteller_steuernr: Mapped[str | None] = mapped_column(String(30), nullable=True)
    aussteller_ust_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    rechnungsdatum: Mapped[date] = mapped_column(Date)
    faelligkeitsdatum: Mapped[date | None] = mapped_column(Date, nullable=True)
    leistungsdatum: Mapped[date | None] = mapped_column(Date, nullable=True)

    summe_netto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    summe_steuer: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    summe_brutto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    waehrung: Mapped[str] = mapped_column(String(3), default="EUR")

    status: Mapped[EingangsrechnungStatus] = mapped_column(
        Enum(EingangsrechnungStatus), default=EingangsrechnungStatus.eingegangen
    )
    kostenstelle_id: Mapped[int | None] = mapped_column(
        ForeignKey("kostenstellen.id"), nullable=True
    )
    sphaere: Mapped[str | None] = mapped_column(String(30), nullable=True)

    quell_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quell_xml: Mapped[str | None] = mapped_column(Text, nullable=True)

    notiz: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None, onupdate=func.now(), nullable=True
    )


class Spendenbescheinigung(Base):
    """Donation receipt."""

    __tablename__ = "spendenbescheinigungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    ausstellungsdatum: Mapped[date] = mapped_column(Date)
    zweck: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
