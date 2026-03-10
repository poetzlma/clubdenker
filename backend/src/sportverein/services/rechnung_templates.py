"""Invoice template definitions — system-defined, not stored in DB."""

from __future__ import annotations


RECHNUNG_TEMPLATES: list[dict] = [
    {
        "id": "quartalsbeitrag",
        "name": "Quartalsbeitrag",
        "beschreibung": "Mitgliedsbeitrag für ein Quartal",
        "rechnungstyp": "mitgliedsbeitrag",
        "sphaere": "ideell",
        "steuerhinweis_text": "Die Leistung ist nach §4 Nr. 22b UStG von der Umsatzsteuer befreit.",
        "zahlungsziel_tage": 14,
        "positionen": [
            {
                "beschreibung": "Mitgliedsbeitrag {kategorie} Q{quartal}/{jahr}",
                "menge": 1,
                "einheit": "×",
                "steuersatz": 0,
                "steuerbefreiungsgrund": "§4 Nr. 22b UStG",
                "platzhalter": {"einzelpreis": "aus_beitragskategorie"},
            }
        ],
    },
    {
        "id": "jahresbeitrag",
        "name": "Jahresbeitrag",
        "beschreibung": "Mitgliedsbeitrag für das gesamte Jahr",
        "rechnungstyp": "mitgliedsbeitrag",
        "sphaere": "ideell",
        "steuerhinweis_text": "Die Leistung ist nach §4 Nr. 22b UStG von der Umsatzsteuer befreit.",
        "zahlungsziel_tage": 14,
        "positionen": [
            {
                "beschreibung": "Jahresbeitrag {kategorie} {jahr}",
                "menge": 1,
                "einheit": "×",
                "steuersatz": 0,
                "steuerbefreiungsgrund": "§4 Nr. 22b UStG",
                "platzhalter": {"einzelpreis": "aus_beitragskategorie"},
            }
        ],
    },
    {
        "id": "kursgebuehr",
        "name": "Kursgebühr",
        "beschreibung": "Gebühr für einen Kurs oder Lehrgang",
        "rechnungstyp": "kursgebuehr",
        "sphaere": "zweckbetrieb",
        "steuerhinweis_text": "Steuerfreier Zweckbetrieb gemäß §65 AO / §4 Nr. 22a UStG.",
        "zahlungsziel_tage": 14,
        "positionen": [
            {
                "beschreibung": "",
                "menge": 1,
                "einheit": "Kurs",
                "steuersatz": 0,
                "steuerbefreiungsgrund": "§4 Nr. 22a UStG",
            }
        ],
    },
    {
        "id": "hallenmiete",
        "name": "Hallenmiete (extern)",
        "beschreibung": "Vermietung von Sportstätten an Externe",
        "rechnungstyp": "hallenmiete",
        "sphaere": "vermoegensverwaltung",
        "empfaenger_typ": "extern",
        "steuerhinweis_text": None,
        "zahlungsziel_tage": 30,
        "positionen": [
            {
                "beschreibung": "Hallenmiete",
                "menge": 1,
                "einheit": "h",
                "steuersatz": 19,
            }
        ],
    },
    {
        "id": "sponsoring",
        "name": "Sponsoringrechnung",
        "beschreibung": "Werbeleistung für Sponsor",
        "rechnungstyp": "sponsoring",
        "sphaere": "wirtschaftlich",
        "empfaenger_typ": "sponsor",
        "steuerhinweis_text": None,
        "zahlungsziel_tage": 30,
        "positionen": [
            {
                "beschreibung": "",
                "menge": 1,
                "einheit": "×",
                "steuersatz": 19,
            }
        ],
    },
    {
        "id": "mahnung_1",
        "name": "Zahlungserinnerung (Stufe 1)",
        "beschreibung": "Freundliche Zahlungserinnerung",
        "rechnungstyp": "mahnung",
        "zahlungsziel_tage": 7,
        "positionen": [],
    },
    {
        "id": "mahnung_2",
        "name": "Erste Mahnung (Stufe 2)",
        "beschreibung": "Formelle erste Mahnung",
        "rechnungstyp": "mahnung",
        "zahlungsziel_tage": 7,
        "positionen": [
            {
                "beschreibung": "Mahngebühr",
                "menge": 1,
                "einheit": "×",
                "einzelpreis_netto": 5.00,
                "steuersatz": 0,
                "steuerbefreiungsgrund": "Verzugsschaden",
            }
        ],
    },
    {
        "id": "mahnung_3",
        "name": "Letzte Mahnung (Stufe 3)",
        "beschreibung": "Letzte Mahnung vor Vereinsausschluss",
        "rechnungstyp": "mahnung",
        "zahlungsziel_tage": 7,
        "positionen": [
            {
                "beschreibung": "Mahngebühr",
                "menge": 1,
                "einheit": "×",
                "einzelpreis_netto": 10.00,
                "steuersatz": 0,
                "steuerbefreiungsgrund": "Verzugsschaden",
            }
        ],
    },
]


class RechnungTemplateService:
    """Service for retrieving invoice templates."""

    def get_templates(self) -> list[dict]:
        """Return all available invoice templates."""
        return RECHNUNG_TEMPLATES

    def get_template(self, template_id: str) -> dict | None:
        """Return a single template by ID, or None if not found."""
        for template in RECHNUNG_TEMPLATES:
            if template["id"] == template_id:
                return template
        return None
