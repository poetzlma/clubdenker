from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sportverein.models.base import Base, TimestampMixin


class MitgliedStatus(str, enum.Enum):
    aktiv = "aktiv"
    passiv = "passiv"
    gekuendigt = "gekuendigt"
    ehrenmitglied = "ehrenmitglied"


class BeitragKategorie(str, enum.Enum):
    erwachsene = "erwachsene"
    jugend = "jugend"
    familie = "familie"
    passiv = "passiv"
    ehrenmitglied = "ehrenmitglied"


class Abteilung(TimestampMixin, Base):
    __tablename__ = "abteilungen"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    beschreibung: Mapped[str | None] = mapped_column(String(500), default=None)

    mitglieder: Mapped[list[MitgliedAbteilung]] = relationship(
        back_populates="abteilung"
    )


class Mitglied(TimestampMixin, Base):
    __tablename__ = "mitglieder"

    mitgliedsnummer: Mapped[str] = mapped_column(String(20), unique=True)
    vorname: Mapped[str] = mapped_column(String(100))
    nachname: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    telefon: Mapped[str | None] = mapped_column(String(50), default=None)
    geburtsdatum: Mapped[date] = mapped_column(Date)
    strasse: Mapped[str | None] = mapped_column(String(200), default=None)
    plz: Mapped[str | None] = mapped_column(String(10), default=None)
    ort: Mapped[str | None] = mapped_column(String(100), default=None)
    eintrittsdatum: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    austrittsdatum: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[MitgliedStatus] = mapped_column(
        Enum(MitgliedStatus), default=MitgliedStatus.aktiv
    )
    beitragskategorie: Mapped[BeitragKategorie] = mapped_column(
        Enum(BeitragKategorie), default=BeitragKategorie.erwachsene
    )
    notizen: Mapped[str | None] = mapped_column(Text, default=None)

    abteilungen: Mapped[list[MitgliedAbteilung]] = relationship(
        back_populates="mitglied"
    )


class MitgliedAbteilung(Base):
    __tablename__ = "mitglied_abteilungen"
    __table_args__ = (
        UniqueConstraint("mitglied_id", "abteilung_id", name="uq_mitglied_abteilung"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    abteilung_id: Mapped[int] = mapped_column(ForeignKey("abteilungen.id"))
    beitrittsdatum: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    mitglied: Mapped[Mitglied] = relationship(back_populates="abteilungen")
    abteilung: Mapped[Abteilung] = relationship(back_populates="mitglieder")
