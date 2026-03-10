"""Training group and attendance models."""

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
