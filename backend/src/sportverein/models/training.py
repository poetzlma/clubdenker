"""Training group, attendance, and trainer license models."""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum as SQLEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sportverein.models.base import Base, TimestampMixin


class Wochentag(str, enum.Enum):
    montag = "montag"
    dienstag = "dienstag"
    mittwoch = "mittwoch"
    donnerstag = "donnerstag"
    freitag = "freitag"
    samstag = "samstag"
    sonntag = "sonntag"


class Lizenztyp(str, enum.Enum):
    trainerlizenz_c = "trainerlizenz_c"
    trainerlizenz_b = "trainerlizenz_b"
    trainerlizenz_a = "trainerlizenz_a"
    erste_hilfe = "erste_hilfe"
    jugendleiter = "jugendleiter"
    rettungsschwimmer = "rettungsschwimmer"
    sonstiges = "sonstiges"


class Trainingsgruppe(TimestampMixin, Base):
    __tablename__ = "trainingsgruppen"

    name: Mapped[str] = mapped_column(String(200))
    abteilung_id: Mapped[int] = mapped_column(ForeignKey("abteilungen.id"))
    trainer: Mapped[str | None] = mapped_column(String(200), default=None)
    wochentag: Mapped[Wochentag] = mapped_column(SQLEnum(Wochentag))
    uhrzeit: Mapped[str] = mapped_column(String(5))  # "18:30"
    dauer_minuten: Mapped[int] = mapped_column(default=90)
    max_teilnehmer: Mapped[int | None] = mapped_column(nullable=True, default=None)
    ort: Mapped[str | None] = mapped_column(String(200), default=None)
    aktiv: Mapped[bool] = mapped_column(default=True)


class TrainerLizenz(TimestampMixin, Base):
    __tablename__ = "trainer_lizenzen"

    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    lizenztyp: Mapped[Lizenztyp] = mapped_column(SQLEnum(Lizenztyp))
    bezeichnung: Mapped[str] = mapped_column(String(300))
    ausstellungsdatum: Mapped[date] = mapped_column(Date)
    ablaufdatum: Mapped[date] = mapped_column(Date)
    lizenznummer: Mapped[str | None] = mapped_column(String(100), default=None)
    ausstellende_stelle: Mapped[str | None] = mapped_column(String(300), default=None)


class Anwesenheit(TimestampMixin, Base):
    __tablename__ = "anwesenheiten"
    __table_args__ = (
        UniqueConstraint(
            "trainingsgruppe_id",
            "mitglied_id",
            "datum",
            name="uq_anwesenheit_gruppe_mitglied_datum",
        ),
    )

    trainingsgruppe_id: Mapped[int] = mapped_column(ForeignKey("trainingsgruppen.id"))
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    datum: Mapped[date] = mapped_column(Date)
    anwesend: Mapped[bool] = mapped_column(default=True)
    notiz: Mapped[str | None] = mapped_column(String(500), default=None)
