"""All models re-exported so Alembic and other tools can discover them."""

from sportverein.models.base import Base, TimestampMixin
from sportverein.models.mitglied import (
    Abteilung,
    BeitragKategorie,
    Mitglied,
    MitgliedAbteilung,
    MitgliedStatus,
)
from sportverein.models.beitrag import BeitragsKategorie, SepaMandat
from sportverein.models.finanzen import (
    Buchung,
    Eingangsrechnung,
    EingangsrechnungFormat,
    EingangsrechnungStatus,
    EmpfaengerTyp,
    Kostenstelle,
    Rechnung,
    RechnungFormat,
    RechnungStatus,
    RechnungTyp,
    Rechnungsposition,
    Sphare,
    Spendenbescheinigung,
    Zahlung,
    Zahlungsart,
)
from sportverein.models.vereinsstammdaten import Vereinsstammdaten
from sportverein.models.kommunikation import (
    EmpfaengerStatus,
    Nachricht,
    NachrichtEmpfaenger,
    NachrichtTyp,
)
from sportverein.models.audit import AuditLog
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp
from sportverein.models.training import Anwesenheit, Trainingsgruppe, Wochentag

__all__ = [
    "Base",
    "TimestampMixin",
    "Abteilung",
    "BeitragKategorie",
    "Mitglied",
    "MitgliedAbteilung",
    "MitgliedStatus",
    "BeitragsKategorie",
    "SepaMandat",
    "Buchung",
    "Eingangsrechnung",
    "EingangsrechnungFormat",
    "EingangsrechnungStatus",
    "EmpfaengerTyp",
    "Kostenstelle",
    "Rechnung",
    "RechnungFormat",
    "RechnungStatus",
    "RechnungTyp",
    "Rechnungsposition",
    "Sphare",
    "Spendenbescheinigung",
    "Vereinsstammdaten",
    "Zahlung",
    "Zahlungsart",
    "Nachricht",
    "NachrichtEmpfaenger",
    "NachrichtTyp",
    "EmpfaengerStatus",
    "AuditLog",
    "Aufwandsentschaedigung",
    "AufwandTyp",
    "Anwesenheit",
    "Trainingsgruppe",
    "Wochentag",
]


def __getattr__(name: str):
    """Lazy import auth models to avoid circular imports."""
    if name in ("AdminUser", "ApiToken"):
        from sportverein.auth.models import AdminUser, ApiToken
        return {"AdminUser": AdminUser, "ApiToken": ApiToken}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
