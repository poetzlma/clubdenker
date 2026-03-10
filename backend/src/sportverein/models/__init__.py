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
    Kostenstelle,
    Rechnung,
    RechnungStatus,
    Sphare,
    Spendenbescheinigung,
    Zahlung,
    Zahlungsart,
)
from sportverein.models.kommunikation import (
    EmpfaengerStatus,
    Nachricht,
    NachrichtEmpfaenger,
    NachrichtTyp,
)
from sportverein.models.audit import AuditLog
from sportverein.models.ehrenamt import Aufwandsentschaedigung, AufwandTyp

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
    "Kostenstelle",
    "Rechnung",
    "RechnungStatus",
    "Sphare",
    "Spendenbescheinigung",
    "Zahlung",
    "Zahlungsart",
    "Nachricht",
    "NachrichtEmpfaenger",
    "NachrichtTyp",
    "EmpfaengerStatus",
    "AuditLog",
    "Aufwandsentschaedigung",
    "AufwandTyp",
]


def __getattr__(name: str):
    """Lazy import auth models to avoid circular imports."""
    if name in ("AdminUser", "ApiToken"):
        from sportverein.auth.models import AdminUser, ApiToken
        return {"AdminUser": AdminUser, "ApiToken": ApiToken}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
