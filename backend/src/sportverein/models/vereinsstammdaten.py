from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from sportverein.models.base import Base


class Vereinsstammdaten(Base):
    """Club master data — used on invoices, SEPA files, legal documents."""

    __tablename__ = "vereinsstammdaten"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    strasse: Mapped[str] = mapped_column(String(200))
    plz: Mapped[str] = mapped_column(String(10))
    ort: Mapped[str] = mapped_column(String(100))
    steuernummer: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ust_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    iban: Mapped[str] = mapped_column(String(34))
    bic: Mapped[str | None] = mapped_column(String(11), nullable=True)
    registergericht: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registernummer: Mapped[str | None] = mapped_column(String(30), nullable=True)
    freistellungsbescheid_datum: Mapped[date | None] = mapped_column(nullable=True)
    freistellungsbescheid_az: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None, onupdate=func.now(), nullable=True
    )
