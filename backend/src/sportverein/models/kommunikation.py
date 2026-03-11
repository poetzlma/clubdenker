from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sportverein.models.base import Base


class NachrichtTyp(str, enum.Enum):
    email = "email"
    brief = "brief"


class EmpfaengerStatus(str, enum.Enum):
    ausstehend = "ausstehend"
    gesendet = "gesendet"
    fehlgeschlagen = "fehlgeschlagen"


class Nachricht(Base):
    """Message."""

    __tablename__ = "nachrichten"

    id: Mapped[int] = mapped_column(primary_key=True)
    betreff: Mapped[str] = mapped_column(String(300))
    inhalt: Mapped[str] = mapped_column(Text)
    typ: Mapped[NachrichtTyp] = mapped_column(Enum(NachrichtTyp))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    gesendet_am: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    empfaenger: Mapped[list[NachrichtEmpfaenger]] = relationship(back_populates="nachricht")


class NachrichtEmpfaenger(Base):
    """Message recipient."""

    __tablename__ = "nachricht_empfaenger"

    id: Mapped[int] = mapped_column(primary_key=True)
    nachricht_id: Mapped[int] = mapped_column(ForeignKey("nachrichten.id"))
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    status: Mapped[EmpfaengerStatus] = mapped_column(
        Enum(EmpfaengerStatus), default=EmpfaengerStatus.ausstehend
    )

    nachricht: Mapped[Nachricht] = relationship(back_populates="empfaenger")
