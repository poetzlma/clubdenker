"""PDF generation for invoices using reportlab."""

from __future__ import annotations

import io
from collections import defaultdict
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sportverein.models.finanzen import Rechnung, RechnungTyp
from sportverein.models.vereinsstammdaten import Vereinsstammdaten

# Page dimensions
_PAGE_WIDTH, _PAGE_HEIGHT = A4
_MARGIN = 2 * cm


def _fmt_decimal(value: Decimal) -> str:
    """Format a Decimal to German number format: 1.234,56 EUR."""
    v = abs(value)
    int_part = int(v)
    frac_part = abs(v - int_part)
    frac_str = f"{frac_part:.2f}"[1:]  # ".56"
    # Group integer part with dots
    int_str = f"{int_part:,}".replace(",", ".")
    sign = "-" if value < 0 else ""
    return f"{sign}{int_str}{frac_str.replace('.', ',')} \u20ac"


def _fmt_date(d) -> str:
    """Format date as DD.MM.YYYY."""
    if d is None:
        return ""
    return d.strftime("%d.%m.%Y")


def _fmt_iban(iban: str | None) -> str:
    """Format IBAN with spaces every 4 chars."""
    if not iban:
        return ""
    clean = iban.replace(" ", "")
    return " ".join(clean[i : i + 4] for i in range(0, len(clean), 4))


def _fmt_pct(value: Decimal) -> str:
    """Format a tax rate like 0%, 7%, 19%."""
    v = int(value) if value == int(value) else float(value)
    return f"{v}%"


class RechnungPdfService:
    """Generate professional German invoice PDFs."""

    def _build_styles(self) -> dict:
        base = getSampleStyleSheet()
        styles = {
            "title": ParagraphStyle(
                "InvoiceTitle",
                parent=base["Heading1"],
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=0,
            ),
            "subtitle": ParagraphStyle(
                "InvoiceSubtitle",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#555555"),
            ),
            "verein_name": ParagraphStyle(
                "VereinName",
                parent=base["Heading2"],
                fontSize=14,
                leading=17,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=2,
            ),
            "verein_address": ParagraphStyle(
                "VereinAddress",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#555555"),
            ),
            "sender_line": ParagraphStyle(
                "SenderLine",
                parent=base["Normal"],
                fontSize=7,
                leading=9,
                textColor=colors.HexColor("#888888"),
                spaceAfter=2,
            ),
            "recipient": ParagraphStyle(
                "Recipient",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
            ),
            "meta_label": ParagraphStyle(
                "MetaLabel",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#666666"),
            ),
            "meta_value": ParagraphStyle(
                "MetaValue",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
            ),
            "body_italic": ParagraphStyle(
                "BodyItalic",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#555555"),
                fontName="Helvetica-Oblique",
            ),
            "body_bold": ParagraphStyle(
                "BodyBold",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
                fontName="Helvetica-Bold",
            ),
            "footer": ParagraphStyle(
                "Footer",
                parent=base["Normal"],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#999999"),
            ),
            "table_header": ParagraphStyle(
                "TableHeader",
                parent=base["Normal"],
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#333333"),
                fontName="Helvetica-Bold",
            ),
            "table_header_right": ParagraphStyle(
                "TableHeaderRight",
                parent=base["Normal"],
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#333333"),
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            ),
            "table_cell": ParagraphStyle(
                "TableCell",
                parent=base["Normal"],
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#1a1a1a"),
            ),
            "table_cell_right": ParagraphStyle(
                "TableCellRight",
                parent=base["Normal"],
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#1a1a1a"),
                alignment=TA_RIGHT,
            ),
            "total_label": ParagraphStyle(
                "TotalLabel",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#333333"),
                alignment=TA_RIGHT,
            ),
            "total_label_bold": ParagraphStyle(
                "TotalLabelBold",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            ),
            "total_value": ParagraphStyle(
                "TotalValue",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#333333"),
                alignment=TA_RIGHT,
            ),
            "total_value_bold": ParagraphStyle(
                "TotalValueBold",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                textColor=colors.HexColor("#1a1a1a"),
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            ),
        }
        return styles

    def _get_title(self, rechnung: Rechnung) -> str:
        if rechnung.rechnungstyp == RechnungTyp.storno:
            return "STORNORECHNUNG"
        if rechnung.rechnungstyp == RechnungTyp.mahnung:
            return "MAHNUNG"
        return "RECHNUNG"

    async def generate_rechnung_pdf(self, session: AsyncSession, rechnung_id: int) -> bytes:
        """Generate PDF for invoice, returns PDF bytes."""
        # Load invoice with positionen
        result = await session.execute(
            select(Rechnung)
            .where(Rechnung.id == rechnung_id)
            .options(selectinload(Rechnung.positionen))
        )
        rechnung = result.scalar_one_or_none()
        if rechnung is None:
            raise ValueError(f"Rechnung {rechnung_id} nicht gefunden")

        # Load storno original if applicable
        original_rechnung = None
        if rechnung.storno_von_id is not None:
            orig_result = await session.execute(
                select(Rechnung).where(Rechnung.id == rechnung.storno_von_id)
            )
            original_rechnung = orig_result.scalar_one_or_none()

        # Load Vereinsstammdaten
        stamm_result = await session.execute(select(Vereinsstammdaten).limit(1))
        stammdaten = stamm_result.scalar_one_or_none()

        return self._render_pdf(rechnung, stammdaten, original_rechnung)

    def _render_pdf(
        self,
        rechnung: Rechnung,
        stammdaten: Vereinsstammdaten | None,
        original_rechnung: Rechnung | None,
    ) -> bytes:
        buffer = io.BytesIO()
        styles = self._build_styles()

        # Club info defaults
        verein_name = stammdaten.name if stammdaten else "Sportverein e.V."
        verein_strasse = stammdaten.strasse if stammdaten else ""
        verein_plz = stammdaten.plz if stammdaten else ""
        verein_ort = stammdaten.ort if stammdaten else ""
        verein_steuernr = stammdaten.steuernummer if stammdaten else None
        verein_ust_id = stammdaten.ust_id if stammdaten else None
        verein_iban = stammdaten.iban if stammdaten else ""
        verein_bic = stammdaten.bic if stammdaten else ""
        verein_register = stammdaten.registergericht if stammdaten else None
        verein_registernr = stammdaten.registernummer if stammdaten else None

        sender_line = f"{verein_name} \u00b7 {verein_strasse} \u00b7 {verein_plz} {verein_ort}"

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=_MARGIN,
            rightMargin=_MARGIN,
            topMargin=_MARGIN,
            bottomMargin=_MARGIN + 1 * cm,
        )

        # Build footer function
        footer_parts = [verein_name]
        if verein_register and verein_registernr:
            footer_parts.append(f"{verein_register} {verein_registernr}")
        if verein_steuernr:
            footer_parts.append(f"StNr: {verein_steuernr}")
        if verein_iban:
            footer_parts.append(f"IBAN: {_fmt_iban(verein_iban)}")
        footer_text = " | ".join(footer_parts)

        def _on_page(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#999999"))
            canvas.drawCentredString(_PAGE_WIDTH / 2, _MARGIN - 0.5 * cm, footer_text)
            canvas.restoreState()

        story = []

        # ---- HEADER ----
        usable_width = _PAGE_WIDTH - 2 * _MARGIN
        left_w = usable_width * 0.55
        right_w = usable_width * 0.45

        header_data = [
            [
                Paragraph(verein_name, styles["verein_name"]),
                Paragraph(self._get_title(rechnung), styles["title"]),
            ],
            [
                Paragraph(
                    f"{verein_strasse}<br/>{verein_plz} {verein_ort}",
                    styles["verein_address"],
                ),
                Paragraph(rechnung.rechnungsnummer, styles["subtitle"]),
            ],
        ]
        header_table = Table(header_data, colWidths=[left_w, right_w], hAlign="LEFT")
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 1.2 * cm))

        # ---- SENDER LINE + RECIPIENT ----
        story.append(Paragraph(sender_line, styles["sender_line"]))
        story.append(Spacer(1, 2 * mm))

        empf_name = rechnung.empfaenger_name or ""
        empf_strasse = rechnung.empfaenger_strasse or ""
        empf_plz = rechnung.empfaenger_plz or ""
        empf_ort = rechnung.empfaenger_ort or ""

        recipient_text = empf_name
        if empf_strasse:
            recipient_text += f"<br/>{empf_strasse}"
        if empf_plz or empf_ort:
            recipient_text += f"<br/>{empf_plz} {empf_ort}".strip()

        # Recipient left, metadata right
        meta_rows = []
        meta_rows.append(("Rechnungsdatum:", _fmt_date(rechnung.rechnungsdatum)))
        meta_rows.append(("Rechnungsnummer:", rechnung.rechnungsnummer))

        if rechnung.leistungszeitraum_von and rechnung.leistungszeitraum_bis:
            meta_rows.append(
                (
                    "Leistungszeitraum:",
                    f"{_fmt_date(rechnung.leistungszeitraum_von)} \u2013 {_fmt_date(rechnung.leistungszeitraum_bis)}",
                )
            )
        elif rechnung.leistungsdatum:
            meta_rows.append(("Leistungsdatum:", _fmt_date(rechnung.leistungsdatum)))

        meta_rows.append(("F\u00e4lligkeitsdatum:", _fmt_date(rechnung.faelligkeitsdatum)))

        if verein_steuernr:
            meta_rows.append(("Steuernummer:", verein_steuernr))
        if verein_ust_id:
            meta_rows.append(("USt-IdNr:", verein_ust_id))

        meta_content = ""
        for label, val in meta_rows:
            meta_content += f"<b>{label}</b> {val}<br/>"

        addr_meta_data = [
            [
                Paragraph(recipient_text, styles["recipient"]),
                Paragraph(meta_content, styles["meta_value"]),
            ]
        ]
        addr_meta_table = Table(addr_meta_data, colWidths=[left_w, right_w], hAlign="LEFT")
        addr_meta_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(addr_meta_table)
        story.append(Spacer(1, 1 * cm))

        # ---- STORNO / MAHNUNG special references ----
        if rechnung.rechnungstyp == RechnungTyp.storno and original_rechnung:
            story.append(
                Paragraph(
                    f"Stornierung zu Rechnung Nr. {original_rechnung.rechnungsnummer}",
                    styles["body_bold"],
                )
            )
            story.append(Spacer(1, 4 * mm))

        if rechnung.rechnungstyp == RechnungTyp.mahnung:
            mahnstufe = rechnung.mahnstufe or 1
            mahnstufe_text = {
                1: "1. Mahnung",
                2: "2. Mahnung",
                3: "3. Mahnung \u2013 letzte Aufforderung",
            }.get(mahnstufe, f"{mahnstufe}. Mahnung")
            story.append(Paragraph(mahnstufe_text, styles["body_bold"]))
            if original_rechnung:
                story.append(
                    Paragraph(
                        f"Bezug: Rechnung Nr. {original_rechnung.rechnungsnummer}",
                        styles["body"],
                    )
                )
            story.append(Spacer(1, 4 * mm))

        # ---- DESCRIPTION ----
        if rechnung.beschreibung:
            story.append(Paragraph(rechnung.beschreibung, styles["body"]))
            story.append(Spacer(1, 4 * mm))

        # ---- POSITIONEN TABLE ----
        positionen = sorted(rechnung.positionen, key=lambda p: p.position_nr)

        if positionen:
            col_widths = [
                usable_width * 0.06,  # Pos
                usable_width * 0.34,  # Beschreibung
                usable_width * 0.08,  # Menge
                usable_width * 0.08,  # Einheit
                usable_width * 0.16,  # Einzelpreis
                usable_width * 0.12,  # USt
                usable_width * 0.16,  # Gesamt
            ]

            table_data = [
                [
                    Paragraph("Pos", styles["table_header"]),
                    Paragraph("Beschreibung", styles["table_header"]),
                    Paragraph("Menge", styles["table_header_right"]),
                    Paragraph("Einheit", styles["table_header"]),
                    Paragraph("Einzelpreis", styles["table_header_right"]),
                    Paragraph("USt", styles["table_header_right"]),
                    Paragraph("Gesamt", styles["table_header_right"]),
                ]
            ]

            for pos in positionen:
                table_data.append(
                    [
                        Paragraph(str(pos.position_nr), styles["table_cell"]),
                        Paragraph(pos.beschreibung, styles["table_cell"]),
                        Paragraph(
                            str(int(pos.menge)) if pos.menge == int(pos.menge) else str(pos.menge),
                            styles["table_cell_right"],
                        ),
                        Paragraph(
                            "\u00d7" if pos.einheit == "x" else pos.einheit, styles["table_cell"]
                        ),
                        Paragraph(_fmt_decimal(pos.einzelpreis_netto), styles["table_cell_right"]),
                        Paragraph(_fmt_pct(pos.steuersatz), styles["table_cell_right"]),
                        Paragraph(_fmt_decimal(pos.gesamtpreis_brutto), styles["table_cell_right"]),
                    ]
                )

            pos_table = Table(table_data, colWidths=col_widths, hAlign="LEFT")

            # Build style commands
            style_cmds: list = [
                # Header row
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#cccccc")),
                # General
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                # Bottom line on last row
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ]
            # Alternating row shading
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafafa")))

            pos_table.setStyle(TableStyle(style_cmds))
            story.append(pos_table)
        else:
            # No line items, show single line
            story.append(
                Paragraph(
                    f"Betrag: {_fmt_decimal(rechnung.betrag)}",
                    styles["body_bold"],
                )
            )

        story.append(Spacer(1, 6 * mm))

        # ---- TOTALS ----
        totals_col_widths = [usable_width * 0.65, usable_width * 0.35]

        totals_data = []
        totals_data.append(
            [
                Paragraph("Summe Netto:", styles["total_label"]),
                Paragraph(_fmt_decimal(rechnung.summe_netto), styles["total_value"]),
            ]
        )

        # Group tax by rate
        if positionen:
            tax_by_rate: dict[Decimal, Decimal] = defaultdict(Decimal)
            for pos in positionen:
                tax_by_rate[pos.steuersatz] += pos.gesamtpreis_steuer
            for rate in sorted(tax_by_rate.keys()):
                totals_data.append(
                    [
                        Paragraph(f"USt {_fmt_pct(rate)}:", styles["total_label"]),
                        Paragraph(_fmt_decimal(tax_by_rate[rate]), styles["total_value"]),
                    ]
                )
        else:
            totals_data.append(
                [
                    Paragraph("USt 0%:", styles["total_label"]),
                    Paragraph(_fmt_decimal(rechnung.summe_steuer), styles["total_value"]),
                ]
            )

        totals_data.append(
            [
                Paragraph("Gesamtbetrag:", styles["total_label_bold"]),
                Paragraph(_fmt_decimal(rechnung.betrag), styles["total_value_bold"]),
            ]
        )

        totals_table = Table(totals_data, colWidths=totals_col_widths, hAlign="LEFT")
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#333333")),
                ]
            )
        )
        story.append(totals_table)
        story.append(Spacer(1, 6 * mm))

        # ---- STEUERHINWEIS ----
        if rechnung.steuerhinweis_text:
            story.append(Paragraph(rechnung.steuerhinweis_text, styles["body_italic"]))
            story.append(Spacer(1, 4 * mm))

        # ---- SKONTO HINWEIS ----
        if (
            rechnung.skonto_prozent is not None
            and rechnung.skonto_frist_tage is not None
            and rechnung.skonto_betrag is not None
            and rechnung.rechnungsdatum is not None
        ):
            from datetime import timedelta

            skonto_bis = rechnung.rechnungsdatum + timedelta(days=rechnung.skonto_frist_tage)
            skonto_text = (
                f"Bei Zahlung bis {_fmt_date(skonto_bis)}: "
                f"{_fmt_pct(rechnung.skonto_prozent)} Skonto "
                f"({_fmt_decimal(rechnung.skonto_betrag)})"
            )
            story.append(Paragraph(skonto_text, styles["body_bold"]))
            story.append(Spacer(1, 4 * mm))

        # ---- ZAHLUNGSINFORMATION ----
        payment_text = (
            f"Bitte \u00fcberweisen Sie den Betrag bis zum "
            f"{_fmt_date(rechnung.faelligkeitsdatum)} auf folgendes Konto:"
        )
        story.append(Paragraph(payment_text, styles["body"]))
        story.append(Spacer(1, 3 * mm))

        payment_details = []
        payment_details.append(f"<b>Kontoinhaber:</b> {verein_name}")
        if verein_iban:
            payment_details.append(f"<b>IBAN:</b> {_fmt_iban(verein_iban)}")
        if verein_bic:
            payment_details.append(f"<b>BIC:</b> {verein_bic}")
        if rechnung.verwendungszweck:
            payment_details.append(f"<b>Verwendungszweck:</b> {rechnung.verwendungszweck}")

        for line in payment_details:
            story.append(Paragraph(line, styles["body"]))

        doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
        return buffer.getvalue()
