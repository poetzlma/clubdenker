"""Protokoll (meeting minutes) model."""

from __future__ import annotations

import enum

from sqlalchemy import Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from sportverein.models.base import Base, TimestampMixin


class ProtokollTyp(str, enum.Enum):
    vorstandssitzung = "vorstandssitzung"
    mitgliederversammlung = "mitgliederversammlung"
    abteilungssitzung = "abteilungssitzung"
    sonstige = "sonstige"


class Protokoll(TimestampMixin, Base):
    """Meeting minutes / protocol record."""

    __tablename__ = "protokolle"

    titel: Mapped[str] = mapped_column()
    datum: Mapped[str] = mapped_column()  # ISO date string
    inhalt: Mapped[str] = mapped_column(Text)
    typ: Mapped[ProtokollTyp] = mapped_column(Enum(ProtokollTyp), default=ProtokollTyp.sonstige)
    erstellt_von: Mapped[str | None] = mapped_column(default=None)
    teilnehmer: Mapped[str | None] = mapped_column(Text, default=None)
    beschluesse: Mapped[str | None] = mapped_column(Text, default=None)
