from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sportverein.models.base import Base


class Sphare(str, enum.Enum):
    ideell = "ideell"
    zweckbetrieb = "zweckbetrieb"
    vermoegensverwaltung = "vermoegensverwaltung"
    wirtschaftlich = "wirtschaftlich"


class RechnungStatus(str, enum.Enum):
    offen = "offen"
    bezahlt = "bezahlt"
    ueberfaellig = "ueberfaellig"
    storniert = "storniert"


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
    mitglied_id: Mapped[int | None] = mapped_column(
        ForeignKey("mitglieder.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Rechnung(Base):
    """Invoice."""

    __tablename__ = "rechnungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    rechnungsnummer: Mapped[str] = mapped_column(String(20), unique=True)
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    beschreibung: Mapped[str] = mapped_column(String(500))
    rechnungsdatum: Mapped[date] = mapped_column(Date)
    faelligkeitsdatum: Mapped[date] = mapped_column(Date)
    status: Mapped[RechnungStatus] = mapped_column(
        Enum(RechnungStatus), default=RechnungStatus.offen
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None, onupdate=func.now()
    )

    zahlungen: Mapped[list[Zahlung]] = relationship(back_populates="rechnung")


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


class Spendenbescheinigung(Base):
    """Donation receipt."""

    __tablename__ = "spendenbescheinigungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    ausstellungsdatum: Mapped[date] = mapped_column(Date)
    zweck: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
