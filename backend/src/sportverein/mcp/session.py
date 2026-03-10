"""DB session management for MCP tools.

MCP tools cannot use FastAPI's dependency injection, so we provide a
context-manager that creates a session from the global async_session_factory.

For testing, the factory can be overridden via ``set_session_factory``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_session_factory_override: async_sessionmaker[AsyncSession] | None = None


def set_session_factory(factory: async_sessionmaker[AsyncSession] | None) -> None:
    """Override the session factory (used in tests)."""
    global _session_factory_override
    _session_factory_override = factory


def _get_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory_override is not None:
        return _session_factory_override
    # Import lazily to avoid circular imports and to pick up runtime config.
    from sportverein.db.session import async_session_factory
    return async_session_factory


@asynccontextmanager
async def get_mcp_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session for MCP tool use."""
    factory = _get_factory()
    async with factory() as session:
        yield session
