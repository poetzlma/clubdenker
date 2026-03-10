"""MCP tools for audit log queries."""

from __future__ import annotations

from typing import Any

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.audit import AuditService


def _audit_to_dict(a: Any) -> dict:
    """Convert an AuditLog ORM object to a plain dict."""
    return {
        "id": a.id,
        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        "user_id": a.user_id,
        "action": a.action,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "details": a.details,
        "ip_address": a.ip_address,
    }


@mcp.tool(description="Audit-Protokoll abfragen (wer hat was wann geändert).")
async def audit_logs_abrufen(
    aktion: str | None = None,
    bereich: str | None = None,
    limit: int = 50,
) -> dict:
    """Query audit trail with optional filters."""
    async with get_mcp_session() as session:
        svc = AuditService(session)
        filters: dict[str, Any] = {}
        if aktion:
            filters["action"] = aktion
        if bereich:
            filters["entity_type"] = bereich
        logs, total = await svc.get_logs(
            filters=filters or None, page=1, page_size=limit
        )
        await session.commit()
        return {
            "items": [_audit_to_dict(log) for log in logs],
            "total": total,
        }
