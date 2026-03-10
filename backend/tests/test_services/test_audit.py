"""Tests for AuditService."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from sportverein.services.audit import AuditService


async def test_log_creates_entry(session: AsyncSession):
    svc = AuditService(session)
    entry = await svc.log(
        action="create",
        entity_type="mitglied",
        entity_id=1,
        details='{"vorname": "Max"}',
    )
    assert entry.id is not None
    assert entry.action == "create"
    assert entry.entity_type == "mitglied"
    assert entry.entity_id == 1
    assert entry.details == '{"vorname": "Max"}'


async def test_log_with_user_and_ip(session: AsyncSession):
    # We need an admin user for the FK
    from sportverein.auth.service import AuthService
    auth = AuthService(session)
    admin = await auth.create_admin(email="audit@test.de", password="pass", name="Audit Admin")
    await session.flush()

    svc = AuditService(session)
    entry = await svc.log(
        user_id=admin.id,
        action="login",
        entity_type="admin_user",
        entity_id=admin.id,
        ip_address="192.168.1.1",
    )
    assert entry.user_id == admin.id
    assert entry.ip_address == "192.168.1.1"


async def test_log_nullable_fields(session: AsyncSession):
    svc = AuditService(session)
    entry = await svc.log(
        action="export",
        entity_type="report",
    )
    assert entry.user_id is None
    assert entry.entity_id is None
    assert entry.details is None
    assert entry.ip_address is None


async def test_get_logs_all(session: AsyncSession):
    svc = AuditService(session)
    for i in range(5):
        await svc.log(action="create", entity_type="mitglied", entity_id=i)

    logs, total = await svc.get_logs()
    assert total == 5
    assert len(logs) == 5


async def test_get_logs_filter_by_entity_type(session: AsyncSession):
    svc = AuditService(session)
    await svc.log(action="create", entity_type="mitglied", entity_id=1)
    await svc.log(action="create", entity_type="buchung", entity_id=1)

    logs, total = await svc.get_logs(filters={"entity_type": "mitglied"})
    assert total == 1
    assert logs[0].entity_type == "mitglied"


async def test_get_logs_filter_by_action(session: AsyncSession):
    svc = AuditService(session)
    await svc.log(action="create", entity_type="mitglied")
    await svc.log(action="update", entity_type="mitglied")
    await svc.log(action="delete", entity_type="mitglied")

    logs, total = await svc.get_logs(filters={"action": "update"})
    assert total == 1
    assert logs[0].action == "update"


async def test_get_logs_pagination(session: AsyncSession):
    svc = AuditService(session)
    for i in range(10):
        await svc.log(action="create", entity_type="mitglied", entity_id=i)

    logs, total = await svc.get_logs(page=1, page_size=3)
    assert total == 10
    assert len(logs) == 3

    logs2, _ = await svc.get_logs(page=2, page_size=3)
    assert len(logs2) == 3


async def test_get_recent(session: AsyncSession):
    svc = AuditService(session)
    for i in range(25):
        await svc.log(action="create", entity_type="mitglied", entity_id=i)

    recent = await svc.get_recent(limit=10)
    assert len(recent) == 10


async def test_get_recent_default_limit(session: AsyncSession):
    svc = AuditService(session)
    for i in range(5):
        await svc.log(action="create", entity_type="mitglied", entity_id=i)

    recent = await svc.get_recent()
    assert len(recent) == 5  # less than default 20
