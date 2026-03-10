from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.beitrag import SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    EmpfaengerTyp,
    Kostenstelle,
    Rechnung,
    RechnungFormat,
    RechnungStatus,
    RechnungTyp,
    Rechnungsposition,
    Sphare,
    Spendenbescheinigung,
    VersandKanal,
    Zahlung,
    Zahlungsart,
)
from sportverein.models.mitglied import Mitglied
from sportverein.models.vereinsstammdaten import Vereinsstammdaten

# Sphare -> Nummernkreis code mapping
_SPHARE_CODE: dict[str, str] = {
    "ideell": "IB",
    "zweckbetrieb": "ZB",
    "vermoegensverwaltung": "VM",
    "wirtschaftlich": "WG",
}


class FinanzenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -- Vereinsstammdaten ---------------------------------------------------

    async def get_vereinsstammdaten(self) -> Vereinsstammdaten | None:
        """Fetch club master data (singleton row)."""
        result = await self.session.execute(
            select(Vereinsstammdaten).limit(1)
        )
        return result.scalar_one_or_none()

    async def update_vereinsstammdaten(
        self, data: dict[str, Any]
    ) -> Vereinsstammdaten:
        """Create or update club master data."""
        result = await self.session.execute(
            select(Vereinsstammdaten).limit(1)
        )
        stammdaten = result.scalar_one_or_none()
        if stammdaten is None:
            stammdaten = Vereinsstammdaten(**data)
            self.session.add(stammdaten)
        else:
            for key, value in data.items():
                if hasattr(stammdaten, key):
                    setattr(stammdaten, key, value)
        await self.session.flush()
        await self.session.refresh(stammdaten)
        return stammdaten

    # -- Bookings ------------------------------------------------------------

    async def create_booking(self, data: dict[str, Any]) -> Buchung:
        """Create a booking with sphere validation."""
        sphare_value = data.get("sphare")
        if isinstance(sphare_value, str):
            try:
                sphare_value = Sphare(sphare_value)
            except ValueError:
                raise ValueError(
                    f"Invalid sphere: {sphare_value}. "
                    f"Must be one of: {[s.value for s in Sphare]}"
                )
        elif isinstance(sphare_value, Sphare):
            pass
        else:
            raise ValueError("Sphere (sphare) is required")

        buchung = Buchung(
            buchungsdatum=data["buchungsdatum"],
            betrag=data["betrag"],
            beschreibung=data["beschreibung"],
            konto=data["konto"],
            gegenkonto=data["gegenkonto"],
            sphare=sphare_value,
            mitglied_id=data.get("mitglied_id"),
        )
        self.session.add(buchung)
        await self.session.flush()
        await self.session.refresh(buchung)
        return buchung

    async def get_bookings(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Buchung], int]:
        """List bookings with optional filters and pagination."""
        query = select(Buchung)
        count_query = select(func.count()).select_from(Buchung)

        conditions = []
        if filters:
            if filters.get("date_from"):
                conditions.append(Buchung.buchungsdatum >= filters["date_from"])
            if filters.get("date_to"):
                conditions.append(Buchung.buchungsdatum <= filters["date_to"])
            if filters.get("sphare"):
                sph = filters["sphare"]
                if isinstance(sph, str):
                    sph = Sphare(sph)
                conditions.append(Buchung.sphare == sph)
            if filters.get("mitglied_id"):
                conditions.append(Buchung.mitglied_id == filters["mitglied_id"])

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Buchung.buchungsdatum.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        bookings = list(result.scalars().all())
        return bookings, total

    async def get_balance_by_sphere(self) -> dict[str, Decimal]:
        """Sum of bookings grouped by sphere."""
        result = await self.session.execute(
            select(Buchung.sphare, func.sum(Buchung.betrag)).group_by(Buchung.sphare)
        )
        return {row[0].value if isinstance(row[0], Sphare) else row[0]: row[1] or Decimal("0.00") for row in result.all()}

    async def get_total_balance(self) -> Decimal:
        """Overall balance (sum of all bookings)."""
        result = await self.session.execute(select(func.sum(Buchung.betrag)))
        return result.scalar_one() or Decimal("0.00")

    # -- Invoices ------------------------------------------------------------

    async def _next_rechnungsnummer(self, sphaere: str | None = None) -> str:
        """Generate next invoice number: {YYYY}-{SPHARE_CODE}-{NR:04d}.

        The counter is per nummernkreis (year + sphare combo).
        """
        year = date.today().year
        code = _SPHARE_CODE.get(sphaere, "RE") if sphaere else "RE"
        prefix = f"{year}-{code}-"

        result = await self.session.execute(
            select(Rechnung.rechnungsnummer)
            .where(Rechnung.rechnungsnummer.like(f"{prefix}%"))
            .order_by(Rechnung.rechnungsnummer.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if last is not None:
            # Extract the numeric suffix after the last dash
            num_str = last.rsplit("-", 1)[-1]
            num = int(num_str)
            return f"{prefix}{num + 1:04d}"
        return f"{prefix}0001"

    async def create_invoice(
        self,
        mitglied_id: int | None = None,
        betrag: Decimal | None = None,
        beschreibung: str = "",
        faelligkeitsdatum: date | None = None,
        rechnungsdatum: date | None = None,
        *,
        rechnungstyp: RechnungTyp | str = RechnungTyp.sonstige,
        empfaenger_typ: EmpfaengerTyp | str = EmpfaengerTyp.mitglied,
        empfaenger_name: str | None = None,
        empfaenger_strasse: str | None = None,
        empfaenger_plz: str | None = None,
        empfaenger_ort: str | None = None,
        empfaenger_ust_id: str | None = None,
        leistungsdatum: date | None = None,
        leistungszeitraum_von: date | None = None,
        leistungszeitraum_bis: date | None = None,
        sphaere: str | None = None,
        steuerhinweis_text: str | None = None,
        zahlungsziel_tage: int = 14,
        positionen: list[dict[str, Any]] | None = None,
        format: RechnungFormat | str = RechnungFormat.pdf,
        skonto_prozent: Decimal | None = None,
        skonto_frist_tage: int | None = None,
    ) -> Rechnung:
        """Create an invoice with auto-generated number and totals."""
        if isinstance(rechnungstyp, str):
            rechnungstyp = RechnungTyp(rechnungstyp)
        if isinstance(empfaenger_typ, str):
            empfaenger_typ = EmpfaengerTyp(empfaenger_typ)
        if isinstance(format, str):
            format = RechnungFormat(format)

        rd = rechnungsdatum or date.today()
        fd = faelligkeitsdatum or (rd + timedelta(days=zahlungsziel_tage))

        # Auto-fill empfaenger from mitglied if not provided
        if mitglied_id and not empfaenger_name:
            member_result = await self.session.execute(
                select(Mitglied).where(Mitglied.id == mitglied_id)
            )
            member = member_result.scalar_one_or_none()
            if member:
                empfaenger_name = f"{member.vorname} {member.nachname}"
                empfaenger_strasse = empfaenger_strasse or member.strasse
                empfaenger_plz = empfaenger_plz or member.plz
                empfaenger_ort = empfaenger_ort or member.ort

        # Calculate totals from positionen if provided
        summe_netto = Decimal("0")
        summe_steuer = Decimal("0")
        summe_brutto = Decimal("0")
        pos_objects: list[Rechnungsposition] = []

        if positionen:
            for idx, pos_data in enumerate(positionen, 1):
                menge = Decimal(str(pos_data.get("menge", "1")))
                einzelpreis_netto = Decimal(str(pos_data["einzelpreis_netto"]))
                steuersatz = Decimal(str(pos_data.get("steuersatz", "0")))

                gp_netto = (menge * einzelpreis_netto).quantize(Decimal("0.01"))
                gp_steuer = (gp_netto * steuersatz / Decimal("100")).quantize(Decimal("0.01"))
                gp_brutto = gp_netto + gp_steuer

                pos_obj = Rechnungsposition(
                    position_nr=idx,
                    beschreibung=pos_data["beschreibung"],
                    menge=menge,
                    einheit=pos_data.get("einheit", "x"),
                    einzelpreis_netto=einzelpreis_netto,
                    steuersatz=steuersatz,
                    steuerbefreiungsgrund=pos_data.get("steuerbefreiungsgrund"),
                    gesamtpreis_netto=gp_netto,
                    gesamtpreis_steuer=gp_steuer,
                    gesamtpreis_brutto=gp_brutto,
                    kostenstelle_id=pos_data.get("kostenstelle_id"),
                )
                pos_objects.append(pos_obj)

                summe_netto += gp_netto
                summe_steuer += gp_steuer
                summe_brutto += gp_brutto

        # If no positionen but betrag provided, use betrag directly
        if not positionen and betrag is not None:
            summe_brutto = betrag
            summe_netto = betrag
            summe_steuer = Decimal("0")
        elif betrag is None:
            betrag = summe_brutto

        nummer = await self._next_rechnungsnummer(sphaere)

        # Auto-generate verwendungszweck
        verwendungszweck = f"{nummer} {beschreibung}"[:140]

        # Auto-set loeschdatum (rechnungsdatum + 10 years retention)
        loeschdatum = date(rd.year + 10, rd.month, rd.day)

        # Auto-calculate skonto_betrag if skonto_prozent is set
        skonto_betrag: Decimal | None = None
        if skonto_prozent is not None:
            skonto_betrag = (
                summe_brutto * (Decimal("1") - skonto_prozent / Decimal("100"))
            ).quantize(Decimal("0.01"))

        rechnung = Rechnung(
            rechnungsnummer=nummer,
            mitglied_id=mitglied_id,
            rechnungstyp=rechnungstyp,
            status=RechnungStatus.entwurf,
            empfaenger_typ=empfaenger_typ,
            empfaenger_name=empfaenger_name,
            empfaenger_strasse=empfaenger_strasse,
            empfaenger_plz=empfaenger_plz,
            empfaenger_ort=empfaenger_ort,
            empfaenger_ust_id=empfaenger_ust_id,
            betrag=summe_brutto,
            summe_netto=summe_netto,
            summe_steuer=summe_steuer,
            bezahlt_betrag=Decimal("0"),
            offener_betrag=summe_brutto,
            beschreibung=beschreibung,
            leistungsdatum=leistungsdatum,
            leistungszeitraum_von=leistungszeitraum_von,
            leistungszeitraum_bis=leistungszeitraum_bis,
            rechnungsdatum=rd,
            faelligkeitsdatum=fd,
            zahlungsziel_tage=zahlungsziel_tage,
            sphaere=sphaere,
            steuerhinweis_text=steuerhinweis_text,
            verwendungszweck=verwendungszweck,
            loeschdatum=loeschdatum,
            format=format,
            skonto_prozent=skonto_prozent,
            skonto_frist_tage=skonto_frist_tage,
            skonto_betrag=skonto_betrag,
        )
        self.session.add(rechnung)
        await self.session.flush()

        # Attach positionen
        for pos_obj in pos_objects:
            pos_obj.rechnung_id = rechnung.id
            self.session.add(pos_obj)
        if pos_objects:
            await self.session.flush()

        await self.session.refresh(rechnung)
        return rechnung

    async def stelle_rechnung(self, rechnung_id: int) -> Rechnung:
        """Move invoice from ENTWURF to GESTELLT (locks editing)."""
        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")
        if rechnung.status != RechnungStatus.entwurf:
            raise ValueError(
                f"Rechnung kann nur aus Status 'entwurf' gestellt werden, "
                f"aktueller Status: '{rechnung.status.value}'"
            )
        rechnung.status = RechnungStatus.gestellt
        rechnung.gestellt_am = datetime.now()
        await self.session.flush()
        await self.session.refresh(rechnung)
        return rechnung

    async def storniere_rechnung(
        self, rechnung_id: int, grund: str | None = None
    ) -> Rechnung:
        """Cancel an invoice by creating a Stornorechnung.

        Returns the new Stornorechnung. The original is marked storniert.
        """
        result = await self.session.execute(
            select(Rechnung)
            .where(Rechnung.id == rechnung_id)
            .options(selectinload(Rechnung.positionen))
        )
        original = result.scalar_one_or_none()
        if original is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")
        if original.status == RechnungStatus.storniert:
            raise ValueError("Rechnung ist bereits storniert")

        # Create storno invoice with negative amounts
        storno_beschreibung = f"Storno zu {original.rechnungsnummer}"
        if grund:
            storno_beschreibung += f" — {grund}"

        storno_positionen: list[dict[str, Any]] = []
        for pos in original.positionen:
            storno_positionen.append({
                "beschreibung": f"Storno: {pos.beschreibung}",
                "menge": pos.menge,
                "einheit": pos.einheit,
                "einzelpreis_netto": -pos.einzelpreis_netto,
                "steuersatz": pos.steuersatz,
                "steuerbefreiungsgrund": pos.steuerbefreiungsgrund,
                "kostenstelle_id": pos.kostenstelle_id,
            })

        # If original had no positionen, create single storno position
        if not storno_positionen:
            storno_positionen.append({
                "beschreibung": storno_beschreibung,
                "menge": Decimal("1"),
                "einheit": "x",
                "einzelpreis_netto": -original.summe_netto,
                "steuersatz": Decimal("0"),
            })

        storno_nummer = await self._next_rechnungsnummer(original.sphaere)

        storno = Rechnung(
            rechnungsnummer=storno_nummer,
            mitglied_id=original.mitglied_id,
            rechnungstyp=RechnungTyp.storno,
            status=RechnungStatus.gestellt,
            empfaenger_typ=original.empfaenger_typ,
            empfaenger_name=original.empfaenger_name,
            empfaenger_strasse=original.empfaenger_strasse,
            empfaenger_plz=original.empfaenger_plz,
            empfaenger_ort=original.empfaenger_ort,
            empfaenger_ust_id=original.empfaenger_ust_id,
            betrag=-original.betrag,
            summe_netto=-original.summe_netto,
            summe_steuer=-original.summe_steuer,
            bezahlt_betrag=Decimal("0"),
            offener_betrag=-original.betrag,
            beschreibung=storno_beschreibung,
            leistungsdatum=original.leistungsdatum,
            leistungszeitraum_von=original.leistungszeitraum_von,
            leistungszeitraum_bis=original.leistungszeitraum_bis,
            rechnungsdatum=date.today(),
            faelligkeitsdatum=date.today(),
            zahlungsziel_tage=0,
            sphaere=original.sphaere,
            steuerhinweis_text=original.steuerhinweis_text,
            verwendungszweck=f"Storno {original.rechnungsnummer}",
            storno_von_id=original.id,
            loeschdatum=original.loeschdatum,
            gestellt_am=datetime.now(),
            format=original.format,
        )
        self.session.add(storno)
        await self.session.flush()

        # Add storno positionen
        for idx, pos_data in enumerate(storno_positionen, 1):
            menge = Decimal(str(pos_data.get("menge", "1")))
            einzelpreis_netto = Decimal(str(pos_data["einzelpreis_netto"]))
            steuersatz = Decimal(str(pos_data.get("steuersatz", "0")))
            gp_netto = (menge * einzelpreis_netto).quantize(Decimal("0.01"))
            gp_steuer = (gp_netto * steuersatz / Decimal("100")).quantize(Decimal("0.01"))
            gp_brutto = gp_netto + gp_steuer

            self.session.add(Rechnungsposition(
                rechnung_id=storno.id,
                position_nr=idx,
                beschreibung=pos_data["beschreibung"],
                menge=menge,
                einheit=pos_data.get("einheit", "x"),
                einzelpreis_netto=einzelpreis_netto,
                steuersatz=steuersatz,
                steuerbefreiungsgrund=pos_data.get("steuerbefreiungsgrund"),
                gesamtpreis_netto=gp_netto,
                gesamtpreis_steuer=gp_steuer,
                gesamtpreis_brutto=gp_brutto,
                kostenstelle_id=pos_data.get("kostenstelle_id"),
            ))

        # Mark original as storniert
        original.status = RechnungStatus.storniert
        await self.session.flush()
        await self.session.refresh(storno)
        return storno

    async def get_invoices(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Rechnung], int]:
        """List invoices with optional filters and pagination."""
        query = select(Rechnung)
        count_query = select(func.count()).select_from(Rechnung)

        conditions = []
        if filters:
            if filters.get("mitglied_id"):
                conditions.append(Rechnung.mitglied_id == filters["mitglied_id"])
            if filters.get("status"):
                status_val = filters["status"]
                if isinstance(status_val, str):
                    status_val = RechnungStatus(status_val)
                conditions.append(Rechnung.status == status_val)

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(Rechnung.rechnungsdatum.desc())
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        invoices = list(result.scalars().all())
        return invoices, total

    # -- Delete invoice (Löschsperre) ----------------------------------------

    async def delete_invoice(self, rechnung_id: int) -> None:
        """Delete an invoice with Löschsperre enforcement (GoBD compliance).

        - Drafts (entwurf) can always be deleted.
        - Invoices that have been gestellt or beyond can NEVER be deleted
          (must be storniert instead).
        - Even storniert invoices are subject to the 10-year retention period
          (loeschdatum check).
        """
        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")

        # Drafts can always be deleted
        if rechnung.status == RechnungStatus.entwurf:
            await self.session.delete(rechnung)
            await self.session.flush()
            return

        # Gestellt and beyond: never delete, must stornieren
        if rechnung.status != RechnungStatus.storniert:
            raise PermissionError(
                "Gestellte Rechnungen können nicht gelöscht werden. "
                "Bitte stornieren Sie die Rechnung."
            )

        # Storniert invoices: check loeschdatum (retention period)
        if rechnung.loeschdatum and rechnung.loeschdatum > date.today():
            raise PermissionError(
                f"Rechnung unterliegt der gesetzlichen Aufbewahrungspflicht "
                f"bis {rechnung.loeschdatum.isoformat()}"
            )

        await self.session.delete(rechnung)
        await self.session.flush()

    # -- Versand (dispatch tracking) -----------------------------------------

    async def versende_rechnung(
        self,
        rechnung_id: int,
        kanal: str,
        empfaenger: str,
    ) -> Rechnung:
        """Record that an invoice was dispatched.

        Validates the invoice is at least gestellt (not a draft).
        Sets gestellt_am if not already set.
        """
        # Validate kanal
        try:
            VersandKanal(kanal)
        except ValueError:
            raise ValueError(
                f"Ungültiger Versandkanal: {kanal}. "
                f"Erlaubt: {[k.value for k in VersandKanal]}"
            )

        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")

        if rechnung.status == RechnungStatus.entwurf:
            raise ValueError(
                "Entwürfe können nicht versendet werden. "
                "Bitte stellen Sie die Rechnung zuerst."
            )

        rechnung.versand_kanal = kanal
        rechnung.versendet_am = datetime.now()
        rechnung.versendet_an = empfaenger

        # Set gestellt_am if not already set
        if rechnung.gestellt_am is None:
            rechnung.gestellt_am = datetime.now()

        await self.session.flush()
        await self.session.refresh(rechnung)
        return rechnung

    # -- Skonto (early payment discount) ----------------------------------------

    async def calculate_skonto(
        self, rechnung_id: int, reference_date: date | None = None
    ) -> dict[str, Any]:
        """Calculate skonto info for an invoice.

        Returns a dict with:
          - skonto_betrag: the discount amount (how much is deducted)
          - zahlbetrag: the amount to pay after skonto
          - skonto_frist_bis: the deadline date for skonto
          - skonto_verfuegbar: whether skonto can still be used
          - skonto_prozent: the discount percentage
        """
        ref = reference_date or date.today()

        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")

        if rechnung.skonto_prozent is None or rechnung.skonto_frist_tage is None:
            return {
                "skonto_betrag": Decimal("0.00"),
                "zahlbetrag": rechnung.betrag,
                "skonto_frist_bis": None,
                "skonto_verfuegbar": False,
                "skonto_prozent": Decimal("0.00"),
            }

        skonto_frist_bis = rechnung.rechnungsdatum + timedelta(
            days=rechnung.skonto_frist_tage
        )
        skonto_verfuegbar = ref <= skonto_frist_bis

        skonto_abzug = (
            rechnung.summe_netto * rechnung.skonto_prozent / Decimal("100")
        ).quantize(Decimal("0.01"))
        zahlbetrag = (rechnung.betrag - skonto_abzug).quantize(Decimal("0.01"))

        return {
            "skonto_betrag": skonto_abzug,
            "zahlbetrag": zahlbetrag,
            "skonto_frist_bis": skonto_frist_bis,
            "skonto_verfuegbar": skonto_verfuegbar,
            "skonto_prozent": rechnung.skonto_prozent,
        }

    # -- Payments ------------------------------------------------------------

    async def record_payment(
        self,
        rechnung_id: int,
        betrag: Decimal,
        zahlungsart: Zahlungsart | str,
        referenz: str | None = None,
        *,
        apply_skonto: bool = False,
    ) -> Zahlung:
        """Record a payment against an invoice, updating status accordingly.

        If ``apply_skonto`` is True and the invoice has skonto terms that are
        still within the deadline, a second booking entry (Skonto-Abzug) is
        created automatically and the remaining open amount is reduced
        accordingly.
        """
        if isinstance(zahlungsart, str):
            zahlungsart = Zahlungsart(zahlungsart)

        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id == rechnung_id)
        )
        rechnung = result.scalar_one()

        zahlung = Zahlung(
            rechnung_id=rechnung_id,
            betrag=betrag,
            zahlungsdatum=date.today(),
            zahlungsart=zahlungsart,
            referenz=referenz,
        )
        self.session.add(zahlung)
        await self.session.flush()

        # Apply skonto if requested and eligible
        skonto_buchung: Buchung | None = None
        if apply_skonto:
            skonto_info = await self.calculate_skonto(rechnung_id)
            if (
                skonto_info["skonto_verfuegbar"]
                and skonto_info["skonto_betrag"] > Decimal("0")
            ):
                skonto_abzug = skonto_info["skonto_betrag"]
                sphare_value = Sphare(rechnung.sphaere) if rechnung.sphaere else Sphare.ideell
                skonto_buchung = Buchung(
                    buchungsdatum=date.today(),
                    betrag=-skonto_abzug,
                    beschreibung=(
                        f"Skonto-Abzug {rechnung.skonto_prozent}% "
                        f"zu Rechnung {rechnung.rechnungsnummer}"
                    ),
                    konto="4730",  # SKR42: Skontoaufwand
                    gegenkonto="1200",  # Forderungen
                    sphare=sphare_value,
                    mitglied_id=rechnung.mitglied_id,
                )
                self.session.add(skonto_buchung)
                await self.session.flush()

                # Record the skonto as an additional payment entry so
                # bezahlt_betrag tracking stays consistent
                skonto_zahlung = Zahlung(
                    rechnung_id=rechnung_id,
                    betrag=skonto_abzug,
                    zahlungsdatum=date.today(),
                    zahlungsart=zahlungsart,
                    referenz=f"Skonto-Abzug {rechnung.skonto_prozent}%",
                )
                self.session.add(skonto_zahlung)
                await self.session.flush()

        # Recalculate total payments
        pay_result = await self.session.execute(
            select(func.sum(Zahlung.betrag)).where(Zahlung.rechnung_id == rechnung_id)
        )
        total_paid = pay_result.scalar_one() or Decimal("0.00")

        rechnung.bezahlt_betrag = total_paid
        rechnung.offener_betrag = rechnung.betrag - total_paid

        if total_paid >= rechnung.betrag:
            rechnung.status = RechnungStatus.bezahlt
            rechnung.bezahlt_am = datetime.now()
        elif total_paid > Decimal("0"):
            rechnung.status = RechnungStatus.teilbezahlt

        await self.session.flush()
        await self.session.refresh(zahlung)
        return zahlung

    # -- Overdue invoices ----------------------------------------------------

    async def get_overdue_invoices(self) -> list[Rechnung]:
        """Invoices past due date that are still open."""
        open_statuses = [
            RechnungStatus.entwurf,
            RechnungStatus.gestellt,
            RechnungStatus.faellig,
            RechnungStatus.teilbezahlt,
            RechnungStatus.mahnung_1,
            RechnungStatus.mahnung_2,
            RechnungStatus.mahnung_3,
        ]
        result = await self.session.execute(
            select(Rechnung).where(
                Rechnung.status.in_(open_statuses),
                Rechnung.faelligkeitsdatum < date.today(),
            )
        )
        return list(result.scalars().all())

    # -- SEPA XML generation -------------------------------------------------

    async def generate_sepa_xml(self, rechnungen_ids: list[int]) -> str:
        """Generate SEPA pain.008.001.02 XML for direct debit collection."""
        # Load Vereinsstammdaten
        stammdaten = await self.get_vereinsstammdaten()
        club_name = stammdaten.name if stammdaten else "Sportverein e.V."
        club_iban = stammdaten.iban if stammdaten else "DE89370400440532013000"
        club_bic = stammdaten.bic if stammdaten else "COBADEFFXXX"

        # Load invoices
        result = await self.session.execute(
            select(Rechnung).where(Rechnung.id.in_(rechnungen_ids))
        )
        rechnungen = list(result.scalars().all())
        if not rechnungen:
            raise ValueError("No invoices found for the given IDs")

        # Load SEPA mandates for all members in these invoices
        mitglied_ids = [r.mitglied_id for r in rechnungen if r.mitglied_id]
        mandate_result = await self.session.execute(
            select(SepaMandat).where(
                SepaMandat.mitglied_id.in_(mitglied_ids),
                SepaMandat.aktiv == True,  # noqa: E712
            )
        )
        mandate_map: dict[int, SepaMandat] = {
            m.mitglied_id: m for m in mandate_result.scalars().all()
        }

        # Load member data
        member_result = await self.session.execute(
            select(Mitglied).where(Mitglied.id.in_(mitglied_ids))
        )
        member_map: dict[int, Mitglied] = {
            m.id: m for m in member_result.scalars().all()
        }

        # Build XML
        ns = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
        root = ET.Element("Document", xmlns=ns)
        cstmr_ddr = ET.SubElement(root, "CstmrDrctDbtInitn")

        # Group Header
        grp_hdr = ET.SubElement(cstmr_ddr, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        ET.SubElement(grp_hdr, "CreDtTm").text = datetime.now().isoformat()
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(len(rechnungen))
        ctrl_sum = sum(r.betrag for r in rechnungen)
        ET.SubElement(grp_hdr, "CtrlSum").text = str(ctrl_sum)
        initg_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(initg_pty, "Nm").text = club_name

        # Payment Information
        pmt_inf = ET.SubElement(cstmr_ddr, "PmtInf")
        ET.SubElement(pmt_inf, "PmtInfId").text = f"PMT-{datetime.now().strftime('%Y%m%d')}"
        ET.SubElement(pmt_inf, "PmtMtd").text = "DD"
        ET.SubElement(pmt_inf, "NbOfTxs").text = str(len(rechnungen))
        ET.SubElement(pmt_inf, "CtrlSum").text = str(ctrl_sum)

        pmt_tp_inf = ET.SubElement(pmt_inf, "PmtTpInf")
        svc_lvl = ET.SubElement(pmt_tp_inf, "SvcLvl")
        ET.SubElement(svc_lvl, "Cd").text = "SEPA"
        lcl_instrm = ET.SubElement(pmt_tp_inf, "LclInstrm")
        ET.SubElement(lcl_instrm, "Cd").text = "CORE"
        ET.SubElement(pmt_tp_inf, "SeqTp").text = "RCUR"

        ET.SubElement(pmt_inf, "ReqdColltnDt").text = date.today().isoformat()

        cdtr = ET.SubElement(pmt_inf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = club_name

        cdtr_acct = ET.SubElement(pmt_inf, "CdtrAcct")
        cdtr_id = ET.SubElement(cdtr_acct, "Id")
        ET.SubElement(cdtr_id, "IBAN").text = club_iban

        cdtr_agt = ET.SubElement(pmt_inf, "CdtrAgt")
        fin_instn = ET.SubElement(cdtr_agt, "FinInstnId")
        ET.SubElement(fin_instn, "BIC").text = club_bic or "NOTPROVIDED"

        # Transactions
        for rechnung in rechnungen:
            mandat = mandate_map.get(rechnung.mitglied_id) if rechnung.mitglied_id else None
            member = member_map.get(rechnung.mitglied_id) if rechnung.mitglied_id else None

            drct_dbt_tx = ET.SubElement(pmt_inf, "DrctDbtTxInf")

            pmt_id = ET.SubElement(drct_dbt_tx, "PmtId")
            ET.SubElement(pmt_id, "EndToEndId").text = rechnung.rechnungsnummer

            inst_amt = ET.SubElement(drct_dbt_tx, "InstdAmt", Ccy="EUR")
            inst_amt.text = str(rechnung.betrag)

            ddt = ET.SubElement(drct_dbt_tx, "DrctDbtTx")
            mndt_rltd = ET.SubElement(ddt, "MndtRltdInf")
            ET.SubElement(mndt_rltd, "MndtId").text = (
                mandat.mandatsreferenz if mandat else "UNKNOWN"
            )
            ET.SubElement(mndt_rltd, "DtOfSgntr").text = (
                mandat.unterschriftsdatum.isoformat() if mandat else "2024-01-01"
            )

            dbtr_agt = ET.SubElement(drct_dbt_tx, "DbtrAgt")
            dbtr_fin = ET.SubElement(dbtr_agt, "FinInstnId")
            ET.SubElement(dbtr_fin, "BIC").text = (
                mandat.bic if mandat and mandat.bic else "NOTPROVIDED"
            )

            dbtr = ET.SubElement(drct_dbt_tx, "Dbtr")
            ET.SubElement(dbtr, "Nm").text = (
                mandat.kontoinhaber
                if mandat
                else (f"{member.vorname} {member.nachname}" if member else "Unknown")
            )

            dbtr_acct = ET.SubElement(drct_dbt_tx, "DbtrAcct")
            dbtr_acct_id = ET.SubElement(dbtr_acct, "Id")
            ET.SubElement(dbtr_acct_id, "IBAN").text = (
                mandat.iban if mandat else "UNKNOWN"
            )

            rmt_inf = ET.SubElement(drct_dbt_tx, "RmtInf")
            ET.SubElement(rmt_inf, "Ustrd").text = (
                rechnung.verwendungszweck or rechnung.beschreibung
            )

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    # -- Cost centers --------------------------------------------------------

    async def get_cost_centers(self) -> list[Kostenstelle]:
        """List all cost centers."""
        result = await self.session.execute(
            select(Kostenstelle).order_by(Kostenstelle.name)
        )
        return list(result.scalars().all())

    async def create_cost_center(self, data: dict[str, Any]) -> Kostenstelle:
        """Create a new cost center."""
        ks = Kostenstelle(
            name=data["name"],
            beschreibung=data.get("beschreibung"),
            abteilung_id=data.get("abteilung_id"),
            budget=data.get("budget"),
            freigabelimit=data.get("freigabelimit"),
        )
        self.session.add(ks)
        await self.session.flush()
        await self.session.refresh(ks)
        return ks

    async def update_cost_center(
        self, kostenstelle_id: int, data: dict[str, Any]
    ) -> Kostenstelle:
        """Update a cost center."""
        result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.id == kostenstelle_id)
        )
        ks = result.scalar_one_or_none()
        if ks is None:
            raise ValueError(f"Kostenstelle {kostenstelle_id} nicht gefunden")

        for field in ("name", "beschreibung", "abteilung_id", "budget", "freigabelimit"):
            if field in data:
                setattr(ks, field, data[field])

        await self.session.flush()
        await self.session.refresh(ks)
        return ks

    async def delete_cost_center(self, kostenstelle_id: int) -> None:
        """Delete a cost center if no bookings are linked."""
        result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.id == kostenstelle_id)
        )
        ks = result.scalar_one_or_none()
        if ks is None:
            raise ValueError(f"Kostenstelle {kostenstelle_id} nicht gefunden")

        booking_count = await self.session.execute(
            select(func.count()).select_from(Buchung).where(
                Buchung.kostenstelle_id == kostenstelle_id
            )
        )
        if booking_count.scalar_one() > 0:
            raise ValueError(
                "Kostenstelle hat zugeordnete Buchungen und kann nicht geloescht werden."
            )

        await self.session.delete(ks)
        await self.session.flush()

    async def get_budget_status(self, kostenstelle_id: int) -> dict:
        """Get budget status for a cost center."""
        result = await self.session.execute(
            select(Kostenstelle).where(Kostenstelle.id == kostenstelle_id)
        )
        ks = result.scalar_one_or_none()
        if ks is None:
            raise ValueError(f"Kostenstelle {kostenstelle_id} not found")

        spent_result = await self.session.execute(
            select(func.sum(Buchung.betrag)).where(
                Buchung.kostenstelle_id == kostenstelle_id
            )
        )
        spent = spent_result.scalar_one() or Decimal("0.00")
        budget = ks.budget or Decimal("0.00")
        remaining = budget - spent
        freigabelimit = ks.freigabelimit

        return {
            "kostenstelle_id": ks.id,
            "name": ks.name,
            "budget": budget,
            "spent": spent,
            "remaining": remaining,
            "freigabelimit": freigabelimit,
        }

    # -- Internal cost allocation (Leistungsverrechnung) ---------------------

    async def allocate_shared_costs(
        self,
        buchung_id: int,
        allocations: list[dict[str, Any]],
    ) -> list[Buchung]:
        """Distribute a booking across departments/cost centers."""
        # Load parent booking
        result = await self.session.execute(
            select(Buchung).where(Buchung.id == buchung_id)
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise ValueError(f"Buchung {buchung_id} nicht gefunden")

        # Validate allocations sum to 1.0
        total_anteil = sum(Decimal(str(a["anteil"])) for a in allocations)
        if abs(total_anteil - Decimal("1.00")) > Decimal("0.01"):
            raise ValueError(
                f"Summe der Anteile muss 1.0 ergeben, ist aber {total_anteil}"
            )

        children: list[Buchung] = []
        for alloc in allocations:
            anteil = Decimal(str(alloc["anteil"]))
            betrag = (parent.betrag * anteil).quantize(Decimal("0.01"))
            child = Buchung(
                buchungsdatum=parent.buchungsdatum,
                betrag=betrag,
                beschreibung=alloc.get("beschreibung") or parent.beschreibung,
                konto=parent.konto,
                gegenkonto=parent.gegenkonto,
                sphare=parent.sphare,
                mitglied_id=parent.mitglied_id,
                kostenstelle_id=alloc["kostenstelle_id"],
                parent_buchung_id=parent.id,
            )
            self.session.add(child)
            children.append(child)

        await self.session.flush()
        for child in children:
            await self.session.refresh(child)
        return children

    # -- EUeR report ----------------------------------------------------------

    async def get_euer_report(
        self,
        year: int,
        sphare: str | None = None,
    ) -> dict[str, Any]:
        """Generate EUeR (Einnahmen-Ueberschuss-Rechnung) for a given year."""
        conditions = [
            extract("year", Buchung.buchungsdatum) == year,
        ]
        if sphare:
            conditions.append(Buchung.sphare == Sphare(sphare))

        # --- Totals ---
        total_result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag > 0, Buchung.betrag),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag < 0, func.abs(Buchung.betrag)),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
            )
            .select_from(Buchung)
            .where(*conditions)
        )
        row = total_result.one()
        total_einnahmen = row[0] or Decimal("0")
        total_ausgaben = row[1] or Decimal("0")

        # --- By sphere ---
        sphere_result = await self.session.execute(
            select(
                Buchung.sphare,
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag > 0, Buchung.betrag),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag < 0, func.abs(Buchung.betrag)),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
            )
            .select_from(Buchung)
            .where(*conditions)
            .group_by(Buchung.sphare)
        )
        nach_sphare = []
        for s_row in sphere_result.all():
            sph = s_row[0].value if isinstance(s_row[0], Sphare) else str(s_row[0])
            ein = s_row[1] or Decimal("0")
            aus = s_row[2] or Decimal("0")
            nach_sphare.append(
                {
                    "sphare": sph,
                    "einnahmen": float(ein),
                    "ausgaben": float(aus),
                    "ergebnis": float(ein - aus),
                }
            )

        # --- By month ---
        month_result = await self.session.execute(
            select(
                extract("month", Buchung.buchungsdatum).label("monat"),
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag > 0, Buchung.betrag),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag < 0, func.abs(Buchung.betrag)),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
            )
            .select_from(Buchung)
            .where(*conditions)
            .group_by("monat")
            .order_by("monat")
        )
        nach_monat = []
        for m_row in month_result.all():
            monat_num = int(m_row[0])
            ein = m_row[1] or Decimal("0")
            aus = m_row[2] or Decimal("0")
            nach_monat.append(
                {
                    "monat": f"{year}-{monat_num:02d}",
                    "einnahmen": float(ein),
                    "ausgaben": float(aus),
                    "ergebnis": float(ein - aus),
                }
            )

        # --- By cost center ---
        ks_result = await self.session.execute(
            select(
                Kostenstelle.name,
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag > 0, Buchung.betrag),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
                func.coalesce(
                    func.sum(
                        func.case(
                            (Buchung.betrag < 0, func.abs(Buchung.betrag)),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ),
            )
            .select_from(Buchung)
            .join(Kostenstelle, Buchung.kostenstelle_id == Kostenstelle.id)
            .where(*conditions)
            .group_by(Kostenstelle.name)
            .order_by(Kostenstelle.name)
        )
        nach_kostenstelle = []
        for k_row in ks_result.all():
            ein = k_row[1] or Decimal("0")
            aus = k_row[2] or Decimal("0")
            nach_kostenstelle.append(
                {
                    "kostenstelle": k_row[0],
                    "einnahmen": float(ein),
                    "ausgaben": float(aus),
                    "ergebnis": float(ein - aus),
                }
            )

        return {
            "jahr": year,
            "zeitraum": {
                "von": f"{year}-01-01",
                "bis": f"{year}-12-31",
            },
            "gesamt": {
                "einnahmen": float(total_einnahmen),
                "ausgaben": float(total_ausgaben),
                "ergebnis": float(total_einnahmen - total_ausgaben),
            },
            "nach_sphare": nach_sphare,
            "nach_monat": nach_monat,
            "nach_kostenstelle": nach_kostenstelle,
        }

    # -- Donation receipts ---------------------------------------------------

    async def create_donation_receipt(
        self,
        mitglied_id: int,
        betrag: Decimal,
        zweck: str,
    ) -> Spendenbescheinigung:
        """Create a donation receipt."""
        bescheinigung = Spendenbescheinigung(
            mitglied_id=mitglied_id,
            betrag=betrag,
            ausstellungsdatum=date.today(),
            zweck=zweck,
        )
        self.session.add(bescheinigung)
        await self.session.flush()
        await self.session.refresh(bescheinigung)
        return bescheinigung

    # -- SEPA Mandate management ---------------------------------------------

    async def get_mandate(
        self,
        aktiv_filter: bool | None = None,
    ) -> tuple[list[dict], int]:
        """List all SEPA mandates with member name joined."""
        query = select(SepaMandat).options(selectinload(SepaMandat.mitglied))

        if aktiv_filter is not None:
            query = query.where(SepaMandat.aktiv == aktiv_filter)

        query = query.order_by(SepaMandat.id.desc())
        result = await self.session.execute(query)
        mandates = list(result.scalars().all())

        items = []
        for m in mandates:
            mitglied_name = None
            if m.mitglied:
                mitglied_name = f"{m.mitglied.vorname} {m.mitglied.nachname}"
            items.append({
                "id": m.id,
                "mitglied_id": m.mitglied_id,
                "mitglied_name": mitglied_name,
                "iban": m.iban,
                "bic": m.bic,
                "kontoinhaber": m.kontoinhaber,
                "mandatsreferenz": m.mandatsreferenz,
                "unterschriftsdatum": m.unterschriftsdatum,
                "gueltig_ab": m.gueltig_ab,
                "gueltig_bis": m.gueltig_bis,
                "aktiv": m.aktiv,
            })

        return items, len(items)

    async def create_mandat(self, data: dict) -> SepaMandat:
        """Create a new SEPA mandate."""
        mandat = SepaMandat(
            mitglied_id=data["mitglied_id"],
            iban=data["iban"],
            bic=data.get("bic"),
            kontoinhaber=data["kontoinhaber"],
            mandatsreferenz=data["mandatsreferenz"],
            unterschriftsdatum=data["unterschriftsdatum"],
            gueltig_ab=data["gueltig_ab"],
            gueltig_bis=data.get("gueltig_bis"),
            aktiv=True,
        )
        self.session.add(mandat)
        await self.session.flush()
        await self.session.refresh(mandat)
        return mandat

    async def update_mandat(self, mandat_id: int, data: dict) -> SepaMandat:
        """Update an existing SEPA mandate."""
        result = await self.session.execute(
            select(SepaMandat).where(SepaMandat.id == mandat_id)
        )
        mandat = result.scalar_one_or_none()
        if mandat is None:
            raise ValueError(f"SEPA-Mandat mit ID {mandat_id} nicht gefunden.")

        for field in (
            "iban", "bic", "kontoinhaber", "mandatsreferenz",
            "unterschriftsdatum", "gueltig_ab", "gueltig_bis",
        ):
            if field in data:
                setattr(mandat, field, data[field])

        await self.session.flush()
        await self.session.refresh(mandat)
        return mandat

    async def deactivate_mandat(self, mandat_id: int) -> SepaMandat:
        """Deactivate a SEPA mandate (soft-delete)."""
        result = await self.session.execute(
            select(SepaMandat).where(SepaMandat.id == mandat_id)
        )
        mandat = result.scalar_one_or_none()
        if mandat is None:
            raise ValueError(f"SEPA-Mandat mit ID {mandat_id} nicht gefunden.")

        mandat.aktiv = False
        await self.session.flush()
        await self.session.refresh(mandat)
        return mandat
