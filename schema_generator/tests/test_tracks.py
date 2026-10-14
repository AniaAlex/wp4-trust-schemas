"""Tests of the two scheme tracks (clause 6.3.0, Table 1) against the three generated variants, in JSON and XML:
  core      core/generated/       both kinds of list: Table 1 and the placement as rules (R-Table1, R-SchemeInfoPlacement)
  explicit  explicit/generated/   Table 1 explicit column as structure
  implicit  implicit/generated/   Table 1 implicit column as structure; the list information in ListAndSchemeInformation
                                  or directly in the list (6.3.0)

"""
import copy, json, pathlib, sys
import pytest
import xmlschema
from jsonschema import Draft202012Validator, FormatChecker
from lxml import etree, isoschematron

from lote_schema_generator.paths import ROOT as _ROOT, HANDWRITTEN_CORE, HANDWRITTEN_PROFILES  # noqa: F401
ROOT = pathlib.Path(_ROOT)
VARIANTS = {"core": ROOT / "core" / "generated", "explicit": ROOT / "explicit" / "generated", "implicit": ROOT / "implicit" / "generated"}
NS = "http://uri.etsi.org/019602/v1#"
COMMON = ["LoTEVersionIdentifier", "LoTESequenceNumber", "SchemeOperatorName", "ListIssueDateTime", "NextUpdate"]
EXPLICIT_ONLY = ["LoTEType", "SchemeOperatorAddress", "SchemeName", "SchemeInformationURI", "StatusDeterminationApproach",
                 "SchemeTypeCommunityRules", "SchemeTerritory", "PolicyOrLegalNotice"]

# ------------------------------------------------------------------ the list information, per component (JSON / XML)
ml = lambda v: [{"lang": "en", "value": v}]
mu = lambda *us: [{"lang": "en", "uriValue": u} for u in us]
E = "http://uri.etsi.org/19602/"
JSON = {
    "LoTEVersionIdentifier": 1, "LoTESequenceNumber": 1,
    "LoTEType": E + "LoTEType/EUPIDProvidersList",
    "SchemeOperatorName": ml("Operator"),
    "SchemeOperatorAddress": {"SchemeOperatorPostalAddress": [{"lang": "en", "StreetAddress": "Main 1", "Country": "BE"}],
                              "SchemeOperatorElectronicAddress": mu("mailto:x@op.eu", "https://op.eu")},
    "SchemeName": ml("EU:Example list"),
    "SchemeInformationURI": mu("https://op.eu/list"),
    "StatusDeterminationApproach": E + "PIDProvidersList/StatusDetn/EU",
    "SchemeTypeCommunityRules": mu(E + "PIDProviders/schemerules/EU"),
    "SchemeTerritory": "EU",
    "PolicyOrLegalNotice": [{"LoTEPolicy": {"lang": "en", "uriValue": "https://op.eu/policy"}}],
    "ListIssueDateTime": "2026-01-01T00:00:00Z", "NextUpdate": "2026-06-01T00:00:00Z",
}
XML = {
    "LoTEVersionIdentifier": "<LoTEVersionIdentifier>1</LoTEVersionIdentifier>",
    "LoTESequenceNumber": "<LoTESequenceNumber>1</LoTESequenceNumber>",
    "LoTEType": f"<LoTEType>{E}LoTEType/EUPIDProvidersList</LoTEType>",
    "SchemeOperatorName": '<SchemeOperatorName><Name xml:lang="en">Operator</Name></SchemeOperatorName>',
    "SchemeOperatorAddress": ('<SchemeOperatorAddress><PostalAddresses><PostalAddress xml:lang="en"><StreetAddress>Main 1'
                              '</StreetAddress><Country>BE</Country></PostalAddress></PostalAddresses><ElectronicAddress>'
                              '<URI xml:lang="en">mailto:x@op.eu</URI><URI xml:lang="en">https://op.eu</URI></ElectronicAddress>'
                              '</SchemeOperatorAddress>'),
    "SchemeName": '<SchemeName><Name xml:lang="en">EU:Example list</Name></SchemeName>',
    "SchemeInformationURI": '<SchemeInformationURI><URI xml:lang="en">https://op.eu/list</URI></SchemeInformationURI>',
    "StatusDeterminationApproach": f"<StatusDeterminationApproach>{E}PIDProvidersList/StatusDetn/EU</StatusDeterminationApproach>",
    "SchemeTypeCommunityRules": f'<SchemeTypeCommunityRules><URI xml:lang="en">{E}PIDProviders/schemerules/EU</URI></SchemeTypeCommunityRules>',
    "SchemeTerritory": "<SchemeTerritory>EU</SchemeTerritory>",
    "PolicyOrLegalNotice": '<PolicyOrLegalNotice><LoTEPolicy xml:lang="en">https://op.eu/policy</LoTEPolicy></PolicyOrLegalNotice>',
    "ListIssueDateTime": "<ListIssueDateTime>2026-01-01T00:00:00Z</ListIssueDateTime>",
    "NextUpdate": "<NextUpdate><dateTime>2026-06-01T00:00:00Z</dateTime></NextUpdate>",
}
ORDER = ["LoTEVersionIdentifier", "LoTESequenceNumber", "LoTEType", "SchemeOperatorName", "SchemeOperatorAddress", "SchemeName",
         "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules", "SchemeTerritory",
         "PolicyOrLegalNotice", "ListIssueDateTime", "NextUpdate"]


def lst(lsi=None, direct=None):
    """A list with these components in ListAndSchemeInformation (None: no component) and these directly in the list."""
    lsi_names = [n for n in ORDER if n in (lsi or [])] if lsi is not None else None
    direct_names = [n for n in ORDER if n in (direct or [])]
    j = {"LoTE": {"LoTETag": "http://uri.etsi.org/19602/LoTETag"}}
    if lsi_names is not None:
        j["LoTE"]["ListAndSchemeInformation"] = {n: copy.deepcopy(JSON[n]) for n in lsi_names}
    j["LoTE"].update({n: copy.deepcopy(JSON[n]) for n in direct_names})
    x = f'<ListOfTrustedEntities xmlns="{NS}" LoTETag="http://uri.etsi.org/19602/LoTETag">'
    if lsi_names is not None:
        x += "<ListAndSchemeInformation>" + "".join(XML[n] for n in lsi_names) + "</ListAndSchemeInformation>"
    x += "".join(XML[n] for n in direct_names) + "</ListOfTrustedEntities>"
    return j, x


V, I = "valid", "invalid"
# (label, (lsi, direct), expected for core / explicit / implicit)
CASES = [
    ("explicit list (Table 1, explicit column)", (COMMON + EXPLICIT_ONLY, None), (V, V, I)),
    ("implicit list, ListAndSchemeInformation with the 5 common elements", (COMMON, None), (V, I, V)),
    ("implicit list with the optional LoTEType, SchemeOperatorAddress, SchemeTerritory", (COMMON + ["LoTEType", "SchemeOperatorAddress", "SchemeTerritory"], None), (V, I, V)),
    ("implicit list without ListAndSchemeInformation: the 5 elements directly (6.3.0)", (None, COMMON), (V, I, V)),
    ("implicit list with SchemeName ('/' in Table 1)", (COMMON + ["SchemeName"], None), (I, I, I)),
    ("explicit list without SchemeName (Table 1 only, defect 19)", (COMMON + [n for n in EXPLICIT_ONLY if n != "SchemeName"], None), (I, I, I)),
    ("explicit list without SchemeOperatorAddress (Table 1 only, defect 19)", (COMMON + [n for n in EXPLICIT_ONLY if n != "SchemeOperatorAddress"], None), (I, I, I)),
    ("both placements: ListAndSchemeInformation and the elements directly", (COMMON, COMMON), (I, I, I)),
    ("neither placement", (None, None), (I, I, I)),
    ("direct placement without NextUpdate", (None, [n for n in COMMON if n != "NextUpdate"]), (I, I, I)),
]



_CHECKERS = {}


def checkers(variant):
    if variant not in _CHECKERS:
        d = VARIANTS[variant]
        _CHECKERS[variant] = (Draft202012Validator(json.load(open(d / "lote_core.schema.json")), format_checker=FormatChecker()),
                              xmlschema.XMLSchema(str(d / "lote_core.xsd")),
                              isoschematron.Schematron(etree.parse(str(d / "lote_core.sch"))))
    return _CHECKERS[variant]


PARAMS = [(label, placement, variant, want, binding)
          for label, placement, expected in CASES for variant, want in zip(VARIANTS, expected) for binding in ("json", "xml")]


@pytest.mark.parametrize("label,placement,variant,want,binding", PARAMS,
                         ids=[f"{v}-{b}-{lbl}" for lbl, _, v, _, b in PARAMS])
def test_track(label, placement, variant, want, binding):
    jv, xsd, sch = checkers(variant)
    j, x = lst(*placement)
    if binding == "json":
        err = next(iter(jv.iter_errors(j)), None)
        msg = err and err.message[:200]
    else:
        xerr = next(iter(xsd.iter_errors(x)), None)
        msg = xerr and "XSD: " + (xerr.reason or "")[:200]
        if not xerr and not sch.validate(etree.fromstring(x.encode())):
            msg = "Schematron: " + " ".join(sch.error_log.last_error.message.split())[:200]
    got = I if msg else V
    assert got == want, f"{variant} {binding} {label}: expected {want}, got {got}" + (f" [{msg}]" if msg else "")
