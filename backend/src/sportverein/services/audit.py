"""Audit logging service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.models.audit import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        *,
        user_id: int | None = None,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        details: str | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_logs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """Search audit logs with filters."""
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        conditions = []
        if filters:
            if filters.get("entity_type"):
                conditions.append(AuditLog.entity_type == filters["entity_type"])
            if filters.get("entity_id"):
                conditions.append(AuditLog.entity_id == filters["entity_id"])
            if filters.get("user_id"):
                conditions.append(AuditLog.user_id == filters["user_id"])
            if filters.get("action"):
                conditions.append(AuditLog.action == filters["action"])
            if filters.get("date_from"):
                df = filters["date_from"]
                if isinstance(df, date) and not isinstance(df, datetime):
                    df = datetime(df.year, df.month, df.day)
                conditions.append(AuditLog.timestamp >= df)
            if filters.get("date_to"):
                dt = filters["date_to"]
                if isinstance(dt, date) and not isinstance(dt, datetime):
                    dt = datetime(dt.year, dt.month, dt.day, 23, 59, 59)
                conditions.append(AuditLog.timestamp <= dt)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(AuditLog.timestamp.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        logs = list(result.scalars().all())
        return logs, total

    async def get_recent(self, limit: int = 20) -> list[AuditLog]:
        """Get the most recent audit log entries."""
        result = await self.session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        )
        return list(result.scalars().all())
