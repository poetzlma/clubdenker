"""Helper to log audit entries from API endpoints."""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.services.audit import AuditService


async def log_audit(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | str | None = None,
    ip_address: str | None = None,
) -> None:
    """Create an audit log entry (fire-and-forget, does not commit)."""
    detail_str: str | None = None
    if details is not None:
        if isinstance(details, dict):
            detail_str = json.dumps(details, default=str)
        else:
            detail_str = str(details)

    svc = AuditService(session)
    await svc.log(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=detail_str,
        ip_address=ip_address,
    )
