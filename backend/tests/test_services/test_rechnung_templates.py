"""Tests for RechnungTemplateService."""

from __future__ import annotations

from sportverein.services.rechnung_templates import (
    RECHNUNG_TEMPLATES,
    RechnungTemplateService,
)


class TestRechnungTemplateService:
    def setup_method(self) -> None:
        self.svc = RechnungTemplateService()

    def test_get_templates_returns_all(self) -> None:
        templates = self.svc.get_templates()
        assert len(templates) == len(RECHNUNG_TEMPLATES)
        assert templates is RECHNUNG_TEMPLATES

    def test_get_templates_contains_expected_ids(self) -> None:
        ids = {t["id"] for t in self.svc.get_templates()}
        expected = {
            "quartalsbeitrag",
            "jahresbeitrag",
            "kursgebuehr",
            "hallenmiete",
            "sponsoring",
            "mahnung_1",
            "mahnung_2",
            "mahnung_3",
        }
        assert ids == expected

    def test_get_template_existing(self) -> None:
        t = self.svc.get_template("quartalsbeitrag")
        assert t is not None
        assert t["name"] == "Quartalsbeitrag"
        assert t["rechnungstyp"] == "mitgliedsbeitrag"
        assert t["sphaere"] == "ideell"

    def test_get_template_nonexistent(self) -> None:
        assert self.svc.get_template("nonexistent") is None

    def test_all_templates_have_required_fields(self) -> None:
        required = {"id", "name", "beschreibung", "rechnungstyp", "zahlungsziel_tage", "positionen"}
        for t in self.svc.get_templates():
            missing = required - set(t.keys())
            assert not missing, f"Template {t['id']} missing fields: {missing}"

    def test_mahnung_templates_have_correct_fees(self) -> None:
        m1 = self.svc.get_template("mahnung_1")
        m2 = self.svc.get_template("mahnung_2")
        m3 = self.svc.get_template("mahnung_3")
        assert m1 is not None and len(m1["positionen"]) == 0
        assert m2 is not None and m2["positionen"][0]["einzelpreis_netto"] == 5.00
        assert m3 is not None and m3["positionen"][0]["einzelpreis_netto"] == 10.00

    def test_sphaere_assignments(self) -> None:
        """Verify tax sphere assignments are correct for each template type."""
        t = {tmpl["id"]: tmpl for tmpl in self.svc.get_templates()}
        assert t["quartalsbeitrag"]["sphaere"] == "ideell"
        assert t["jahresbeitrag"]["sphaere"] == "ideell"
        assert t["kursgebuehr"]["sphaere"] == "zweckbetrieb"
        assert t["hallenmiete"]["sphaere"] == "vermoegensverwaltung"
        assert t["sponsoring"]["sphaere"] == "wirtschaftlich"

    def test_hallenmiete_and_sponsoring_have_vat(self) -> None:
        for tid in ["hallenmiete", "sponsoring"]:
            t = self.svc.get_template(tid)
            assert t is not None
            for pos in t["positionen"]:
                assert pos["steuersatz"] == 19

    def test_ideell_templates_are_vat_exempt(self) -> None:
        for tid in ["quartalsbeitrag", "jahresbeitrag"]:
            t = self.svc.get_template(tid)
            assert t is not None
            for pos in t["positionen"]:
                assert pos["steuersatz"] == 0
                assert "steuerbefreiungsgrund" in pos
