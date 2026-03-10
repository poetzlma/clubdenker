"""Ensure the database path is always absolute, regardless of cwd."""

import os
from pathlib import Path


def test_database_url_is_absolute():
    from sportverein.config import settings

    # Extract file path from sqlite URL (strip driver prefix)
    url = settings.database_url
    assert url.startswith("sqlite+aiosqlite:///"), f"Unexpected DB URL scheme: {url}"
    db_path = url.removeprefix("sqlite+aiosqlite:///")
    assert os.path.isabs(db_path), f"DB path must be absolute, got: {db_path}"


def test_database_url_points_to_backend_dir():
    from sportverein.config import settings

    db_path = Path(settings.database_url.removeprefix("sqlite+aiosqlite:///"))
    # The DB file should live in the backend/ directory (next to alembic.ini)
    backend_dir = Path(__file__).resolve().parent.parent
    assert db_path.parent == backend_dir, (
        f"DB should be in {backend_dir}, but points to {db_path.parent}"
    )
