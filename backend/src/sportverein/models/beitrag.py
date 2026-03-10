from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sportverein.models.base import Base, TimestampMixin
from sportverein.models.mitglied import BeitragKategorie, Mitglied

import enum
from sqlalchemy import Enum


class BeitragsKategorie(TimestampMixin, Base):
    """Fee category with annual amount."""

    __tablename__ = "beitragskategorien"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    jahresbeitrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    beschreibung: Mapped[str | None] = mapped_column(String(500), default=None)


class SepaMandat(TimestampMixin, Base):
    """SEPA direct debit mandate."""

    __tablename__ = "sepa_mandate"

    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    mandatsreferenz: Mapped[str] = mapped_column(String(35), unique=True)
    iban: Mapped[str] = mapped_column(String(34))
    bic: Mapped[str | None] = mapped_column(String(11), default=None)
    kontoinhaber: Mapped[str] = mapped_column(String(200))
    unterschriftsdatum: Mapped[date] = mapped_column(Date)
    gueltig_ab: Mapped[date] = mapped_column(Date)
    gueltig_bis: Mapped[date | None] = mapped_column(Date, default=None)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    mitglied: Mapped[Mitglied] = relationship()
