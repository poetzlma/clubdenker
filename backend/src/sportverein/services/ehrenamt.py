"""Volunteer compensation (Aufwandsentschaedigung) service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.models.mitglied import Mitglied


# Legal limits per year
_LIMITS: dict[AufwandTyp, Decimal] = {
    AufwandTyp.uebungsleiter: Decimal("3000.00"),  # section 3 Nr. 26 EStG
    AufwandTyp.ehrenamt: Decimal("840.00"),         # section 3 Nr. 26a EStG
}


class EhrenamtService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_compensation(self, data: dict[str, Any]) -> Aufwandsentschaedigung:
        """Create a new compensation entry."""
        typ_value = data.get("typ")
        if isinstance(typ_value, str):
            typ_value = AufwandTyp(typ_value)

        entry = Aufwandsentschaedigung(
            mitglied_id=data["mitglied_id"],
            betrag=data["betrag"] if isinstance(data["betrag"], Decimal) else Decimal(str(data["betrag"])),
            datum=data["datum"] if isinstance(data["datum"], date) else date.fromisoformat(data["datum"]),
            typ=typ_value,
            beschreibung=data["beschreibung"],
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_annual_total(
        self, member_id: int, year: int, typ: AufwandTyp | str
    ) -> Decimal:
        """Sum of compensation for a member/year/type."""
        if isinstance(typ, str):
            typ = AufwandTyp(typ)

        result = await self.session.execute(
            select(func.sum(Aufwandsentschaedigung.betrag)).where(
                Aufwandsentschaedigung.mitglied_id == member_id,
                extract("year", Aufwandsentschaedigung.datum) == year,
                Aufwandsentschaedigung.typ == typ,
            )
        )
        return result.scalar_one() or Decimal("0.00")

    async def check_limits(self, member_id: int, year: int) -> dict:
        """Check limits for both types for a member/year."""
        result = {}
        for typ, limit in _LIMITS.items():
            total = await self.get_annual_total(member_id, year, typ)
            remaining = max(limit - total, Decimal("0.00"))
            percent = float(total / limit * 100) if limit > 0 else 0.0
            result[typ.value] = {
                "total": total,
                "limit": limit,
                "remaining": remaining,
                "percent": round(percent, 1),
            }
        return result

    async def list_compensations(
        self, year: int, typ: AufwandTyp | str | None = None
    ) -> list[dict]:
        """List all compensation entries for a given year with member names."""
        stmt = (
            select(Aufwandsentschaedigung, Mitglied.vorname, Mitglied.nachname)
            .join(Mitglied, Mitglied.id == Aufwandsentschaedigung.mitglied_id)
            .where(extract("year", Aufwandsentschaedigung.datum) == year)
            .order_by(Aufwandsentschaedigung.datum.desc())
        )
        if typ is not None:
            if isinstance(typ, str):
                typ = AufwandTyp(typ)
            stmt = stmt.where(Aufwandsentschaedigung.typ == typ)

        result = await self.session.execute(stmt)
        entries = []
        for row in result.all():
            entry = row[0]
            vorname = row[1]
            nachname = row[2]
            entries.append({
                "id": entry.id,
                "mitglied_id": entry.mitglied_id,
                "mitglied_name": f"{vorname} {nachname}",
                "betrag": float(entry.betrag),
                "datum": entry.datum.isoformat(),
                "typ": entry.typ.value if hasattr(entry.typ, "value") else str(entry.typ),
                "beschreibung": entry.beschreibung,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            })
        return entries

    async def get_freibetrag_summary(self, year: int) -> list[dict]:
        """Get per-member freibetrag usage summary for a given year."""
        stmt = (
            select(
                Aufwandsentschaedigung.mitglied_id,
                Aufwandsentschaedigung.typ,
                func.sum(Aufwandsentschaedigung.betrag).label("total"),
                Mitglied.vorname,
                Mitglied.nachname,
            )
            .join(Mitglied, Mitglied.id == Aufwandsentschaedigung.mitglied_id)
            .where(extract("year", Aufwandsentschaedigung.datum) == year)
            .group_by(
                Aufwandsentschaedigung.mitglied_id,
                Aufwandsentschaedigung.typ,
                Mitglied.vorname,
                Mitglied.nachname,
            )
        )
        result = await self.session.execute(stmt)
        summaries = []
        for row in result.all():
            member_id = row[0]
            typ = row[1]
            total = row[2]
            vorname = row[3]
            nachname = row[4]
            typ_value = typ.value if hasattr(typ, "value") else str(typ)
            limit = _LIMITS.get(AufwandTyp(typ_value), Decimal("0"))
            percent = float(total / limit * 100) if limit > 0 else 0.0
            summaries.append({
                "mitglied_id": member_id,
                "mitglied_name": f"{vorname} {nachname}",
                "typ": typ_value,
                "total": float(total),
                "limit": float(limit),
                "remaining": float(max(limit - total, Decimal("0"))),
                "percent": round(percent, 1),
                "warning": percent > 80.0,
            })
        return summaries

    async def get_warnings(self, year: int) -> list[dict]:
        """Members at >80% of any limit."""
        warnings: list[dict] = []

        for typ, limit in _LIMITS.items():
            threshold = limit * Decimal("0.80")
            # Find members with total > threshold
            stmt = (
                select(
                    Aufwandsentschaedigung.mitglied_id,
                    func.sum(Aufwandsentschaedigung.betrag).label("total"),
                )
                .where(
                    extract("year", Aufwandsentschaedigung.datum) == year,
                    Aufwandsentschaedigung.typ == typ,
                )
                .group_by(Aufwandsentschaedigung.mitglied_id)
                .having(func.sum(Aufwandsentschaedigung.betrag) > threshold)
            )
            result = await self.session.execute(stmt)
            for row in result.all():
                member_id = row[0]
                total = row[1]
                # Get member name
                m_result = await self.session.execute(
                    select(Mitglied.vorname, Mitglied.nachname).where(
                        Mitglied.id == member_id
                    )
                )
                m_row = m_result.one_or_none()
                name = f"{m_row[0]} {m_row[1]}" if m_row else f"ID {member_id}"
                warnings.append({
                    "member_id": member_id,
                    "name": name,
                    "typ": typ.value,
                    "total": total,
                    "limit": limit,
                    "percent": round(float(total / limit * 100), 1),
                })

        return warnings
