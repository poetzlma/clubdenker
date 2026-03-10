from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from sportverein.models.base import Base


class AufwandTyp(str, enum.Enum):
    uebungsleiter = "uebungsleiter"
    ehrenamt = "ehrenamt"


class Aufwandsentschaedigung(Base):
    __tablename__ = "aufwandsentschaedigungen"

    id: Mapped[int] = mapped_column(primary_key=True)
    mitglied_id: Mapped[int] = mapped_column(ForeignKey("mitglieder.id"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    datum: Mapped[date] = mapped_column(Date)
    typ: Mapped[AufwandTyp] = mapped_column(Enum(AufwandTyp))
    beschreibung: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
