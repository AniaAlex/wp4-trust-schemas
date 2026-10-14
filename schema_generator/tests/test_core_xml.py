"""Clause-by-clause tests of the generated core XML binding (core/generated/lote_core.xsd + lote_core.sch)
against ETSI TS 119 602 V1.1.1. A case passes when the verdict of XSD + Schematron together matches the text.

"""
import pathlib, sys
import pytest
import xmlschema
from lxml import etree, isoschematron

from lote_schema_generator.paths import ROOT as _ROOT, HANDWRITTEN_CORE, HANDWRITTEN_PROFILES  # noqa: F401
ROOT = pathlib.Path(_ROOT)
GEN = ROOT / "core" / "generated"
XSD = xmlschema.XMLSchema(str(GEN / "lote_core.xsd"))
SCH = isoschematron.Schematron(etree.parse(str(GEN / "lote_core.sch")))
NS = "http://uri.etsi.org/019602/v1#"
CERT = "MIIBszCCAVmgAwIBAgIUQQ=="

ADDR = ('<PostalAddresses><PostalAddress xml:lang="en"><StreetAddress>Rue de la Loi 200</StreetAddress>{loc}'
        '<Country>{cc}</Country></PostalAddress></PostalAddresses>')
EADDR = '<URI xml:lang="en">mailto:helpdesk@example.eu</URI><URI xml:lang="en">https://example.eu</URI>'
EXPLICIT = '''<LoTEType>http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList</LoTEType>
<SchemeOperatorName><Name xml:lang="en">{opname}</Name></SchemeOperatorName>
<SchemeOperatorAddress>{addr}<ElectronicAddress>{eaddr}</ElectronicAddress></SchemeOperatorAddress>
<SchemeName><Name xml:lang="en">EU:PID providers list</Name></SchemeName>
<SchemeInformationURI><URI xml:lang="en">https://example.eu/pid</URI></SchemeInformationURI>
<StatusDeterminationApproach>http://uri.etsi.org/19602/PIDProvidersList/StatusDetn/EU</StatusDeterminationApproach>
<SchemeTypeCommunityRules><URI xml:lang="en">http://uri.etsi.org/19602/PIDProviders/schemerules/EU</URI></SchemeTypeCommunityRules>
<SchemeTerritory>{territory}</SchemeTerritory>
<PolicyOrLegalNotice>{policy}</PolicyOrLegalNotice>'''


def doc(head="", lsi_extra="", dt="2026-01-01T00:00:00Z", nextupdate="<dateTime>2026-06-01T00:00:00Z</dateTime>",
        explicit=True, te="", tag=' LoTETag="http://uri.etsi.org/19602/LoTETag"', addr=None, eaddr=EADDR, territory="EU",
        policy='<LoTEPolicy xml:lang="en">https://example.eu/policy</LoTEPolicy>', opname="European Commission", tail=""):
    a = addr if addr is not None else ADDR.format(loc="<Locality>Brussels</Locality>", cc="BE")
    exp = EXPLICIT.format(addr=a, eaddr=eaddr, territory=territory, policy=policy, opname=opname) if explicit else \
        f'<SchemeOperatorName><Name xml:lang="en">{opname}</Name></SchemeOperatorName>'
    lsi = (f'<LoTEVersionIdentifier>1</LoTEVersionIdentifier><LoTESequenceNumber>1</LoTESequenceNumber>{head}{exp}{lsi_extra}'
           f'<ListIssueDateTime>{dt}</ListIssueDateTime><NextUpdate>{nextupdate}</NextUpdate>{tail}')
    return f'<ListOfTrustedEntities xmlns="{NS}"{tag}><ListAndSchemeInformation>{lsi}</ListAndSchemeInformation>{te}</ListOfTrustedEntities>'


def entity(sdi=f"<DigitalId><X509Certificate>{CERT}</X509Certificate></DigitalId>", status="", history="", te_ext="", svc_ext=""):
    return (f'<TrustedEntitiesList><TrustedEntity><TrustedEntityInformation><TEName><Name xml:lang="en">Provider</Name></TEName>'
            f'<TEAddress><TEPostalAddress><PostalAddress xml:lang="en"><StreetAddress>Main 1</StreetAddress><Country>DE</Country>'
            f'</PostalAddress></TEPostalAddress><TEElectronicAddress>{EADDR}</TEElectronicAddress></TEAddress>'
            f'<TEInformationURI><URI xml:lang="en">https://provider.example</URI></TEInformationURI>{te_ext}'
            f'</TrustedEntityInformation><TrustedEntityServices><TrustedEntityService><ServiceInformation>'
            f'<ServiceName><Name xml:lang="en">Issuance</Name></ServiceName><ServiceDigitalIdentity>{sdi}</ServiceDigitalIdentity>'
            f'{status}{svc_ext}</ServiceInformation>{history}</TrustedEntityService></TrustedEntityServices></TrustedEntity></TrustedEntitiesList>')


# The extension elements (OtherAssociatedBodies, AssociatedBody, ServiceUniqueIdentifier) are in their extension
# namespace; the components of AssociatedBodyType are core components, so they are in the core namespace.
TIE = "http://uri.etsi.org/019602/v1/TrustedEntityExtensions"
SIE = "http://uri.etsi.org/019602/v1/ServiceInformationExtensions"
ASSOC = (f'<TEInformationExtensions><Extension><tie:OtherAssociatedBodies xmlns:tie="{TIE}"><tie:AssociatedBody>'
         '<AssociatedBodyName><Name xml:lang="en">Body</Name></AssociatedBodyName>'
         '</tie:AssociatedBody></tie:OtherAssociatedBodies></Extension></TEInformationExtensions>')
ASSOC_NONAME = (f'<TEInformationExtensions><Extension><tie:OtherAssociatedBodies xmlns:tie="{TIE}"><tie:AssociatedBody>'
                '<AssociatedBodyTypeIdentifier>http://x.eu/t</AssociatedBodyTypeIdentifier>'
                '</tie:AssociatedBody></tie:OtherAssociatedBodies></Extension></TEInformationExtensions>')
SUI = (f'<ServiceInformationExtensions><Extension><sie:ServiceUniqueIdentifier xmlns:sie="{SIE}">urn:example:wallet:42'
       '</sie:ServiceUniqueIdentifier></Extension></ServiceInformationExtensions>')
HIST = ('<ServiceHistory><ServiceHistoryInstance><ServiceName><Name xml:lang="en">Issuance</Name></ServiceName>'
        '<ServiceDigitalIdentity><DigitalId><X509SKI>q1w2e3r4</X509SKI></DigitalId></ServiceDigitalIdentity>'
        '<ServiceStatus>http://x.eu/withdrawn</ServiceStatus><StatusStartingTime>2025-01-01T00:00:00Z</StatusStartingTime>'
        '</ServiceHistoryInstance></ServiceHistory>')
STATUS = '<ServiceStatus>http://x.eu/granted</ServiceStatus>'
PTR = ('<PointersToOtherLoTE><OtherLoTEPointer>{sdi}<LoTELocation>https://example.eu/lote.xml</LoTELocation>{q}'
       '</OtherLoTEPointer></PointersToOtherLoTE>')                 # Forge order: identities before the location
QUAL = ('<LoTEQualifiers><LoTEQualifier><LoTEType>http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList</LoTEType>'
        '<SchemeOperatorName><Name xml:lang="en">EC</Name></SchemeOperatorName><SchemeTerritory>EU</SchemeTerritory>'
        '<MimeType>{mime}</MimeType></LoTEQualifier></LoTEQualifiers>')
PSDI = f'<ServiceDigitalIdentities><ServiceDigitalIdentity><DigitalId><X509Certificate>{CERT}</X509Certificate></DigitalId></ServiceDigitalIdentity></ServiceDigitalIdentities>'

CASES = [
    # (clause, label, expected, document)
    ("5", "explicit list with entity, service and both extensions", "valid", doc(te=entity(te_ext=ASSOC, svc_ext=SUI))),
    ("6.3.0", "minimal implicit list (Table 1)", "valid", doc(explicit=False)),
    ("6.3.15", "closed list: empty NextUpdate", "valid", doc(nextupdate="")),
    ("6.3.5.1", "postal address without Locality", "valid", doc(addr=ADDR.format(loc="", cc="BE"))),
    ("6.1.5 b", "regional SchemeTerritory 'ASIA'", "valid", doc(territory="ASIA")),
    ("6.3.11", "legal notice text instead of policy", "valid", doc(policy='<LoTELegalNotice xml:lang="en">Notice</LoTELegalNotice>')),
    ("6.6.0", "history kept and every service has a status", "valid",
     doc(head="", lsi_extra="<HistoricalInformationPeriod>65535</HistoricalInformationPeriod>", te=entity(status=STATUS, history=HIST))),
    ("6.3.13", "pointer with identity and qualifiers", "valid", doc(lsi_extra=PTR.format(sdi=PSDI, q=QUAL.format(mime="application/xml")))),
    ("6.2", "missing LoTETag", "invalid", doc(tag="")),
    ("6.3.0", "explicit list without SchemeTerritory", "invalid", doc().replace("<SchemeTerritory>EU</SchemeTerritory>", "")),
    ("6.3.0", "implicit list carrying SchemeName", "invalid",
     doc(explicit=False, lsi_extra='<SchemeName><Name xml:lang="en">EU:X</Name></SchemeName>')),
    ("6.1.3", "date-time with fraction and offset", "invalid", doc(dt="2026-01-01T10:00:00.5+02:00")),
    ("6.1.3", "date-time without time zone", "invalid", doc(dt="2026-01-01T10:00:00")),
    ("6.1.5", "SchemeTerritory 'x1'", "invalid", doc(territory="x1")),
    ("6.1.5 a", "SchemeTerritory 'GB'", "invalid", doc(territory="GB")),
    ("6.1.5 a", "postal Country 'GB'", "invalid", doc(addr=ADDR.format(loc="", cc="GB"))),
    ("6.3.5.1", "postal country element named CountryName", "invalid",
     doc(addr=ADDR.format(loc="", cc="BE").replace("<Country>", "<CountryName>").replace("</Country>", "</CountryName>"))),
    ("6.1.4", "upper-case language tag 'EN'", "invalid", doc().replace('<Name xml:lang="en">European', '<Name xml:lang="EN">European')),
    ("6.1.4", "no English entry", "invalid", doc().replace('<Name xml:lang="en">European Commission', '<Name xml:lang="fr">Commission')),
    ("B.2", "line feed inside a name", "invalid", doc(opname="European\nCommission")),
    ("6.3.5.2", "electronic address without mailto:", "invalid",
     doc(eaddr='<URI xml:lang="en">tel:+3222991111</URI><URI xml:lang="en">https://example.eu</URI>')),
    ("6.6.3.0", "empty ServiceDigitalIdentity", "invalid", doc(te=entity(sdi=""))),
    ("6.6.3.0", "empty DigitalId", "invalid", doc(te=entity(sdi="<DigitalId/>"))),
    ("6.6.3.1", "certificate not Base64", "invalid", doc(te=entity(sdi="<DigitalId><X509Certificate>%%%</X509Certificate></DigitalId>"))),
    ("6.4.3", "empty ServiceHistory", "invalid", doc(te=entity(history="<ServiceHistory/>"))),
    ("6.3.13", "pointer without identity and qualifiers", "invalid", doc(lsi_extra=PTR.format(sdi="", q=""))),
    ("6.3.13", "qualifier with a malformed MIME type", "invalid", doc(lsi_extra=PTR.format(sdi=PSDI, q=QUAL.format(mime="xml")))),
    ("6.6.0", "history kept but a service without status", "invalid",
     doc(lsi_extra="<HistoricalInformationPeriod>65535</HistoricalInformationPeriod>", te=entity())),
    ("6.3.17", "scheme extension without criticality", "invalid", doc(tail="<SchemeExtensions><Extension>x</Extension></SchemeExtensions>")),
    ("6.5.5.1.1", "associated body without a name (extension content checked)", "invalid", doc(te=entity(te_ext=ASSOC_NONAME))),
]


def verdict(xml):
    errs = []
    try:
        XSD.validate(xml)
    except xmlschema.XMLSchemaValidationError as e:
        errs.append(("XSD", str(e.reason)[:90]))
    except Exception as e:                                     # malformed XML etc.
        errs.append(("XML", str(e).splitlines()[0][:90]))
    else:
        if not SCH.validate(etree.fromstring(xml.encode())):
            msg = SCH.error_log.last_error.message if SCH.error_log else ""
            errs.append(("Schematron", msg[:90]))
    return errs



@pytest.mark.parametrize("clause,label,expected,xml", CASES, ids=[f"{c[0]} {c[1]}" for c in CASES])
def test_case(clause, label, expected, xml):
    errs = verdict(xml)
    got = "invalid" if errs else "valid"
    assert got == expected, f"[{clause}] {label}: expected {expected}, got {got}" + (f" [{errs[0][0]}: {errs[0][1]}]" if errs else "")
