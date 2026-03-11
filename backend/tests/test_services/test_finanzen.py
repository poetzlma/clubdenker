from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal

import pytest

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    RechnungStatus,
    Sphare,
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
