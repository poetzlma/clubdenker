from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    RechnungStatus,
    Sphare,
    Zahlung,
    Zahlungsart,
)
from sportverein.models.mitglied import Mitglied, MitgliedStatus
from sportverein.services.finanzen import FinanzenService


def _make_member(
    *,
    vorname: str = "Max",
    nachname: str = "Mustermann",
    email: str = "max@example.com",
    mitgliedsnummer: str = "M-0001",
    geburtsdatum: date = date(1990, 1, 1),
    eintrittsdatum: date = date(2020, 1, 1),
) -> Mitglied:
    return Mitglied(
        vorname=vorname,
        nachname=nachname,
        email=email,
        mitgliedsnummer=mitgliedsnummer,
        geburtsdatum=geburtsdatum,
        eintrittsdatum=eintrittsdatum,
        status=MitgliedStatus.aktiv,
    )


class TestCreateBooking:
    async def test_create_booking_valid_sphere(self, session):
        svc = FinanzenService(session)
        member = _make_member()
        session.add(member)
        await session.flush()

        buchung = await svc.create_booking(
            {
                "buchungsdatum": date(2024, 6, 15),
                "betrag": Decimal("100.00"),
                "beschreibung": "Mitgliedsbeitrag",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
                "mitglied_id": member.id,
            }
        )

        assert buchung.id is not None
        assert buchung.sphare == Sphare.ideell
        assert buchung.betrag == Decimal("100.00")

    async def test_create_booking_with_enum_sphere(self, session):
        svc = FinanzenService(session)
        buchung = await svc.create_booking(
            {
                "buchungsdatum": date(2024, 6, 15),
                "betrag": Decimal("50.00"),
                "beschreibung": "Kursgebühr",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": Sphare.zweckbetrieb,
            }
        )
        assert buchung.sphare == Sphare.zweckbetrieb

    async def test_create_booking_invalid_sphere(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="Invalid sphere"):
            await svc.create_booking(
                {
                    "buchungsdatum": date(2024, 6, 15),
                    "betrag": Decimal("100.00"),
                    "beschreibung": "Test",
                    "konto": "4000",
                    "gegenkonto": "1200",
                    "sphare": "invalid_sphere",
                }
            )

    async def test_create_booking_missing_sphere(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="required"):
            await svc.create_booking(
                {
                    "buchungsdatum": date(2024, 6, 15),
                    "betrag": Decimal("100.00"),
                    "beschreibung": "Test",
                    "konto": "4000",
                    "gegenkonto": "1200",
                }
            )


class TestGetBookings:
    async def test_get_bookings_with_filters(self, session):
        svc = FinanzenService(session)

        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 3, 1),
                "betrag": Decimal("100.00"),
                "beschreibung": "Beitrag",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 6, 1),
                "betrag": Decimal("200.00"),
                "beschreibung": "Kurs",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": "zweckbetrieb",
            }
        )

        # Filter by sphere
        bookings, total = await svc.get_bookings({"sphare": "ideell"})
        assert total == 1
        assert bookings[0].beschreibung == "Beitrag"

        # Filter by date range
        bookings, total = await svc.get_bookings(
            {
                "date_from": date(2024, 5, 1),
                "date_to": date(2024, 7, 1),
            }
        )
        assert total == 1
        assert bookings[0].beschreibung == "Kurs"

    async def test_get_bookings_pagination(self, session):
        svc = FinanzenService(session)
        for i in range(5):
            await svc.create_booking(
                {
                    "buchungsdatum": date(2024, 1, i + 1),
                    "betrag": Decimal("10.00"),
                    "beschreibung": f"Entry {i}",
                    "konto": "4000",
                    "gegenkonto": "1200",
                    "sphare": "ideell",
                }
            )

        bookings, total = await svc.get_bookings(page=1, page_size=2)
        assert total == 5
        assert len(bookings) == 2


class TestBalanceBySphere:
    async def test_balance_grouped(self, session):
        svc = FinanzenService(session)
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 1),
                "betrag": Decimal("100.00"),
                "beschreibung": "A",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 2),
                "betrag": Decimal("50.00"),
                "beschreibung": "B",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 3),
                "betrag": Decimal("200.00"),
                "beschreibung": "C",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": "zweckbetrieb",
            }
        )

        balance = await svc.get_balance_by_sphere()
        assert balance["ideell"] == Decimal("150.00")
        assert balance["zweckbetrieb"] == Decimal("200.00")

    async def test_total_balance(self, session):
        svc = FinanzenService(session)
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 1),
                "betrag": Decimal("100.00"),
                "beschreibung": "A",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 1),
                "betrag": Decimal("200.00"),
                "beschreibung": "B",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": "zweckbetrieb",
            }
        )

        total = await svc.get_total_balance()
        assert total == Decimal("300.00")


class TestInvoices:
    async def test_create_invoice_auto_number(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        r1 = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("240.00"),
            beschreibung="Beitrag 2024",
            faelligkeitsdatum=date(2024, 1, 31),
        )
        assert r1.rechnungsnummer.endswith("-0001")

        r2 = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("120.00"),
            beschreibung="Beitrag 2024 H2",
            faelligkeitsdatum=date(2024, 7, 31),
        )
        assert r2.rechnungsnummer.endswith("-0002")

    async def test_get_invoices_with_filters(self, session):
        m1 = _make_member()
        m2 = _make_member(
            vorname="Anna",
            email="anna@example.com",
            mitgliedsnummer="M-0002",
        )
        session.add_all([m1, m2])
        await session.flush()

        svc = FinanzenService(session)
        await svc.create_invoice(m1.id, Decimal("100.00"), "A", date(2024, 1, 31))
        await svc.create_invoice(m2.id, Decimal("200.00"), "B", date(2024, 1, 31))

        invoices, total = await svc.get_invoices({"mitglied_id": m1.id})
        assert total == 1
        assert invoices[0].beschreibung == "A"


class TestPaymentAndStatus:
    async def test_record_payment_updates_status(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Test",
            faelligkeitsdatum=date(2024, 1, 31),
        )

        assert rechnung.status == RechnungStatus.entwurf

        # Partial payment
        await svc.record_payment(rechnung.id, Decimal("60.00"), "ueberweisung")
        await session.refresh(rechnung)
        assert rechnung.status == RechnungStatus.teilbezahlt

        # Full payment
        await svc.record_payment(rechnung.id, Decimal("40.00"), "ueberweisung")
        await session.refresh(rechnung)
        assert rechnung.status == RechnungStatus.bezahlt

    async def test_record_payment_with_reference(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(member.id, Decimal("50.00"), "Test", date(2024, 1, 31))
        zahlung = await svc.record_payment(
            rechnung.id, Decimal("50.00"), Zahlungsart.lastschrift, referenz="REF-001"
        )
        assert zahlung.referenz == "REF-001"
        assert zahlung.zahlungsart == Zahlungsart.lastschrift

    async def test_record_payment_nonexistent_invoice(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.record_payment(99999, Decimal("50.00"), "ueberweisung")


class TestOverdueInvoices:
    async def test_overdue_invoices(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        # Overdue invoice (past)
        await svc.create_invoice(
            member.id,
            Decimal("100.00"),
            "Overdue",
            faelligkeitsdatum=date(2020, 1, 1),
            rechnungsdatum=date(2019, 12, 1),
        )
        # Future invoice (not overdue)
        await svc.create_invoice(
            member.id,
            Decimal("200.00"),
            "Future",
            faelligkeitsdatum=date(2099, 12, 31),
        )

        overdue = await svc.get_overdue_invoices()
        assert len(overdue) == 1
        assert overdue[0].beschreibung == "Overdue"


class TestSepaXml:
    async def test_generate_sepa_xml(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        # Create SEPA mandate
        mandat = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MREF-001",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=True,
        )
        session.add(mandat)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("240.00"), "Beitrag 2024", date(2024, 1, 31)
        )

        xml_str = await svc.generate_sepa_xml([rechnung.id])

        # Verify it's well-formed XML
        root = ET.fromstring(xml_str)

        # Verify structure
        assert (
            root.tag == "{urn:iso:std:iso:20022:tech:xsd:pain.008.001.02}Document"
            or root.tag == "Document"
        )

        # Find elements (with or without namespace)
        ns = {"ns": "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"}

        # Check NbOfTxs
        nb_txs = root.find(".//NbOfTxs")
        if nb_txs is None:
            nb_txs = root.find(".//ns:NbOfTxs", ns)
        assert nb_txs is not None
        assert nb_txs.text == "1"

        # Check IBAN is present
        xml_text = xml_str
        assert "DE89370400440532013000" in xml_text
        assert "MREF-001" in xml_text
        assert "Max Mustermann" in xml_text

    async def test_generate_sepa_xml_no_invoices(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="No invoices found"):
            await svc.generate_sepa_xml([9999])


class TestDonationReceipt:
    async def test_create_donation_receipt(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        receipt = await svc.create_donation_receipt(
            mitglied_id=member.id,
            betrag=Decimal("500.00"),
            zweck="Sportförderung",
        )

        assert receipt.id is not None
        assert receipt.mitglied_id == member.id
        assert receipt.betrag == Decimal("500.00")
        assert receipt.zweck == "Sportförderung"
        assert receipt.ausstellungsdatum == date.today()


class TestSkonto:
    """Tests for skonto (early payment discount) calculation and application."""

    async def test_calculate_skonto_within_deadline(self, session):
        """Skonto is available when reference_date is within the skonto deadline."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("1000.00"),
            beschreibung="Test Skonto",
            rechnungsdatum=date(2024, 1, 1),
            faelligkeitsdatum=date(2024, 2, 1),
            sphaere="ideell",
            skonto_prozent=Decimal("2.00"),
            skonto_frist_tage=10,
        )

        # Within deadline (day 5)
        info = await svc.calculate_skonto(rechnung.id, reference_date=date(2024, 1, 5))

        assert info["skonto_verfuegbar"] is True
        assert info["skonto_prozent"] == Decimal("2.00")
        # netto is 1000, skonto = 1000 * 2% = 20
        assert info["skonto_betrag"] == Decimal("20.00")
        assert info["zahlbetrag"] == Decimal("980.00")
        assert info["skonto_frist_bis"] == date(2024, 1, 11)

    async def test_calculate_skonto_on_deadline_day(self, session):
        """Skonto is still available on the exact deadline day."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("500.00"),
            beschreibung="Test Skonto deadline",
            rechnungsdatum=date(2024, 3, 1),
            faelligkeitsdatum=date(2024, 4, 1),
            sphaere="ideell",
            skonto_prozent=Decimal("3.00"),
            skonto_frist_tage=14,
        )

        # Exactly on deadline day
        info = await svc.calculate_skonto(rechnung.id, reference_date=date(2024, 3, 15))
        assert info["skonto_verfuegbar"] is True
        assert info["skonto_betrag"] == Decimal("15.00")

    async def test_calculate_skonto_after_deadline(self, session):
        """Skonto is not available after the deadline has passed."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("1000.00"),
            beschreibung="Test Skonto expired",
            rechnungsdatum=date(2024, 1, 1),
            faelligkeitsdatum=date(2024, 2, 1),
            sphaere="ideell",
            skonto_prozent=Decimal("2.00"),
            skonto_frist_tage=10,
        )

        # After deadline (day 12)
        info = await svc.calculate_skonto(rechnung.id, reference_date=date(2024, 1, 12))
        assert info["skonto_verfuegbar"] is False
        # Still returns the amounts for informational purposes
        assert info["skonto_betrag"] == Decimal("20.00")

    async def test_calculate_skonto_no_skonto_configured(self, session):
        """Invoice without skonto terms returns zero discount."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="No skonto",
            faelligkeitsdatum=date(2024, 1, 31),
        )

        info = await svc.calculate_skonto(rechnung.id)
        assert info["skonto_verfuegbar"] is False
        assert info["skonto_betrag"] == Decimal("0.00")
        assert info["zahlbetrag"] == Decimal("100.00")
        assert info["skonto_frist_bis"] is None

    async def test_calculate_skonto_not_found(self, session):
        """Raises ValueError for non-existent invoice."""
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.calculate_skonto(99999)

    async def test_record_payment_with_skonto(self, session):
        """Payment with apply_skonto creates skonto booking and marks as paid."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("1000.00"),
            beschreibung="Skonto payment test",
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today(),
            sphaere="ideell",
            skonto_prozent=Decimal("2.00"),
            skonto_frist_tage=10,
        )

        # Pay the discounted amount (980) with skonto applied
        zahlung = await svc.record_payment(
            rechnung.id,
            Decimal("980.00"),
            "ueberweisung",
            apply_skonto=True,
        )

        await session.refresh(rechnung)

        # The payment itself is 980
        assert zahlung.betrag == Decimal("980.00")

        # Total paid should be 1000 (980 payment + 20 skonto)
        assert rechnung.bezahlt_betrag == Decimal("1000.00")
        assert rechnung.offener_betrag == Decimal("0.00")
        assert rechnung.status == RechnungStatus.bezahlt

    async def test_record_payment_with_skonto_expired(self, session):
        """Payment with apply_skonto after deadline does not apply skonto."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        # Invoice from the past with expired skonto
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("1000.00"),
            beschreibung="Skonto expired test",
            rechnungsdatum=date(2020, 1, 1),
            faelligkeitsdatum=date(2020, 2, 1),
            sphaere="ideell",
            skonto_prozent=Decimal("2.00"),
            skonto_frist_tage=10,
        )

        # Pay full amount with skonto flag -- but skonto is expired
        zahlung = await svc.record_payment(
            rechnung.id,
            Decimal("1000.00"),
            "ueberweisung",
            apply_skonto=True,
        )

        await session.refresh(rechnung)

        # No skonto applied, just the direct payment
        assert zahlung.betrag == Decimal("1000.00")
        assert rechnung.bezahlt_betrag == Decimal("1000.00")
        assert rechnung.status == RechnungStatus.bezahlt

    async def test_record_payment_without_skonto_flag(self, session):
        """Payment without apply_skonto does not apply skonto even if eligible."""
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("1000.00"),
            beschreibung="No skonto flag",
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today(),
            sphaere="ideell",
            skonto_prozent=Decimal("2.00"),
            skonto_frist_tage=10,
        )

        # Pay 980 without skonto flag -- treated as partial payment
        zahlung = await svc.record_payment(
            rechnung.id,
            Decimal("980.00"),
            "ueberweisung",
        )

        await session.refresh(rechnung)

        assert zahlung.betrag == Decimal("980.00")
        assert rechnung.bezahlt_betrag == Decimal("980.00")
        assert rechnung.offener_betrag == Decimal("20.00")
        assert rechnung.status == RechnungStatus.teilbezahlt


class TestCostCenterCRUD:
    async def test_create_cost_center(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center(
            {
                "name": "Fussball",
                "beschreibung": "Fussball-Abteilung",
                "budget": Decimal("5000.00"),
                "freigabelimit": Decimal("500.00"),
            }
        )
        assert ks.id is not None
        assert ks.name == "Fussball"
        assert ks.beschreibung == "Fussball-Abteilung"
        assert ks.budget == Decimal("5000.00")
        assert ks.freigabelimit == Decimal("500.00")

    async def test_get_cost_centers_empty(self, session):
        svc = FinanzenService(session)
        result = await svc.get_cost_centers()
        assert result == []

    async def test_get_cost_centers_returns_sorted(self, session):
        svc = FinanzenService(session)
        await svc.create_cost_center({"name": "Turnen"})
        await svc.create_cost_center({"name": "Fussball"})
        await svc.create_cost_center({"name": "Handball"})

        centers = await svc.get_cost_centers()
        assert len(centers) == 3
        assert [c.name for c in centers] == ["Fussball", "Handball", "Turnen"]

    async def test_update_cost_center(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center(
            {"name": "Alt", "budget": Decimal("1000.00")}
        )

        updated = await svc.update_cost_center(
            ks.id, {"name": "Neu", "budget": Decimal("2000.00")}
        )
        assert updated.name == "Neu"
        assert updated.budget == Decimal("2000.00")

    async def test_update_cost_center_not_found(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.update_cost_center(99999, {"name": "X"})

    async def test_delete_cost_center(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center({"name": "Loeschbar"})

        await svc.delete_cost_center(ks.id)

        centers = await svc.get_cost_centers()
        assert len(centers) == 0

    async def test_delete_cost_center_not_found(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.delete_cost_center(99999)

    async def test_delete_cost_center_with_bookings_fails(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center({"name": "MitBuchungen"})

        buchung = await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 1),
                "betrag": Decimal("100.00"),
                "beschreibung": "Test",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        # Assign cost center directly since create_booking doesn't pass it
        buchung.kostenstelle_id = ks.id
        await session.flush()

        with pytest.raises(ValueError, match="zugeordnete Buchungen"):
            await svc.delete_cost_center(ks.id)


class TestBudgetStatus:
    async def test_budget_status_no_spending(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center(
            {"name": "Leer", "budget": Decimal("3000.00"), "freigabelimit": Decimal("200.00")}
        )

        status = await svc.get_budget_status(ks.id)
        assert status["name"] == "Leer"
        assert status["budget"] == Decimal("3000.00")
        assert status["spent"] == Decimal("0.00")
        assert status["remaining"] == Decimal("3000.00")
        assert status["freigabelimit"] == Decimal("200.00")

    async def test_budget_status_with_spending(self, session):
        svc = FinanzenService(session)
        ks = await svc.create_cost_center(
            {"name": "Aktiv", "budget": Decimal("1000.00")}
        )

        b1 = await svc.create_booking(
            {
                "buchungsdatum": date(2024, 3, 1),
                "betrag": Decimal("300.00"),
                "beschreibung": "Ausgabe 1",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        b1.kostenstelle_id = ks.id

        b2 = await svc.create_booking(
            {
                "buchungsdatum": date(2024, 4, 1),
                "betrag": Decimal("150.00"),
                "beschreibung": "Ausgabe 2",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        b2.kostenstelle_id = ks.id
        await session.flush()

        status = await svc.get_budget_status(ks.id)
        assert status["spent"] == Decimal("450.00")
        assert status["remaining"] == Decimal("550.00")

    async def test_budget_status_not_found(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="not found"):
            await svc.get_budget_status(99999)


class TestEuerReport:
    async def test_euer_report_empty_year(self, session):
        svc = FinanzenService(session)
        report = await svc.get_euer_report(2024)

        assert report["jahr"] == 2024
        assert report["gesamt"]["einnahmen"] == 0.0
        assert report["gesamt"]["ausgaben"] == 0.0
        assert report["gesamt"]["ergebnis"] == 0.0
        assert report["nach_sphare"] == []
        assert report["nach_monat"] == []

    async def test_euer_report_with_bookings_in_different_spheres(self, session):
        svc = FinanzenService(session)

        # Income in ideell sphere
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 3, 15),
                "betrag": Decimal("500.00"),
                "beschreibung": "Beitraege",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        # Expense in ideell sphere (negative)
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 3, 20),
                "betrag": Decimal("-200.00"),
                "beschreibung": "Hallenmiete",
                "konto": "6000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        # Income in zweckbetrieb sphere
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 6, 1),
                "betrag": Decimal("800.00"),
                "beschreibung": "Kursgebuehren",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": "zweckbetrieb",
            }
        )

        report = await svc.get_euer_report(2024)

        assert report["gesamt"]["einnahmen"] == 1300.0
        assert report["gesamt"]["ausgaben"] == 200.0
        assert report["gesamt"]["ergebnis"] == 1100.0

        # Check by sphere
        by_sphere = {s["sphare"]: s for s in report["nach_sphare"]}
        assert "ideell" in by_sphere
        assert by_sphere["ideell"]["einnahmen"] == 500.0
        assert by_sphere["ideell"]["ausgaben"] == 200.0
        assert by_sphere["ideell"]["ergebnis"] == 300.0
        assert "zweckbetrieb" in by_sphere
        assert by_sphere["zweckbetrieb"]["einnahmen"] == 800.0
        assert by_sphere["zweckbetrieb"]["ausgaben"] == 0.0

        # Check by month
        by_month = {m["monat"]: m for m in report["nach_monat"]}
        assert "2024-03" in by_month
        assert "2024-06" in by_month

    async def test_euer_report_filtered_by_sphere(self, session):
        svc = FinanzenService(session)

        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 1),
                "betrag": Decimal("100.00"),
                "beschreibung": "Ideell",
                "konto": "4000",
                "gegenkonto": "1200",
                "sphare": "ideell",
            }
        )
        await svc.create_booking(
            {
                "buchungsdatum": date(2024, 1, 2),
                "betrag": Decimal("200.00"),
                "beschreibung": "Zweck",
                "konto": "4100",
                "gegenkonto": "1200",
                "sphare": "zweckbetrieb",
            }
        )

        report = await svc.get_euer_report(2024, sphare="ideell")
        assert report["gesamt"]["einnahmen"] == 100.0
        # Only ideell should appear
        assert len(report["nach_sphare"]) == 1
        assert report["nach_sphare"][0]["sphare"] == "ideell"


class TestDeleteInvoice:
    async def test_delete_draft_invoice(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Draft", date(2024, 1, 31)
        )
        assert rechnung.status == RechnungStatus.entwurf

        await svc.delete_invoice(rechnung.id)

        # Verify it's gone
        invoices, total = await svc.get_invoices({})
        assert total == 0

    async def test_delete_gestellt_invoice_fails(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Gestellt", date(2024, 1, 31)
        )
        await svc.stelle_rechnung(rechnung.id)

        with pytest.raises(PermissionError, match="nicht gelöscht"):
            await svc.delete_invoice(rechnung.id)

    async def test_delete_nonexistent_invoice_fails(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.delete_invoice(99999)

    async def test_delete_storniert_within_retention_fails(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Storniert", date(2024, 1, 31)
        )
        await svc.stelle_rechnung(rechnung.id)
        await svc.storniere_rechnung(rechnung.id)

        # Reload to get the storniert original
        await session.refresh(rechnung)
        # Set a future loeschdatum to simulate retention period
        rechnung.loeschdatum = date(2099, 12, 31)
        await session.flush()

        with pytest.raises(PermissionError, match="Aufbewahrungspflicht"):
            await svc.delete_invoice(rechnung.id)

    async def test_delete_storniert_after_retention_succeeds(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Storniert alt", date(2024, 1, 31)
        )
        await svc.stelle_rechnung(rechnung.id)
        await svc.storniere_rechnung(rechnung.id)

        await session.refresh(rechnung)
        # Retention has expired
        rechnung.loeschdatum = date(2020, 1, 1)
        await session.flush()

        await svc.delete_invoice(rechnung.id)

        invoices, total = await svc.get_invoices({})
        # Only the storno-copy remains
        for inv in invoices:
            assert inv.id != rechnung.id


class TestVersendeRechnung:
    async def test_versende_gestellt_invoice(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Versand", date(2024, 1, 31)
        )
        await svc.stelle_rechnung(rechnung.id)

        result = await svc.versende_rechnung(rechnung.id, "email_pdf", "max@example.com")
        assert result.versand_kanal == "email_pdf"
        assert result.versendet_an == "max@example.com"
        assert result.versendet_am is not None
        assert result.gestellt_am is not None

    async def test_versende_draft_fails(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Draft", date(2024, 1, 31)
        )

        with pytest.raises(ValueError, match="Entwürfe können nicht versendet"):
            await svc.versende_rechnung(rechnung.id, "email_pdf", "max@example.com")

    async def test_versende_invalid_kanal(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            member.id, Decimal("100.00"), "Test", date(2024, 1, 31)
        )
        await svc.stelle_rechnung(rechnung.id)

        with pytest.raises(ValueError, match="Ungültiger Versandkanal"):
            await svc.versende_rechnung(rechnung.id, "brieftaube", "max@example.com")

    async def test_versende_nonexistent_invoice(self, session):
        svc = FinanzenService(session)
        with pytest.raises(ValueError, match="nicht gefunden"):
            await svc.versende_rechnung(99999, "email_pdf", "x@example.com")


class TestGetMandate:
    async def test_get_mandate_empty(self, session):
        svc = FinanzenService(session)
        items, total = await svc.get_mandate()
        assert items == []
        assert total == 0

    async def test_get_mandate_returns_all(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)

        mandat = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MREF-100",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=True,
        )
        session.add(mandat)
        await session.flush()

        items, total = await svc.get_mandate()
        assert total == 1
        assert items[0]["mandatsreferenz"] == "MREF-100"
        assert items[0]["mitglied_name"] == "Max Mustermann"
        assert items[0]["iban"] == "DE89370400440532013000"
        assert items[0]["aktiv"] is True

    async def test_get_mandate_filter_active(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)

        aktiv = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MREF-A",
            iban="DE89370400440532013000",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=True,
        )
        inaktiv = SepaMandat(
            mitglied_id=member.id,
            mandatsreferenz="MREF-I",
            iban="DE89370400440532013001",
            kontoinhaber="Max Mustermann",
            unterschriftsdatum=date(2023, 1, 1),
            gueltig_ab=date(2023, 1, 1),
            aktiv=False,
        )
        session.add_all([aktiv, inaktiv])
        await session.flush()

        active_items, active_total = await svc.get_mandate(aktiv_filter=True)
        assert active_total == 1
        assert active_items[0]["mandatsreferenz"] == "MREF-A"

        inactive_items, inactive_total = await svc.get_mandate(aktiv_filter=False)
        assert inactive_total == 1
        assert inactive_items[0]["mandatsreferenz"] == "MREF-I"


@pytest.mark.asyncio
async def test_delete_draft_invoice_with_payments(session):
    """Deleting a draft invoice that has payments should raise ValueError."""
    member = _make_member()
    session.add(member)
    await session.flush()

    svc = FinanzenService(session)
    rechnung = await svc.create_invoice(
        mitglied_id=member.id,
        betrag=Decimal("100.00"),
        beschreibung="Draft with payment",
        faelligkeitsdatum=date(2026, 12, 31),
        sphaere="ideell",
    )
    await session.flush()

    # Add a payment directly to the draft
    zahlung = Zahlung(
        rechnung_id=rechnung.id,
        betrag=Decimal("50.00"),
        zahlungsdatum=date(2026, 1, 15),
        zahlungsart=Zahlungsart.ueberweisung,
    )
    session.add(zahlung)
    await session.flush()

    with pytest.raises(ValueError, match="Zahlung"):
        await svc.delete_invoice(rechnung.id)


class TestOverpaymentValidation:
    async def test_record_payment_overpayment(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Overpayment test",
            faelligkeitsdatum=date(2024, 1, 31),
        )

        with pytest.raises(ValueError, match="übersteigt"):
            await svc.record_payment(rechnung.id, Decimal("150.00"), "ueberweisung")

    async def test_record_payment_negative_amount(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Negative payment test",
            faelligkeitsdatum=date(2024, 1, 31),
        )

        with pytest.raises(ValueError, match="positiv"):
            await svc.record_payment(rechnung.id, Decimal("-50.00"), "ueberweisung")

    async def test_record_payment_exact_amount(self, session):
        member = _make_member()
        session.add(member)
        await session.flush()

        svc = FinanzenService(session)
        rechnung = await svc.create_invoice(
            mitglied_id=member.id,
            betrag=Decimal("100.00"),
            beschreibung="Exact payment test",
            faelligkeitsdatum=date(2024, 1, 31),
        )

        zahlung = await svc.record_payment(rechnung.id, Decimal("100.00"), "ueberweisung")
        await session.refresh(rechnung)

        assert zahlung.betrag == Decimal("100.00")
        assert rechnung.status == RechnungStatus.bezahlt
