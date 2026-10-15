"""Tests of the generated XML profiles (Annexes D-I): explicit/generated/base/lote_core.xsd + lote_core.sch + the profile's .sch.
The cases mirror test_profiles.py (JSON) so both bindings are held to the same requirements, plus the 6-month NextUpdate
cases, which only Schematron can check.

"""
import pathlib, sys
import pytest
import xmlschema
from lxml import etree, isoschematron

from lote_schema_generator.paths import ROOT as _ROOT, HANDWRITTEN_CORE, HANDWRITTEN_PROFILES  # noqa: F401
ROOT = pathlib.Path(_ROOT)
GEN = ROOT / "explicit" / "generated"                  # the profiles build on the explicit track (x.1)
XSD = xmlschema.XMLSchema(str(GEN / "base" / "lote_core.xsd"))
CORE_SCH = isoschematron.Schematron(etree.parse(str(GEN / "base" / "lote_core.sch")))
NS, E = "http://uri.etsi.org/019602/v1#", "http://uri.etsi.org/19602/"
SIE = "http://uri.etsi.org/019602/v1/ServiceInformationExtensions"
CERT = "MIIBszCCAVmgAwIBAgIUQQ=="
DS = "http://www.w3.org/2000/09/xmldsig#"
SIG = (f'<ds:Signature xmlns:ds="{DS}"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
       '<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/><ds:Reference URI=""><ds:Transforms>'
       '<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
       '<ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/></ds:Transforms>'
       '<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>AAAA</ds:DigestValue></ds:Reference>'
       '</ds:SignedInfo><ds:SignatureValue>AAAA</ds:SignatureValue></ds:Signature>')   # structure only; not a real signature

P = {  # annex: (profile file stem, LoTEType, status determination approach, scheme rules, TE uri segment, service prefix)
    "D": ("D_pid_providers", "EUPIDProvidersList", "PIDProvidersList/StatusDetn/EU", "PIDProviders/schemerules/EU", "PIDProvider", "PID"),
    "E": ("E_wallet_providers", "EUWalletProvidersList", "WalletProvidersList/StatusDetn/EU", "WalletProvidersList/schemerules/EU", "WalletProvider", "WalletSolution"),
    "F": ("F_wrpac_providers", "EUWRPACProvidersList", "WRPACProvidersList/StatusDetn/EU", "WRPACProvidersList/schemerules/EU", "WRPACProvider", "WRPAC"),
    "G": ("G_wrprc_providers", "EUWRPRCProvidersList", "WRPRCrovidersList/StatusDetn/EU", "WRPRCProvidersList/schemerules/EU", "WRPRCProvider", "WRPRC"),
    "H": ("H_pub_eaa_providers", "EUPubEAAProvidersList", "PubEAAProvidersList/StatusDetn/EU", "PubEAAProvidersList/schemerules/EU", "PubEAAProvider", "PubEAA"),
    "I": ("I_registrars_and_registers", "EURegistrarsAndRegistersList", "RegistrarsAndRegistersList/StatusDetn/EU", "RegistrarsAndRegistersList/schemerules/EU", "Registrar", None),
}
SCH = {a: isoschematron.Schematron(etree.parse(str(GEN / "profiles" / f"lote_profile_{p[0]}.sch"))) for a, p in P.items()}

name = lambda v: f'<Name xml:lang="en">{v}</Name>'
uris = lambda *us: "".join(f'<URI xml:lang="en">{u}</URI>' for u in us)
ADDR = '<PostalAddress xml:lang="en"><StreetAddress>Rue de la Loi 200</StreetAddress><Locality>Brussels</Locality><Country>BE</Country></PostalAddress>'


def parts(a):
    """The example list of Annex a as named parts, in schema order; tests change single parts."""
    _, lt, sda, rules, teu, svc = P[a]
    p = {
        "version": "1", "lotetype": E + "LoTEType/" + lt, "sda": E + sda, "rules": E + rules, "territory": "EU",
        "hip": "", "pointers": (f'<PointersToOtherLoTE><OtherLoTEPointer>'
                                f'<ServiceDigitalIdentities><ServiceDigitalIdentity><DigitalId><X509Certificate>{CERT}</X509Certificate>'
                                f'</DigitalId></ServiceDigitalIdentity></ServiceDigitalIdentities>'
                                f'<LoTELocation>https://ec.europa.eu/lote.xml</LoTELocation><LoTEQualifiers><LoTEQualifier>'
                                f'<LoTEType>{E}LoTEType/{lt}</LoTEType><SchemeOperatorName>{name("EC")}</SchemeOperatorName>'
                                f'<SchemeTerritory>EU</SchemeTerritory><MimeType>application/xml</MimeType></LoTEQualifier>'
                                f'</LoTEQualifiers></OtherLoTEPointer></PointersToOtherLoTE>'),
        "explicit": True, "tradename": "",
        "elec": uris("mailto:c@p.be", "https://p.be", "tel:+3221234567"),
        "teinfo": uris("https://p.be/terms", f"{E}ListOfTrustedEntities/{teu}/BE"),
        "svctype": E + (f"SvcType/{svc}/Issuance" if svc else "SvcType/Register"),
        "sdi": f"<DigitalId><X509Certificate>{CERT}</X509Certificate></DigitalId>",
        "status": "", "start": "", "supply": "", "ext": "", "history": "", "sig": "",
        "issue": "2025-11-01T10:00:00Z", "next": "<NextUpdate><dateTime>2026-05-01T10:00:00Z</dateTime></NextUpdate>",
    }
    if a == "H":
        p.update(hip="<HistoricalInformationPeriod>65535</HistoricalInformationPeriod>", pointers="", sig=SIG,
                 tradename=f"<TETradeName>{name('OJ:BE:2020-123')}</TETradeName>",
                 elec=p["elec"] + uris(f"{E}ListOfTrustedEntities/{teu}/BE"), teinfo=uris("https://p.be/terms"),
                 status=f"<ServiceStatus>{E}PubEAAProvidersList/SvcStatus/notified</ServiceStatus>",
                 start="<StatusStartingTime>2025-11-01T10:00:00Z</StatusStartingTime>")
    if a == "E":
        p["ext"] = (f'<ServiceInformationExtensions><Extension><sie:ServiceUniqueIdentifier xmlns:sie="{SIE}">urn:eu:wallet:ref:123'
                    f'</sie:ServiceUniqueIdentifier></Extension></ServiceInformationExtensions>')
    if a == "I":
        p["supply"] = "<ServiceSupplyPoints><ServiceSupplyPoint>https://registry.be/api</ServiceSupplyPoint></ServiceSupplyPoints>"
    return p


def xml(p):
    scheme = (f'<LoTEType>{p["lotetype"]}</LoTEType><SchemeOperatorName>{name("European Commission")}</SchemeOperatorName>'
              f'<SchemeOperatorAddress><PostalAddresses>{ADDR}</PostalAddresses><ElectronicAddress>'
              f'{uris("mailto:x@ec.europa.eu", "https://ec.europa.eu")}</ElectronicAddress></SchemeOperatorAddress>'
              f'<SchemeName>{name("EU:list")}</SchemeName><SchemeInformationURI>{uris("https://ec.europa.eu/info", "https://ec.europa.eu/history")}'
              f'</SchemeInformationURI><StatusDeterminationApproach>{p["sda"]}</StatusDeterminationApproach>'
              f'<SchemeTypeCommunityRules>{uris(p["rules"])}</SchemeTypeCommunityRules><SchemeTerritory>{p["territory"]}</SchemeTerritory>'
              f'<PolicyOrLegalNotice><LoTEPolicy xml:lang="en">https://ec.europa.eu/policy</LoTEPolicy></PolicyOrLegalNotice>') \
        if p["explicit"] else f'<SchemeOperatorName>{name("European Commission")}</SchemeOperatorName>'
    return (f'<ListOfTrustedEntities xmlns="{NS}" LoTETag="http://uri.etsi.org/19602/LoTETag"><ListAndSchemeInformation>'
            f'<LoTEVersionIdentifier>{p["version"]}</LoTEVersionIdentifier><LoTESequenceNumber>1</LoTESequenceNumber>{scheme}'
            f'{p["hip"]}{p["pointers"]}<ListIssueDateTime>{p["issue"]}</ListIssueDateTime>'
            f'{p["next"]}</ListAndSchemeInformation>'
            f'<TrustedEntitiesList><TrustedEntity><TrustedEntityInformation><TEName>{name("Provider BE")}</TEName>{p["tradename"]}'
            f'<TEAddress><TEPostalAddress>{ADDR}</TEPostalAddress><TEElectronicAddress>{p["elec"]}</TEElectronicAddress></TEAddress>'
            f'<TEInformationURI>{p["teinfo"]}</TEInformationURI></TrustedEntityInformation><TrustedEntityServices><TrustedEntityService>'
            f'<ServiceInformation><ServiceTypeIdentifier>{p["svctype"]}</ServiceTypeIdentifier><ServiceName>{name("Service")}</ServiceName>'
            f'<ServiceDigitalIdentity>{p["sdi"]}</ServiceDigitalIdentity>{p["status"]}{p["start"]}{p["supply"]}{p["ext"]}'
            f'</ServiceInformation>{p["history"]}</TrustedEntityService></TrustedEntityServices></TrustedEntity></TrustedEntitiesList>'
            f'{p["sig"]}</ListOfTrustedEntities>')


def ms(p, code):                                           # replace the Member State code of the ETSI URI in TEInformationURI
    return p["teinfo"].replace("/BE</URI>", f"/{code}</URI>")


HIST = lambda sdi, status: (f'<ServiceHistory><ServiceHistoryInstance><ServiceName>{name("S")}</ServiceName>'
                            f'<ServiceDigitalIdentity>{sdi}</ServiceDigitalIdentity><ServiceStatus>{status}</ServiceStatus>'
                            f'<StatusStartingTime>2025-01-01T00:00:00Z</StatusStartingTime></ServiceHistoryInstance></ServiceHistory>')
SKI = "<DigitalId><X509SKI>AAEC</X509SKI></DigitalId>"
NOTIFIED = E + "PubEAAProvidersList/SvcStatus/notified"

COMMON = [
    ("version 2", {"version": "2"}),
    ("wrong LoTEType", {"lotetype": E + "LoTEType/EUPIDProvidersList_X"}),
    ("wrong StatusDeterminationApproach", {"sda": "http://example.eu/sda"}),
    ("wrong SchemeTypeCommunityRules", {"rules": "http://example.eu/rules"}),
    ("territory BE", {"territory": "BE"}),
    ("implicit scheme info", {"explicit": False}),
    ("wrong service type", {"svctype": E + "SvcType/Other"}),
    ("no phone in TE address", lambda p: {"elec": p["elec"].replace('<URI xml:lang="en">tel:+3221234567</URI>', "")}),
    ("NextUpdate 6 months + 1 s", {"next": "<NextUpdate><dateTime>2026-05-01T10:00:01Z</dateTime></NextUpdate>"}),
    ("NextUpdate 7 months", {"next": "<NextUpdate><dateTime>2026-06-01T10:00:00Z</dateTime></NextUpdate>"}),
    ("NextUpdate empty (closed list)", {"next": "<NextUpdate/>"}, "valid"),
    ("31 Aug + 6 months: 28 Feb", {"issue": "2025-08-31T00:00:00Z", "next": "<NextUpdate><dateTime>2026-02-28T00:00:00Z</dateTime></NextUpdate>"}, "valid"),
    ("31 Aug + 6 months: 1 Mar", {"issue": "2025-08-31T00:00:00Z", "next": "<NextUpdate><dateTime>2026-03-01T00:00:00Z</dateTime></NextUpdate>"}),
]
NOT_H = [
    ("HistoricalInformationPeriod present", {"hip": "<HistoricalInformationPeriod>0</HistoricalInformationPeriod>"}),
    ("no PointersToOtherLoTE", {"pointers": ""}),
    ("pointer not to itself", lambda p: {"pointers": p["pointers"].replace(f"<LoTEType>{p['lotetype']}", f"<LoTEType>{E}LoTEType/Other")}),
    ("ServiceStatus present", {"status": f"<ServiceStatus>{E}x</ServiceStatus>"}),
    ("StatusStartingTime present", {"start": "<StatusStartingTime>2025-11-01T10:00:00Z</StatusStartingTime>"}),
    ("identity by SKI only", {"sdi": SKI}),
    ("no Member State URI in TEInformationURI", {"teinfo": uris("https://p.be/terms", "https://p.be/more")}),
    ("ServiceHistory present (cl. 6.4.3)", {"history": HIST(f"<DigitalId><X509Certificate>{CERT}</X509Certificate></DigitalId>", E + "x")}),
    ("Member State URI with non-EU code US", lambda p: {"teinfo": ms(p, "US")}),
    ("Member State URI with GR (6.1.5 says EL)", lambda p: {"teinfo": ms(p, "GR")}),
    ("Member State URI with EL", lambda p: {"teinfo": ms(p, "EL")}, "valid"),
    ("Member State URI with 'Belgium'", lambda p: {"teinfo": ms(p, "Belgium")}),
]
ONLY = {
    "E": [("no ServiceUniqueIdentifier ext", {"ext": ""})],
    "G": [("SDA with corrected spelling", {"sda": E + "WRPRCProvidersList/StatusDetn/EU"}, "valid")],
    "H": [("no ds:Signature in XML (H.4: the Signature component shall be present)", {"sig": ""}),
          ("no HistoricalInformationPeriod", {"hip": ""}),
          ("history period 10", {"hip": "<HistoricalInformationPeriod>10</HistoricalInformationPeriod>"}),
          ("PointersToOtherLoTE present", lambda p: {"pointers": parts("D")["pointers"]}),
          ("no ServiceStatus", {"status": ""}),
          ("status not in list", {"status": f"<ServiceStatus>{E}PubEAAProvidersList/SvcStatus/granted</ServiceStatus>"}),
          ("no law reference in TETradeName", {"tradename": f"<TETradeName>{name('VATBE-0123456789')}</TETradeName>"}),
          ("law reference OJ:US (not EU/MS)", {"tradename": f"<TETradeName>{name('OJ:US:2020-1')}</TETradeName>"}),
          ("law reference OJ:GR (ISO code)", {"tradename": f"<TETradeName>{name('OJ:GR:2020-1')}</TETradeName>"}, "valid"),
          ("law reference OJ:EU", {"tradename": f"<TETradeName>{name('OJ:EU:2024/1183')}</TETradeName>"}, "valid"),
          ("website is only the ETSI URI", {"elec": uris("mailto:c@p.be", "tel:+32", E + "ListOfTrustedEntities/PubEAAProvider/BE")}),
          ("Member State URI with US in TE address", {"elec": uris("mailto:c@p.be", "https://p.be", "tel:+32", E + "ListOfTrustedEntities/PubEAAProvider/US")}),
          ("no Member State URI in TE address", {"elec": uris("mailto:c@p.be", "https://p.be", "tel:+32")}),
          ("identity without certificate (allowed)", {"sdi": SKI}, "valid"),
          ("history with certificate", {"history": HIST(f"{SKI}<DigitalId><X509Certificate>{CERT}</X509Certificate></DigitalId>", NOTIFIED)}),
          ("history with SKI only (allowed)", {"history": HIST(SKI, NOTIFIED)}, "valid")],
    "I": [("no ServiceSupplyPoints", {"supply": ""})],
}


def verdict(a, doc):
    try:
        XSD.validate(doc)
    except xmlschema.XMLSchemaValidationError as e:
        return ("XSD", str(e.reason)[:80])
    tree = etree.fromstring(doc.encode())
    for layer, sch in (("core Schematron", CORE_SCH), (f"Annex {a} Schematron", SCH[a])):
        if not sch.validate(tree):
            return (layer, etree.fromstring(sch.error_log.last_error.message.encode()).findtext(".//{*}text", "")[:80]
                    if sch.error_log else "")
    return None



def cases(a):
    return [("valid example", {}, "valid")] + [c if len(c) == 3 else c + ("invalid",)
                                              for c in COMMON + (NOT_H if a != "H" else []) + ONLY.get(a, [])]


PARAMS = [(a, i, c[0]) for a in P for i, c in enumerate(cases(a))]


@pytest.mark.parametrize("a,i,label", PARAMS, ids=[f"{a}-{lbl}" for a, i, lbl in PARAMS])
def test_profile_case(a, i, label):
    _, change, expect = cases(a)[i]
    p = parts(a)
    p.update(change(p) if callable(change) else change)
    v = verdict(a, xml(p))
    got = "invalid" if v else "valid"
    assert got == expect, f"Annex {a} {label}: expected {expect}, got {got}" + (f" [{v[0]}: {v[1]}]" if v else "")


@pytest.mark.parametrize("a,b", [(a, b) for a in P for b in P if a != b])
def test_rejects_other_annex(a, b):
    assert verdict(a, xml(parts(b))) is not None, f"Annex {a} accepts the Annex {b} list"
