"""Service layer for Protokoll (meeting minutes) management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.protokoll import Protokoll, ProtokollTyp


class ProtokollService:
    """Business logic for meeting minutes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_protokolle(
        self,
        *,
        typ: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Protokoll], int]:
        """Return paginated list of protocols with optional filters."""
        stmt = select(Protokoll)
        count_stmt = select(func.count(Protokoll.id))

        if typ:
            stmt = stmt.where(Protokoll.typ == ProtokollTyp(typ))
            count_stmt = count_stmt.where(Protokoll.typ == ProtokollTyp(typ))

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(Protokoll.titel.ilike(pattern) | Protokoll.inhalt.ilike(pattern))
            count_stmt = count_stmt.where(
                Protokoll.titel.ilike(pattern) | Protokoll.inhalt.ilike(pattern)
            )

        total = (await self._session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Protokoll.datum.desc(), Protokoll.id.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_protokoll(self, protokoll_id: int) -> Protokoll:
        """Get a single protocol by ID."""
        result = await self._session.execute(select(Protokoll).where(Protokoll.id == protokoll_id))
        protokoll = result.scalar_one_or_none()
        if protokoll is None:
            raise ValueError(f"Protokoll {protokoll_id} nicht gefunden.")
        return protokoll

    async def create_protokoll(
        self,
        *,
        titel: str,
        datum: str,
        inhalt: str,
        typ: str = "sonstige",
        erstellt_von: str | None = None,
        teilnehmer: str | None = None,
        beschluesse: str | None = None,
    ) -> Protokoll:
        """Create a new protocol."""
        protokoll = Protokoll(
            titel=titel,
            datum=datum,
            inhalt=inhalt,
            typ=ProtokollTyp(typ),
            erstellt_von=erstellt_von,
            teilnehmer=teilnehmer,
            beschluesse=beschluesse,
        )
        self._session.add(protokoll)
        await self._session.flush()
        return protokoll

    async def update_protokoll(self, protokoll_id: int, **kwargs: object) -> Protokoll:
        """Update an existing protocol."""
        protokoll = await self.get_protokoll(protokoll_id)
        if "typ" in kwargs and kwargs["typ"] is not None:
            kwargs["typ"] = ProtokollTyp(str(kwargs["typ"]))
        for key, value in kwargs.items():
            if hasattr(protokoll, key):
                setattr(protokoll, key, value)
        await self._session.flush()
        return protokoll

    async def delete_protokoll(self, protokoll_id: int) -> None:
        """Delete a protocol."""
        protokoll = await self.get_protokoll(protokoll_id)
        await self._session.delete(protokoll)
        await self._session.flush()
