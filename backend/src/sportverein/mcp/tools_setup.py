"""MCP tools for Vereins-Setup: Abteilungen and BeitragsKategorien management."""

from __future__ import annotations

from decimal import Decimal

from sportverein.mcp.server import mcp
from sportverein.mcp.session import get_mcp_session
from sportverein.services.beitraege import BeitraegeService
from sportverein.services.mitglieder import MitgliederService


@mcp.tool(
    description="Abteilungen des Vereins verwalten: auflisten, erstellen, aktualisieren, löschen"
)
async def vereins_setup_abteilungen(
    action: str = "list",
    department_id: int | None = None,
    name: str | None = None,
    beschreibung: str | None = None,
) -> dict:
    """Manage departments.

    action: list | create | update | delete
    """
    async with get_mcp_session() as session:
        svc = MitgliederService(session)

        if action == "list":
            departments = await svc.get_departments()
            await session.commit()
            return {
                "items": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "beschreibung": d.beschreibung,
                        "created_at": d.created_at.isoformat() if d.created_at else None,
                    }
                    for d in departments
                ]
            }

        if action == "create":
            if name is None:
                return {"error": "Name ist erforderlich."}
            try:
                dept = await svc.create_department(name=name, beschreibung=beschreibung)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": dept.id,
                "name": dept.name,
                "beschreibung": dept.beschreibung,
                "message": "Abteilung erfolgreich erstellt.",
            }

        if action == "update":
            if department_id is None:
                return {"error": "department_id ist erforderlich."}
            try:
                dept = await svc.update_department(
                    department_id, name=name, beschreibung=beschreibung
                )
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": dept.id,
                "name": dept.name,
                "beschreibung": dept.beschreibung,
                "message": "Abteilung erfolgreich aktualisiert.",
            }

        if action == "delete":
            if department_id is None:
                return {"error": "department_id ist erforderlich."}
            try:
                await svc.delete_department(department_id)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {"message": f"Abteilung {department_id} erfolgreich gelöscht."}

        return {"error": f"Unbekannte Aktion: {action}"}


@mcp.tool(description="Beitragskategorien und Jahresbeiträge verwalten")
async def vereins_setup_beitragskategorien(
    action: str = "list",
    category_id: int | None = None,
    name: str | None = None,
    jahresbeitrag: float | None = None,
    beschreibung: str | None = None,
) -> dict:
    """Manage fee categories.

    action: list | create | update | delete
    """
    async with get_mcp_session() as session:
        svc = BeitraegeService(session)

        if action == "list":
            categories = await svc.get_categories()
            await session.commit()
            return {
                "items": [
                    {
                        "id": k.id,
                        "name": k.name,
                        "jahresbeitrag": float(k.jahresbeitrag),
                        "beschreibung": k.beschreibung,
                        "created_at": k.created_at.isoformat() if k.created_at else None,
                    }
                    for k in categories
                ]
            }

        if action == "create":
            if name is None or jahresbeitrag is None:
                return {"error": "Name und jahresbeitrag sind erforderlich."}
            try:
                category = await svc.create_category(
                    name=name,
                    jahresbeitrag=Decimal(str(jahresbeitrag)),
                    beschreibung=beschreibung,
                )
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": category.id,
                "name": category.name,
                "jahresbeitrag": float(category.jahresbeitrag),
                "message": "Beitragskategorie erfolgreich erstellt.",
            }

        if action == "update":
            if category_id is None:
                return {"error": "category_id ist erforderlich."}
            kwargs: dict = {}
            if jahresbeitrag is not None:
                kwargs["jahresbeitrag"] = Decimal(str(jahresbeitrag))
            if beschreibung is not None:
                kwargs["beschreibung"] = beschreibung
            try:
                category = await svc.update_category(category_id, **kwargs)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {
                "id": category.id,
                "name": category.name,
                "jahresbeitrag": float(category.jahresbeitrag),
                "message": "Beitragskategorie erfolgreich aktualisiert.",
            }

        if action == "delete":
            if category_id is None:
                return {"error": "category_id ist erforderlich."}
            try:
                await svc.delete_category(category_id)
            except ValueError as exc:
                return {"error": str(exc)}
            await session.commit()
            return {"message": f"Beitragskategorie {category_id} erfolgreich gelöscht."}

        return {"error": f"Unbekannte Aktion: {action}"}
