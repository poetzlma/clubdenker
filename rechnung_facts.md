rechnung_facts.md
Vollständige Rechnungsspezifikation für Vereinsverwaltungssoftware
Sportverein (300–1.000 Mitglieder) · Stand März 2026 · Rechtsstand Deutschland

Zweck dieses Dokuments: Checkliste und Entwicklungsreferenz für alle Rechnungs-Features.
Jeder Abschnitt ist mit [ ] Checkboxen versehen — abhakbar bei Implementierung.
Quellen: §14 UStG, §33 UStDV, §147 AO, GoBD, Wachstumschancengesetz 2024, BMF-Schreiben 15.10.2024


1. Pflichtfelder nach §14 Abs. 4 UStG
Dies sind die gesetzlich zwingenden Mindestangaben. Fehlt ein Feld, ist die Rechnung steuerrechtlich ungültig und der Empfänger verliert seinen Vorsteuerabzug.
1.1 Aussteller (Verein)
FeldPflichtHinweisVollständiger Vereinsname✅ Pflichtexakt wie im VereinsregisterVollständige Anschrift✅ PflichtPostfach oder c/o reicht auchSteuernummer✅ Pflichtentweder Steuernr. ODER USt-IdNr.USt-Identifikationsnummer✅ Pflicht (alternativ)nur wenn vorhanden
Felder in der Software:

 verein_name — aus Vereinsstammdaten, nicht editierbar je Rechnung
 verein_strasse, verein_plz, verein_ort
 verein_steuernummer
 verein_ust_id (optional, wenn vorhanden)
 Validierung: mindestens eines von steuernummer ODER ust_id muss befüllt sein

1.2 Empfänger
FeldPflichtHinweisVollständiger Name✅ Pflichtbei Privatpersonen Vor- + NachnameVollständige Anschrift✅ PflichtRechnungsadresse, nicht Lieferadresse
Felder in der Software:
‚
 empfaenger_name — aus Mitgliederstammdaten oder manuell
 empfaenger_strasse, empfaenger_plz, empfaenger_ort
 empfaenger_ustid — nur bei B2B-Rechnungen (Sponsoren, Dienstleister)
 Warnung wenn Adresse im Mitgliedsprofil fehlt

1.3 Rechnungsmetadaten
FeldPflichtHinweisAusstellungsdatum✅ PflichtDatum der ErstellungRechnungsnummer✅ Pflichtfortlaufend, eindeutig, einmaligLeistungszeitpunkt / -zeitraum✅ Pflichtauch wenn = Ausstellungsdatum → dann explizit vermerken
Felder in der Software:

 rechnungsdatum — automatisch auf Erstellungstag, editierbar
 rechnungsnummer — automatisch generiert, nie manuell, Schema konfigurierbar
 leistungsdatum — bei einmaligen Leistungen ein Datum
 leistungszeitraum_von, leistungszeitraum_bis — bei Dauerschuldverhältnissen (Quartalsbeiträge)
 Hinweis im UI: „Leistungszeitraum entspricht Ausstellungsdatum" als Checkbox (spart Eingabe)

1.4 Leistungsbeschreibung
FeldPflichtHinweisMenge✅ Pflichtbei Mitgliedsbeiträgen: „1×"Art der Leistung✅ Pflichthandelsübliche Bezeichnung, keine Abkürzungen
Felder je Rechnungsposition:

 position_menge — Zahl (kann Dezimal sein: 2,5h)
 position_einheit — frei: „×", „h", „Monat", „Kurs", „Stück"
 position_beschreibung — Freitext + Auswahl aus Vorlagen
 position_einzelpreis_netto
 position_steuersatz — 0%, 7%, 19% oder „steuerbefreit"
 position_steuerbefreiungsgrund — Pflichtfeld wenn Steuersatz = 0%/befreit (z.B. §4 Nr. 22b UStG)
 position_gesamtpreis_netto
 Mehrere Positionen möglich (n:1 zu Rechnung)

1.5 Betragsfelder
FeldPflichtHinweisNettobetrag (aufgeschlüsselt nach Steuersatz)✅ Pflichtwenn mehrere Sätze → je GruppeSteuersatz✅ Pflichtoder Hinweis auf SteuerbefreiungSteuerbetrag✅ Pflichtoder 0,00 € mit BegründungBruttobetrag (Gesamtbetrag)✅ PflichtVorauszahlungen / Anzahlungen✅ Pflicht (wenn vorhanden)müssen in Endrechnung abgezogen werden
Felder in der Software:

 summe_netto — automatisch berechnet
 summe_steuer — automatisch berechnet
 summe_brutto — automatisch berechnet
 anzahlung_betrag — wenn Vorauszahlung erfolgt
 anzahlung_referenz — Verweis auf Vorausrechnungs-Nr.
 restbetrag — Brutto minus Anzahlung


2. Rechnungsnummern-Logik
Die Rechnungsnummer ist das kritischste Feld — Fehler hier führen zu steuerlichen Problemen.
Anforderungen (§14 Abs. 4 Nr. 4 UStG)

Fortlaufend (keine Lücken)
Einmalig (keine Duplikate)
Vom Aussteller eindeutig zuordenbar
Mehrere Nummernkreise erlaubt (z.B. je Sphäre)

Empfohlenes Schema für Sportvereine
{JAHR}-{SPHÄRE}-{LAUFNR}

Beispiele:
2026-IB-0147    (Ideeller Bereich, Mitgliedsbeiträge)
2026-ZB-0034    (Zweckbetrieb, Kurse/Turniere)
2026-WG-0012    (Wirtschaftl. Geschäftsbetrieb, Werbung)
2026-VM-0003    (Vermögensverwaltung, Hallenmiete)
Felder in der Software:

 nummernkreis_schema — konfigurierbar: {YYYY}-{SPHAERE}-{NR:4} etc.
 nummernkreis_sphare — enum: IB / ZB / WG / VM
 laufende_nummer — automatisch, pro Nummernkreis und Jahr
 Kein manuelles Überschreiben der Rechnungsnummer nach Erstellung
 Jahresreset: Laufnummer beginnt am 1. Januar neu
 Lückenerkennung: System warnt bei unerwarteter Lücke im Nummernkreis


3. Steuerliche Sphären und Steuerhinweise
Der häufigste Fehler bei Vereinen — jede Rechnung muss der richtigen Sphäre zugeordnet sein.
Sphärenmatrix für Sportvereine
SphäreTypische VorgängeUSt?Pflichthinweis auf RechnungIdeeller BereichMitgliedsbeiträge, Aufnahmegebühren, Spenden (keine Gegenleistung)Nein„Gemäß §4 Nr. 22b UStG von der Umsatzsteuer befreit"ZweckbetriebStartgelder, Kursgebühren, Sportveranstaltungen für MitgliederNein (wenn §65 AO)„Steuerfreier Zweckbetrieb i.S.d. §65 AO / §4 Nr. 22a UStG"VermögensverwaltungHallenverleih an Externe, Zinserträge, Pachten19%Normaler SteuerausweisWirtschaftl. GeschäftsbetriebTrikotwerbung, Catering, Merchandise, Festzelt19% (oder 7%)Normaler Steuerausweis
Felder in der Software:

 sphaere — enum: IDEELL / ZWECKBETRIEB / VERMOEGEN / WIRTSCHAFT
 Automatische Vorschlag-Logik basierend auf Leistungsart
 steuerhinweis_text — bei Steuerbefreiung Pflichtfeld
 Validierung: wenn steuersatz = 0, dann steuerhinweis_text nicht leer
 SKR42-Kostenstelle automatisch aus Sphäre ableiten

Steuerbefreiungshinweise (Textvorlagen im System)
§4 Nr. 22b UStG:
"Die Leistung ist nach §4 Nr. 22b UStG von der Umsatzsteuer befreit.
 Mitgliedsbeiträge an gemeinnützige Sportvereine sind umsatzsteuerfrei."

§65 AO / §4 Nr. 22a UStG:
"Steuerfreier Zweckbetrieb gemäß §65 AO. Die Veranstaltung dient
 unmittelbar der Verwirklichung des gemeinnützigen Vereinszwecks."

§19 UStG (Kleinunternehmer, falls zutreffend):
"Gemäß §19 UStG wird keine Umsatzsteuer berechnet."

 Textvorlagen pro Steuerbefreiungsgrund konfigurierbar
 Automatische Auswahl basierend auf Sphäre


4. Rechnungsarten im Vereinskontext
4.1 AUSGEHENDE Rechnungen (Verein stellt aus)
A) Mitgliedsbeitragsrechnung

 Empfänger: Mitglied (aus Mitgliederstamm)
 Leistung: Grundbeitrag + optionale Spartenbeiträge
 Zeitraum: Quartal / Halbjahr / Jahr
 Steuer: §4 Nr. 22b UStG, 0%
 Massengeneration: für alle fälligen Mitglieder gleichzeitig
 SEPA-Verknüpfung: direkter Link zur SEPA-Lastschrift-Datei
 Kombination: Familienrechnung möglich (mehrere Mitglieder, eine Rechnung)

B) Mahnrechnung / Zahlungserinnerung

 Bezug auf ursprüngliche Rechnungsnummer
 Mahnstufe: 1 (Erinnerung) / 2 (Erste Mahnung) / 3 (Letzte Mahnung)
 Mahngebühr als zusätzliche Position (optional, in Satzung zu verankern)
 Zahlungsfrist: kürzer als Original (z.B. 7 Tage)
 Hinweis auf Vereinsausschluss bei Mahnstufe 3 (wenn in Satzung vorgesehen)


⚠️ Achtung: Mahnung ≠ Rechnung im steuerlichen Sinne (§14 Abs. 1 S. 4 UStG). System muss unterscheiden.

C) Kursgebühr / Startgeldrechnung

 Empfänger: Mitglied oder Nicht-Mitglied
 Leistung: spezifischer Kurs / Turnier / Veranstaltung
 Steuer: §4 Nr. 22a UStG (wenn Zweckbetrieb), sonst 19%
 Verknüpfung zur Veranstaltung im System

D) Hallenmiete / Nutzungsgebühr (Externe)

 Empfänger: Dritter (Firma, anderer Verein, Privatperson)
 Steuer: 19% USt (wirtschaftlicher Geschäftsbetrieb)
 B2B: USt-IdNr. des Empfängers erfassen
 E-Rechnung: Pflicht bei B2B ab 2028 (Übergang bis 2027)

E) Sponsoring-/Werbungsrechnung

 Empfänger: Sponsor/Werbepartner (immer B2B)
 Leistung: Trikotwerbung, Bandenwerbung, Website, Veranstaltungssponsoring
 Steuer: 19% (wirtschaftlicher Geschäftsbetrieb, USt-pflichtig!)
 USt-IdNr. des Sponsors erfassen
 Laufzeit aus Sponsorenvertrag übernehmen
 E-Rechnung: ab 2025/2028 je nach Übergangsfrist

F) Aufwandsentschädigungs-Beleg (kein Rechnung im UStG-Sinne)

 Für §3 Nr. 26 EStG (Übungsleiter, max. €3.000/Jahr steuerfrei)
 Für §3 Nr. 26a EStG (Ehrenamt, max. €840/Jahr steuerfrei)
 Kein USt-Ausweis (keine Umsatzsteuerrechnung)
 Jahresgrenze pro Person im System verfolgen + Warnung bei >80%
 Dokumenttyp: „Quittung/Beleg" nicht „Rechnung"

G) Zuwendungsbestätigung / Spendenbescheinigung

 Kein Rechnung, aber ähnlicher Dokumenttyp
 Amtliches Muster (§10b EStG, BMF-Muster verwenden)
 Betrag, Datum, Zweck, Vereinsstatus (Freistellungsbescheid-Nr. + Datum)
 Eigene Nummerierung (getrennt von Rechnungsnummern)
 Aufbewahrungspflicht: Durchschlag/Kopie 10 Jahre


4.2 EINGEHENDE Rechnungen (Verein empfängt)
A) Trainerhonorar / Übungsleiterabrechnung

 Aussteller: freiberuflicher Trainer
 Steuerpflichtig: 19% wenn Trainer USt-pflichtig
 Pflicht ab 2025: E-Rechnung empfangsfähig sein (keine Übergangsfrist fürs Empfangen!)
 Kostenstelle: jeweilige Sparte
 Prüfpflicht: sind alle Pflichtangaben lt. §14 UStG vorhanden?

B) Hallenmiete / Sportstättenrechnung

 Aussteller: Gemeinde, privater Hallenbetreiber
 Steuer: oft 19% oder steuerfrei (Gemeinde)
 Kostenstelle: je Sparte oder Infrastruktur-Kostenstelle
 Dauerrechnung möglich (monatlich gleicher Betrag)

C) Sportartikel / Equipment

 Aussteller: Händler/Lieferant
 Steuer: 19%
 Kostenstelle: Sparte die Equipment erhält
 Lieferschein verknüpfen

D) Wartung / Reparatur Anlage

 Aussteller: Handwerksbetrieb, Fachbetrieb
 Steuer: 19%
 Ggf. Reverse Charge wenn EU-Ausland
 Kostenstelle: Infrastruktur

E) Software / IT-Dienstleistungen

 Aussteller: SaaS-Anbieter, IT-Dienstleister
 Steuer: 19% oder Reverse Charge (wenn EU-Ausland)
 E-Rechnung empfangen: ab 01.01.2025 keine Übergangsfrist


5. E-Rechnung — Regelungen ab 2025 (Wachstumschancengesetz)
5.1 Was gilt wann
ZeitraumAusstellenEmpfangenAb 01.01.2025Übergang: PDF/Papier noch erlaubtPflicht: E-Rechnung empfangen könnenBis 31.12.2026Papier oder PDF (mit Zustimmung Empfänger) erlaubtPflichtBis 31.12.2027Nur Vereine mit Vorjahresumsatz ≤ €800.000: PDF/Papier noch erlaubtPflichtAb 01.01.2028E-Rechnung Pflicht für alle B2B-UmsätzePflicht

Ausnahmen von E-Rechnungspflicht:

Rechnungen an Privatpersonen (B2C) → immer Papier/PDF möglich
Kleinbetragsrechnungen ≤ €250 brutto → immer Papier/PDF möglich
Nach §4 Nr. 8–29 UStG steuerbefreite Leistungen → kein E-Rechnungszwang (betrifft die meisten Vereinsleistungen!)
Beitragsrechnungen (ideeller Bereich) → kein E-Rechnungszwang


5.2 E-Rechnungsformate
FormatStandardAnwendungXRechnungXML-only, EN 16931Bevorzugt bei B2G (öffentliche Auftraggeber)ZUGFeRD 2.xHybrid: PDF + eingebettetes XMLEmpfohlen für B2B, menschenlesbar + maschinenlesbarFactur-X= ZUGFeRD, EU-BezeichnungSynonym
Features in der Software:

 E-Rechnung empfangen: E-Mail-Postfach-Integration, XML-Parser für ZUGFeRD/XRechnung
 E-Rechnung ausstellen: ZUGFeRD-Export (PDF + XML) für B2B-Rechnungen
 Format-Auswahl je Empfänger konfigurierbar
 Validierung gegen EN 16931 Schema vor Versand
 Fallback: PDF wenn Empfänger B2C oder steuerbefreite Leistung


6. Zahlungsfelder und -wege
6.1 Zahlungsinformationen auf der Rechnung
FeldPflicht (UStG)EmpfohlenHinweisZahlungsziel (Datum)Nein✅ Jaz.B. „fällig bis 24.03.2026"IBANNein✅ Jafür ÜberweisungBICNeinOptionalbei SEPA nicht mehr PflichtVerwendungszweckNein✅ Jakritisch für auto. ZuordnungSkonto-HinweisNeinOptional„2% Skonto bei Zahlung bis..."Mahngebühr-HinweisNeinOptionalnur bei Mahnungen
Felder in der Software:

 zahlungsziel_tage — konfigurierbar (default: 14 Tage), berechnet automatisch Fälligkeitsdatum
 zahlungsziel_datum — automatisch aus rechnungsdatum + zahlungsziel_tage
 iban — aus Vereinsstammdaten
 verwendungszweck — automatisch: RE-{rechnungsnummer} / {empfaenger_nachname}
 skonto_prozent, skonto_frist_tage — optional
 zahlungshinweis_text — Freitextfeld für individuelle Hinweise

6.2 Zahlungswege die das System abbilden muss
WegTypRichtungAutomatisierungsgradSEPA-LastschriftPush (Verein zieht ein)Ausgehend✅ Vollautomatisch (mit HITL)ÜberweisungPull (Mitglied überweist)EingehendSemi (Zuordnung manuell/auto)BarzahlungDirektBeideManuell, Quittung erzeugenPayPal / StripeOnlineEingehendWebhook-Integration (Phase 6)EC-KarteDirektEingehendKassensystem-Anbindung (Phase 6)
Features in der Software:

 SEPA-Verknüpfung: Rechnung → SEPA-Lastschrift-Position
 Zahlungseingang manuell buchen (Überweisung, Barzahlung)
 Automatische Zuordnung über Verwendungszweck (IBAN + RE-Nummer)
 Offene Posten: Differenz zwischen Rechnungsbetrag und Zahlungseingang
 Teilzahlung: Buchung von Teilbeträgen möglich


7. Rechnungsstatus-Workflow
Jede Rechnung muss durch einen definierten Status-Workflow laufen:
ENTWURF → GESTELLT → FÄLLIG → GEMAHNT (1/2/3) → BEZAHLT / ABGESCHRIEBEN
                              ↓
                         STORNIERT
Status-Definitionen:
StatusBedeutungMögliche FolgeaktionenENTWURFErstellt, noch nicht versendetBearbeiten, Löschen, StellenGESTELLTVersendet, Zahlungsziel läuftZahlung verbuchen, StornierenFAELLIGZahlungsziel überschrittenMahnung auslösen, Zahlung verbuchenMAHNUNG_1Erste ZahlungserinnerungZahlung verbuchen, Stufe erhöhenMAHNUNG_2Erste echte MahnungZahlung verbuchen, Stufe erhöhenMAHNUNG_3Letzte Mahnung, ggf. InkassoVorstand benachrichtigenBEZAHLTVollständig beglichenKeine (Abschluss)TEILBEZAHLTTeilzahlung eingegangenRestbetrag verfolgenSTORNIERTRechnung annulliertStornorechnung erzeugenABGESCHRIEBENForderung aufgegebenBuchung als Aufwand
Features in der Software:

 status — enum, alle oben genannten Werte
 Automatischer Wechsel GESTELLT → FAELLIG nach Fälligkeitsdatum
 Mahnwesen-Agent: automatisch Status erhöhen nach konfigurierbaren Fristen
 Stornorechnung: bei Stornierung automatisch Gegenbuchung + neue RE-Nr.
 Abschreibung: als Aufwandsbuchung in SKR42 verbuchen


8. Storno und Korrekturen
SzenarioLösungRE-NummerBetrag falschStorno + neue RechnungOriginal + Stornorechnung + neue REEmpfänger falschStorno + neue RechnungidemSteuersatz falschStorno + neue RechnungidemKleine Korrektur (Tippfehler)Nur wenn Pflichtangabe betroffen: Stornosonst: Anmerkung
Stornorechnung-Pflichtinhalt:

 Bezug auf Original-Rechnungsnummer
 Alle Beträge negativ (Umkehrung)
 Eigene Stornobelegnummer: STORNO-{original-nr}
 Datum der Stornierung
 Kein nachträgliches Überschreiben von gestellten Rechnungen (GoBD: Unveränderlichkeit)


9. Aufbewahrungsfristen (§147 AO, GoBD)
DokumenttypFristBeginnRechtsgrundlageRechnungen (eingehend + ausgehend)10 JahreEnde des Ausstellungsjahres§147 Abs. 1 Nr. 4 AOBuchungsbelege (alle)10 JahreEnde des Buchungsjahres§147 Abs. 1 Nr. 4 AOJahresabschlüsse / EÜR10 JahreEnde des Aufstellungsjahres§147 Abs. 1 Nr. 1 AOHandels-/Geschäftsbriefe6 JahreEnde des Entstehungsjahres§147 Abs. 1 Nr. 2 AOSpendenbescheinigungen (Kopie)10 Jahre—§63 Abs. 3 AOMittelverwendungsnachweise10 Jahre—§63 AO (Gemeinnützigkeit)

⚠️ Praxisempfehlung: Alles 10 Jahre aufbewahren — erspart die Sortierarbeit.
⚠️ Tipp für Steuerprüfung: Bei fehlenden Belegen darf das Finanzamt schätzen. Sportvereine riskieren dann, die Zweckbetriebs-Umsatzgrenze von €45.000/Jahr zu überschreiten → Gemeinnützigkeit gefährdet.

Features in der Software:

 loeschdatum — automatisch berechnet: rechnungsdatum + 10 Jahre + 1 Tag
 Löschsperre: Rechnungen können nicht vor Ablauf der Frist gelöscht werden
 GoBD-konforme Archivierung: Dokumente unveränderbar nach Stellung
 Revisionssicheres Audit-Log: wer hat was wann erstellt/geändert/versendet
 Jahresüberprüfung: Monitor-Agent prüft monatlich welche Dokumente vernichtet werden dürfen
 Export-Funktion: alle Rechnungen eines Jahres als ZIP für Steuerberater/Finanzamt


10. Datenbankfelder — vollständige Feldliste
Tabelle rechnungen
sql-- Identifikation
id                    UUID PRIMARY KEY
rechnungsnummer       VARCHAR(30) UNIQUE NOT NULL  -- z.B. "2026-IB-0147"
rechnungstyp          ENUM(MITGLIEDSBEITRAG, KURSGEBUEHR, HALLENMIETE,
                           SPONSORING, SONSTIGE, STORNO, MAHNUNG)

-- Status
status                ENUM(ENTWURF, GESTELLT, FAELLIG, MAHNUNG_1,
                           MAHNUNG_2, MAHNUNG_3, BEZAHLT, TEILBEZAHLT,
                           STORNIERT, ABGESCHRIEBEN)
mahnstufe             INTEGER DEFAULT 0  -- 0-3

-- Aussteller (Verein)
verein_id             UUID FK → vereine
-- Empfänger
empfaenger_typ        ENUM(MITGLIED, SPONSOR, EXTERN, ANONYM)
mitglied_id           UUID FK → mitglieder NULLABLE
empfaenger_name       VARCHAR(200)
empfaenger_strasse    VARCHAR(200)
empfaenger_plz        VARCHAR(10)
empfaenger_ort        VARCHAR(100)
empfaenger_ust_id     VARCHAR(20) NULLABLE

-- Datumsfelder
rechnungsdatum        DATE NOT NULL
leistungsdatum        DATE NULLABLE
leistungszeitraum_von DATE NULLABLE
leistungszeitraum_bis DATE NULLABLE
faelligkeitsdatum     DATE  -- automatisch berechnet
loeschdatum           DATE  -- automatisch: rechnungsdatum + 10 Jahre

-- Beträge
summe_netto           DECIMAL(10,2)
summe_steuer          DECIMAL(10,2)
summe_brutto          DECIMAL(10,2)
anzahlung_betrag      DECIMAL(10,2) DEFAULT 0
restbetrag            DECIMAL(10,2)  -- automatisch berechnet
bezahlt_betrag        DECIMAL(10,2) DEFAULT 0
offener_betrag        DECIMAL(10,2)  -- automatisch: summe_brutto - bezahlt_betrag

-- Steuer / Sphäre
sphaere               ENUM(IDEELL, ZWECKBETRIEB, VERMOEGEN, WIRTSCHAFT)
steuerhinweis_text    TEXT NULLABLE

-- Zahlung
iban                  VARCHAR(34)
verwendungszweck      VARCHAR(140)
zahlungsziel_tage     INTEGER DEFAULT 14
skonto_prozent        DECIMAL(4,2) NULLABLE
skonto_frist_tage     INTEGER NULLABLE

-- E-Rechnung
format                ENUM(PDF, ZUGFERD, XRECHNUNG)
e_rechnung_xml        TEXT NULLABLE  -- eingebettetes XML

-- Referenzen
storno_von_id         UUID FK → rechnungen NULLABLE  -- bei Stornorechnung
original_re_nr        VARCHAR(30) NULLABLE
sepa_mandat_id        UUID FK → sepa_mandate NULLABLE
buchungs_id           UUID FK → buchungen NULLABLE

-- Metadaten
erstellt_von          UUID FK → nutzer
erstellt_am           TIMESTAMPTZ
geaendert_von         UUID FK → nutzer
geaendert_am          TIMESTAMPTZ
gestellt_am           TIMESTAMPTZ NULLABLE
bezahlt_am            TIMESTAMPTZ NULLABLE
Tabelle rechnungspositionen
sqlid                    UUID PRIMARY KEY
rechnung_id           UUID FK → rechnungen
position_nr           INTEGER  -- Reihenfolge

beschreibung          TEXT NOT NULL
menge                 DECIMAL(10,3) NOT NULL
einheit               VARCHAR(20)  -- "×", "h", "Monat", "Stück"
einzelpreis_netto     DECIMAL(10,2) NOT NULL
steuersatz            DECIMAL(5,2) NOT NULL  -- 0.00, 7.00, 19.00
steuerbefreiungsgrund VARCHAR(100) NULLABLE  -- "§4 Nr. 22b UStG"
gesamtpreis_netto     DECIMAL(10,2)  -- berechnet: menge × einzelpreis
gesamtpreis_steuer    DECIMAL(10,2)  -- berechnet
gesamtpreis_brutto    DECIMAL(10,2)  -- berechnet

-- Verknüpfungen
beitragskategorie_id  UUID FK → beitragskategorien NULLABLE
veranstaltung_id      UUID FK → veranstaltungen NULLABLE
kostenstelle_id       UUID FK → kostenstellen NULLABLE
Tabelle zahlungseingaenge
sqlid                    UUID PRIMARY KEY
rechnung_id           UUID FK → rechnungen
betrag                DECIMAL(10,2) NOT NULL
zahlungsdatum         DATE NOT NULL
zahlungsweg           ENUM(SEPA, UEBERWEISUNG, BAR, PAYPAL, SONSTIGE)
verwendungszweck      VARCHAR(140)
bankbuchungs_id       VARCHAR(50) NULLABLE  -- Referenz aus Kontoauszug
notiz                 TEXT NULLABLE

11. Rechnungsvorlagen (Templates)
Das System muss vorgefertigte Templates für die häufigsten Rechnungstypen anbieten:

 Template: Quartalsbeitrag — Grundbeitrag + Spartenbeitrag(e), §4 Nr. 22b UStG
 Template: Jahresbeitrag — wie Quartal, aber Leistungszeitraum = Kalenderjahr
 Template: Kursgebühr — Einzelkurs oder Kursreihe, Zweckbetrieb
 Template: Hallenmiete extern — 19% USt, B2B-Felder
 Template: Sponsoringrechnung — 19% USt, Werbeleistung beschreiben
 Template: Mahnvorlage Stufe 1 — freundliche Erinnerung
 Template: Mahnvorlage Stufe 2 — formelle Mahnung mit Frist
 Template: Mahnvorlage Stufe 3 — letzte Mahnung, Androhung Konsequenzen
 Template: Stornorechnung — automatisch aus Original befüllt

Jedes Template enthält:

 Vorausgefüllte Leistungsbeschreibung
 Vorausgewählte Sphäre + Steuersatz
 Vorausgefüllter Steuerhinweistext
 Konfigurierbare Zahlungsfrist


12. Versand-Kanäle
KanalWannAnforderungE-Mail (PDF-Anhang)Standard, B2CEinwilligung des Empfängers (§14 Abs. 1 UStG: Zustimmung zu elektr. Format)E-Mail (ZUGFeRD)B2B ab 2025Zustimmung des Empfängers bis 2027PostversandAuf Anfrage, ältere MitgliederImmer ohne Zustimmung möglichDownload-LinkSelf-Service-PortalMitglied ruft eigene Rechnungen abMCP-Tool-AufrufÜber KI-Agentrechnung_erstellen + rechnung_versenden
Features in der Software:

 versand_kanal — ENUM: EMAIL_PDF / EMAIL_ZUGFERD / POST / PORTAL / MANUELL
 Versandprotokoll: wann, an welche E-Mail-Adresse, welches Format
 Unzustellbarkeit-Behandlung: Bounce → Alert an Vorstand
 Einwilligungsstatus: hat Mitglied elektronischen Versand zugestimmt (DSGVO + UStG)
 Massenversand: bis 500 Rechnungen in einem Lauf, Rate-Limiting


13. Schnittstellen und Integrationen
SystemRichtungDatenflussSEPA-Lastschrift (pain.008)AusgehendRechnungen → SEPA-DateiDATEVExportBuchungen + Rechnungen → SteuerberaterE-Mail-Server (SMTP)AusgehendRechnungs-PDF/ZUGFeRDKontoauszug-Import (MT940/CAMT)EingehendZahlungseingänge auto. zuordnenDokumenten-Storage (S3/MinIO)InternPDF-ArchivierungMCP-ServerBidirektionalKI-Agent-Zugriff auf alle Rechnungs-Tools

14. MCP-Tools für Rechnungen (Vollständige Liste)
ToolBeschreibungHITLSphärerechnung_erstellenNeue Rechnung aus Template oder manuellNeinallerechnung_detailsEinzelne Rechnung abrufenNein—rechnungen_suchenSuche nach Empfänger, Status, Zeitraum, SphäreNein—rechnung_stellenStatus ENTWURF → GESTELLT, Versand auslösenJa—rechnung_stornierenStornorechnung erzeugenJa—zahlung_verbuchenZahlungseingang einer Rechnung zuordnenNein—mahnung_erstellenNächste Mahnstufe für überfällige RechnungJa—rechnung_pdf_generierenPDF-Dokument erzeugen (ohne zu versenden)Nein—rechnungen_exportAlle Rechnungen eines Zeitraums als ZIPNein—offene_posten_uebersichtAlle unbezahlten Rechnungen mit AgingNein—sepa_xml_aus_rechnungenSEPA-Lastschrift aus fälligen RechnungenJa—spendenbescheinigung_erstellenZuwendungsbestätigung (kein UStG-Rechnung)NeinIdeell

15. Offene Rechtsfragen / Edge Cases
Die folgenden Punkte erfordern Beratung durch Steuerberater und sollten im System mit expliziten Warnungen versehen sein:

 Gemischte Rechnung (z.B. Beitrag + Hallenmiete in einer RE): mehrere Steuersätze, komplexe Aufteilung → Warnung im UI
 Familienrechnung: ein Dokument für mehrere Mitglieder → Rechnungsnummern-Zuordnung klären
 Auslandsrechnung (Mitglied wohnt in Österreich): Grenzfälle §3a UStG
 Reverse Charge (EU-Dienstleister, z.B. Softwareanbieter): System muss bei eingehenden Rechnungen warnen
 Kleinunternehmerregelung (§19 UStG): wenn Verein unter €22.000 Jahresumsatz — andere Rechnungshinweise
 Vorsteuerabzug: nur im wirtschaftlichen Geschäftsbetrieb möglich — System muss Vorsteuerbuchungen auf die richtige Sphäre beschränken
 Veranstaltungsrechnung an Nicht-Mitglieder: könnte Umsatzsteuerpflicht auslösen (Zweckbetrieb verlassen)


16. Checkliste Mindestanforderungen MVP
Bevor die Rechnungsfunktion als produktionsreif gilt, müssen alle diese Punkte implementiert sein:
Pflichtfelder:

 Alle 10 §14 UStG-Pflichtangaben vorhanden und validiert
 Automatische Rechnungsnummernvergabe ohne Lücken
 Steuerbefreiungshinweis bei 0%-Sätzen
 Sphärenzuordnung je Rechnung

Unveränderlichkeit:

 Gestellte Rechnungen können nicht mehr bearbeitet werden (GoBD)
 Korrekturen nur über Stornorechnung
 Audit-Log für alle Statusänderungen

E-Rechnung:

 E-Rechnungsempfang technisch möglich (XML-Parser)
 ZUGFeRD-Export für B2B-Rechnungen

Aufbewahrung:

 Löschsperre für 10-Jahres-Frist
 PDF-Archiv unveränderlich (revisionssicher)

SEPA-Verknüpfung:

 Mitgliedsbeitragsrechnungen → SEPA-Lastschrift-Datei generierbar


rechnung_facts.md v1.0 · Erstellt März 2026 · Rechtsstand: §14 UStG i.d.F. JStG 2024, BMF-Schreiben 15.10.2024
Kein Ersatz für steuerrechtliche Beratung. Bei Unklarheiten: Steuerberater hinzuziehen.