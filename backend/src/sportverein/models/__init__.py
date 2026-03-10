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
from sportverein.auth.models import AdminUser, ApiToken

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
    "AdminUser",
    "ApiToken",
]
