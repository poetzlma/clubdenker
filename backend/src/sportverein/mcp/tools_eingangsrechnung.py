"""MCP tool for validating and parsing incoming e-invoices (XRechnung / ZUGFeRD)."""

from __future__ import annotations

from sportverein.mcp.server import mcp
from sportverein.services.eingangsrechnung import EingangsrechnungService


@mcp.tool(
    description=(
        "E-Rechnung (XRechnung / ZUGFeRD) pruefen: "
        "XML-Inhalt analysieren, Pflichtfelder nach §14 UStG validieren "
        "und strukturierte Rechnungsdaten extrahieren."
    )
)
async def eingangsrechnung_pruefen(xml_content: str) -> dict:
    """Parse and validate an incoming e-invoice XML.

    Args:
        xml_content: The XML content of the e-invoice (XRechnung CII or UBL format).

    Returns:
        Dict with parsed fields, format info, and validation warnings.
    """
    svc = EingangsrechnungService()

    try:
        parsed = svc.parse_xml(xml_content)
    except ValueError as exc:
        return {"erfolg": False, "fehler": str(exc)}

    warnungen = await svc.validate_pflichtfelder(parsed)

    # Remove quell_xml from output (too large for MCP response)
    parsed.pop("quell_xml", None)

    # Convert date/Decimal objects to strings for JSON serialization
    serializable = {}
    for key, value in parsed.items():
        if hasattr(value, "isoformat"):
            serializable[key] = value.isoformat()
        elif hasattr(value, "__str__") and not isinstance(value, str):
            serializable[key] = str(value)
        else:
            serializable[key] = value

    return {
        "erfolg": True,
        "daten": serializable,
        "warnungen": warnungen,
        "pflichtfelder_vollstaendig": len(warnungen) == 0,
    }
