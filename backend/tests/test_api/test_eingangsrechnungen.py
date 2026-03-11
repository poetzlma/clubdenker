"""Tests for Eingangsrechnung (incoming invoice) API endpoints."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

SAMPLE_CII_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
  <rsm:ExchangedDocument><ram:ID>TEST-001</ram:ID><ram:TypeCode>380</ram:TypeCode></rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:GrandTotalAmount>119.00</ram:GrandTotalAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""

BASE = "/api/finanzen/eingangsrechnungen"


async def _upload_invoice(client):
    """Helper: upload the sample CII XML and return the response."""
    return await client.post(
        f"{BASE}/upload",
        files={"file": ("invoice.xml", SAMPLE_CII_XML.encode(), "application/xml")},
    )


async def test_list_eingangsrechnungen_empty(client):
    """GET /api/finanzen/eingangsrechnungen returns empty list when no invoices exist."""
    resp = await client.get(BASE)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_upload_eingangsrechnung(client):
    """POST upload with a CII XML creates an Eingangsrechnung."""
    resp = await _upload_invoice(client)
    assert resp.status_code == 201
    data = resp.json()
    rechnung = data["rechnung"]
    assert rechnung["rechnungsnummer"] == "TEST-001"
    assert rechnung["summe_brutto"] == 119.0
    assert rechnung["status"] == "eingegangen"
    assert rechnung["quell_format"] == "xrechnung"
    # warnungen should list missing Pflichtfelder (no seller name, no netto)
    assert isinstance(data["warnungen"], list)
    assert len(data["warnungen"]) > 0


async def test_get_eingangsrechnung_not_found(client):
    """GET for a non-existent ID returns 404."""
    resp = await client.get(f"{BASE}/999")
    assert resp.status_code == 404
    assert "nicht gefunden" in resp.json()["detail"]


async def test_upload_then_get_detail(client):
    """Upload an invoice then fetch its detail including quell_xml."""
    upload_resp = await _upload_invoice(client)
    rechnung_id = upload_resp.json()["rechnung"]["id"]

    resp = await client.get(f"{BASE}/{rechnung_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["rechnungsnummer"] == "TEST-001"
    assert "CrossIndustryInvoice" in detail["quell_xml"]


async def test_update_eingangsrechnung_status(client):
    """Create an invoice then update its status to freigegeben."""
    upload_resp = await _upload_invoice(client)
    rechnung_id = upload_resp.json()["rechnung"]["id"]

    resp = await client.put(
        f"{BASE}/{rechnung_id}/status",
        json={"status": "freigegeben"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "freigegeben"


async def test_update_status_invalid(client):
    """Updating with an invalid status returns 400."""
    upload_resp = await _upload_invoice(client)
    rechnung_id = upload_resp.json()["rechnung"]["id"]

    resp = await client.put(
        f"{BASE}/{rechnung_id}/status",
        json={"status": "ungueltig"},
    )
    assert resp.status_code == 400


async def test_eingangsrechnungen_require_auth(unauthed_client):
    """Unauthenticated requests are rejected."""
    resp = await unauthed_client.get(BASE)
    assert resp.status_code in (401, 403, 422)

    resp = await unauthed_client.post(
        f"{BASE}/upload",
        files={"file": ("invoice.xml", b"<xml/>", "application/xml")},
    )
    assert resp.status_code in (401, 403, 422)

    resp = await unauthed_client.get(f"{BASE}/1")
    assert resp.status_code in (401, 403, 422)

    resp = await unauthed_client.put(
        f"{BASE}/1/status",
        json={"status": "freigegeben"},
    )
    assert resp.status_code in (401, 403, 422)
