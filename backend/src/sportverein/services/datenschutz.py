"""DSGVO compliance service."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.audit import AuditLog
from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import Rechnung, Zahlung
from sportverein.models.mitglied import Mitglied, MitgliedAbteilung, MitgliedStatus


class DatenschutzService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_auskunft(self, member_id: int) -> dict:
        """DSGVO Art. 15 data export.

        Collects ALL data about a member: personal data, departments,
        invoices, payments, SEPA mandates, audit log entries.
        """
        # Personal data
        result = await self.session.execute(
            select(Mitglied)
            .where(Mitglied.id == member_id)
            .options(selectinload(Mitglied.abteilungen).selectinload(MitgliedAbteilung.abteilung))
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError(f"Member {member_id} not found")

        personal_data = {
            "id": member.id,
            "mitgliedsnummer": member.mitgliedsnummer,
            "vorname": member.vorname,
            "nachname": member.nachname,
            "email": member.email,
            "telefon": member.telefon,
            "geburtsdatum": member.geburtsdatum.isoformat() if member.geburtsdatum else None,
            "strasse": member.strasse,
            "plz": member.plz,
            "ort": member.ort,
            "eintrittsdatum": member.eintrittsdatum.isoformat() if member.eintrittsdatum else None,
            "austrittsdatum": member.austrittsdatum.isoformat() if member.austrittsdatum else None,
            "status": member.status.value if member.status else None,
            "beitragskategorie": member.beitragskategorie.value
            if member.beitragskategorie
            else None,
            "dsgvo_einwilligung": member.dsgvo_einwilligung,
            "einwilligung_datum": member.einwilligung_datum.isoformat()
            if member.einwilligung_datum
            else None,
            "loesch_datum": member.loesch_datum.isoformat() if member.loesch_datum else None,
        }

        # Departments
        departments = [
            {
                "abteilung": ma.abteilung.name if ma.abteilung else str(ma.abteilung_id),
                "beitrittsdatum": ma.beitrittsdatum.isoformat() if ma.beitrittsdatum else None,
            }
            for ma in member.abteilungen
        ]

        # Invoices
        inv_result = await self.session.execute(
            select(Rechnung).where(Rechnung.mitglied_id == member_id)
        )
        invoices_data = []
        for inv in inv_result.scalars().all():
            invoices_data.append(
                {
                    "id": inv.id,
                    "rechnungsnummer": inv.rechnungsnummer,
                    "betrag": str(inv.betrag),
                    "status": inv.status.value if inv.status else None,
                    "rechnungsdatum": inv.rechnungsdatum.isoformat()
                    if inv.rechnungsdatum
                    else None,
                }
            )

        # Payments
        inv_ids = [i["id"] for i in invoices_data]
        payments_data = []
        if inv_ids:
            pay_result = await self.session.execute(
                select(Zahlung).where(Zahlung.rechnung_id.in_(inv_ids))
            )
            for pay in pay_result.scalars().all():
                payments_data.append(
                    {
                        "id": pay.id,
                        "rechnung_id": pay.rechnung_id,
                        "betrag": str(pay.betrag),
                        "zahlungsdatum": pay.zahlungsdatum.isoformat()
                        if pay.zahlungsdatum
                        else None,
                        "zahlungsart": pay.zahlungsart.value if pay.zahlungsart else None,
                    }
                )

        # SEPA mandates
        sepa_result = await self.session.execute(
            select(SepaMandat).where(SepaMandat.mitglied_id == member_id)
        )
        sepa_data = []
        for m in sepa_result.scalars().all():
            sepa_data.append(
                {
                    "id": m.id,
                    "mandatsreferenz": m.mandatsreferenz,
                    "iban": m.iban,
                    "bic": m.bic,
                    "kontoinhaber": m.kontoinhaber,
                    "aktiv": m.aktiv,
                }
            )

        # Audit log entries
        audit_result = await self.session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "mitglied",
                AuditLog.entity_id == member_id,
            )
        )
        audit_data = []
        for a in audit_result.scalars().all():
            audit_data.append(
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "action": a.action,
                    "details": a.details,
                }
            )

        return {
            "personal_data": personal_data,
            "departments": departments,
            "invoices": invoices_data,
            "payments": payments_data,
            "sepa_mandates": sepa_data,
            "audit_log": audit_data,
        }

    async def set_consent(self, member_id: int, consent: bool) -> Mitglied:
        """Update DSGVO consent flag."""
        result = await self.session.execute(select(Mitglied).where(Mitglied.id == member_id))
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError(f"Member {member_id} not found")

        member.dsgvo_einwilligung = consent
        member.einwilligung_datum = date.today() if consent else None
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def schedule_deletion(self, member_id: int, retention_days: int = 365 * 10) -> Mitglied:
        """Set loesch_datum for a member."""
        result = await self.session.execute(select(Mitglied).where(Mitglied.id == member_id))
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError(f"Member {member_id} not found")

        member.loesch_datum = date.today() + timedelta(days=retention_days)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_pending_deletions(self) -> list[Mitglied]:
        """Members past their loesch_datum that have not yet been anonymized."""
        result = await self.session.execute(
            select(Mitglied).where(
                Mitglied.loesch_datum != None,  # noqa: E711
                Mitglied.loesch_datum <= date.today(),
                Mitglied.geloescht_am == None,  # noqa: E711
            )
        )
        return list(result.scalars().all())

    async def delete_member_data(self, member_id: int) -> Mitglied:
        """Anonymize personal data for DSGVO compliance.

        Keeps the record for financial audit trail (soft-delete).
        Replaces personal data with placeholder values and sets geloescht_am.
        """
        result = await self.session.execute(select(Mitglied).where(Mitglied.id == member_id))
        member = result.scalar_one_or_none()
        if member is None:
            raise ValueError(f"Mitglied mit ID {member_id} nicht gefunden.")

        if member.geloescht_am is not None:
            raise ValueError(
                f"Mitglied mit ID {member_id} wurde bereits am "
                f"{member.geloescht_am.isoformat()} anonymisiert."
            )

        # Anonymize personal data
        member.vorname = "Geloescht"
        member.nachname = "Geloescht"
        member.email = f"geloescht-{member.id}@deleted.local"
        member.telefon = None
        member.strasse = None
        member.plz = None
        member.ort = None
        member.geburtsdatum = date(1900, 1, 1)
        member.notizen = None
        member.dsgvo_einwilligung = False
        member.einwilligung_datum = None
        member.status = MitgliedStatus.gekuendigt
        member.geloescht_am = datetime.now()

        # Log the deletion in audit trail
        from sportverein.services.audit import AuditService

        audit_svc = AuditService(self.session)
        await audit_svc.log(
            action="dsgvo_loeschung",
            entity_type="mitglied",
            entity_id=member_id,
            details=json.dumps(
                {"grund": "DSGVO-Datenlöschung durchgeführt"},
                default=str,
            ),
        )

        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def enforce_pending_deletions(self) -> list[dict]:
        """Find all members with loesch_datum <= today and anonymize them.

        Returns a list of dicts with member_id and status for each processed member.
        """
        pending = await self.get_pending_deletions()
        results: list[dict] = []
        for member in pending:
            try:
                await self.delete_member_data(member.id)
                results.append(
                    {
                        "mitglied_id": member.id,
                        "status": "geloescht",
                    }
                )
            except ValueError as exc:
                results.append(
                    {
                        "mitglied_id": member.id,
                        "status": "fehler",
                        "detail": str(exc),
                    }
                )
        return results
