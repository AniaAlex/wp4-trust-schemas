"""Clause-by-clause tests of the core JSON schema against ETSI TS 119 602 V1.1.1 (clauses 5-6, Annex B): the generated
core (both kinds of list) and the earlier hand-written schema are held to the same cases."""
import copy, json, os, pathlib
import pytest
from jsonschema import Draft202012Validator, FormatChecker

from lote_schema_generator.paths import ROOT as _ROOT, HANDWRITTEN_CORE, HANDWRITTEN_PROFILES  # noqa: F401
ROOT = pathlib.Path(_ROOT)
# The same cases against the earlier hand-written core schema and the generated core (both kinds of list).
SCHEMAS = {"handwritten": pathlib.Path(HANDWRITTEN_CORE), "generated": ROOT / "base" / "generated" / "lote_core.schema.json"}
_VALIDATORS = {}


def validator(name):
    if name not in _VALIDATORS:
        core = json.load(open(SCHEMAS[name], encoding="utf-8"))
        Draft202012Validator.check_schema(core)
        _VALIDATORS[name] = Draft202012Validator(core, format_checker=FormatChecker())
    return _VALIDATORS[name]

ml = lambda v, l="en": [{"lang": l, "value": v}]
mu = lambda *us: [{"lang": "en", "uriValue": u} for u in us]
addr = [{"lang": "en", "StreetAddress": "Rue de la Loi 200", "Locality": "Brussels", "Country": "BE"}]
CERT = "MIIBszCCAVmgAwIBAgIUQQ=="
TAG = "http://uri.etsi.org/19602/LoTETag"         # any URI: the text registers no Tag URI value


def base():
    return copy.deepcopy({"LoTE": {
        "LoTETag": TAG,
        "ListAndSchemeInformation": {
            "LoTEVersionIdentifier": 1, "LoTESequenceNumber": 1,
            "LoTEType": "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList",
            "SchemeOperatorName": ml("European Commission"),
            "SchemeOperatorAddress": {"SchemeOperatorPostalAddress": addr,
                                      "SchemeOperatorElectronicAddress": mu("mailto:x@ec.europa.eu", "https://ec.europa.eu")},
            "SchemeName": ml("EU:PID providers list"),
            "SchemeInformationURI": mu("https://ec.europa.eu/lote"),
            "StatusDeterminationApproach": "http://uri.etsi.org/19602/PIDProvidersList/StatusDetn/EU",
            "SchemeTypeCommunityRules": mu("http://uri.etsi.org/19602/PIDProviders/schemerules/EU"),
            "SchemeTerritory": "EU",
            "PolicyOrLegalNotice": [{"LoTEPolicy": {"lang": "en", "uriValue": "https://ec.europa.eu/policy"}}],
            "ListIssueDateTime": "2025-11-01T10:00:00Z", "NextUpdate": "2026-05-01T10:00:00Z",
        },
        "TrustedEntitiesList": [{
            "TrustedEntityInformation": {
                "TEName": ml("Provider BE"),
                "TEAddress": {"TEPostalAddress": addr, "TEElectronicAddress": mu("mailto:c@p.be", "https://p.be")},
                "TEInformationURI": mu("https://p.be/terms"),
            },
            "TrustedEntityServices": [{"ServiceInformation": {
                "ServiceName": ml("Service"),
                "ServiceDigitalIdentity": {"X509Certificates": [CERT]},
            }}],
        }],
    }})


LSI = lambda d: d["LoTE"]["ListAndSchemeInformation"]
TE = lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityInformation"]
TS = lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityServices"][0]
SI = lambda d: TS(d)["ServiceInformation"]
SDI = lambda d: SI(d)["ServiceDigitalIdentity"]
put = lambda sel, k, v: (lambda d: sel(d).__setitem__(k, v))
pop = lambda sel, *ks: (lambda d: [sel(d).pop(k) for k in ks])
IMPLICIT_ONLY = ["SchemeName", "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules", "PolicyOrLegalNotice"]
HIST = {"ServiceName": ml("S"), "ServiceDigitalIdentity": {"X509SKIs": ["AAEC"]},
        "ServiceStatus": "http://example.eu/status/granted", "StatusStartingTime": "2025-01-01T00:00:00Z"}

# (clause, label, expected, mutation)
CASES = [
    ("-", "valid explicit list", "valid", lambda d: None),
    ("5/6.2", "LoTETag present as URI", "valid", put(lambda d: d["LoTE"], "LoTETag", "http://uri.etsi.org/19602/LoTETag")),
    ("5/6.2", "LoTETag with another URI (no value registered)", "valid", put(lambda d: d["LoTE"], "LoTETag", "https://example.eu/my-lote-tag")),
    ("5", "no LoTETag (clause 5: exactly one tag)", "invalid", pop(lambda d: d["LoTE"], "LoTETag")),
    ("6.8.0", "Signature inside LoTE in JSON (JSON signs by encapsulation)", "invalid", put(lambda d: d["LoTE"], "Signature", {"protected": "eyJ", "signature": "AAA"})),
    ("5/6.2", "LoTETag not a URI", "invalid", put(lambda d: d["LoTE"], "LoTETag", "not a uri")),
    ("5", "unknown top-level component", "invalid", put(lambda d: d["LoTE"], "Foo", 1)),
    ("6.3.0/T1", "minimal implicit list", "valid", pop(LSI, "LoTEType", "SchemeOperatorAddress", "SchemeTerritory", *IMPLICIT_ONLY)),
    ("6.3.0/T1", "implicit list with SchemeName ('/' element)", "invalid", pop(LSI, "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules", "PolicyOrLegalNotice")),
    ("6.3.0/T1", "no ListIssueDateTime (M)", "invalid", pop(LSI, "ListIssueDateTime")),
    ("6.3.1", "version 0 (text imposes no value)", "valid", put(LSI, "LoTEVersionIdentifier", 0)),
    ("6.3.1", "version as string", "invalid", put(LSI, "LoTEVersionIdentifier", "1")),
    ("6.3.2", "sequence number 0", "invalid", put(LSI, "LoTESequenceNumber", 0)),
    ("6.3.3", "LoTEType not a URI", "invalid", put(LSI, "LoTEType", "PID list")),
    ("6.3.5.1", "postal Country GR (6.1.5 says EL)", "invalid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("Country", "GR")),
    ("6.3.5.1", "postal Country EL", "valid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("Country", "EL")),
    ("6.3.5.1", "postal Country UK", "valid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("Country", "UK")),
    ("6.3.5.1", "postal Country XX (not ISO 3166-1)", "invalid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("Country", "XX")),
    ("6.3.5.1", "postal Country 'Belgium'", "invalid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("Country", "Belgium")),
    ("6.3.5.1", "no StreetAddress", "invalid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].pop("StreetAddress")),
    ("6.3.5.1/6.1.4", "postal address only in German", "invalid", lambda d: LSI(d)["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0].__setitem__("lang", "de")),
    ("6.3.5.2", "no mailto: address", "invalid", put(lambda d: LSI(d)["SchemeOperatorAddress"], "SchemeOperatorElectronicAddress", mu("https://ec.europa.eu", "tel:+32"))),
    ("6.3.5.2", "no web-site", "invalid", put(lambda d: LSI(d)["SchemeOperatorAddress"], "SchemeOperatorElectronicAddress", mu("mailto:x@ec.europa.eu", "tel:+32"))),
    ("6.3.6", "SchemeName without CC: prefix", "invalid", put(LSI, "SchemeName", ml("PID providers list"))),
    ("6.3.6", "SchemeName only in French", "invalid", put(LSI, "SchemeName", ml("EU:Liste", "fr"))),
    ("6.3.10", "SchemeTerritory GR", "invalid", put(LSI, "SchemeTerritory", "GR")),
    ("6.3.10", "SchemeTerritory GB", "invalid", put(LSI, "SchemeTerritory", "GB")),
    ("6.3.10", "SchemeTerritory ASIA (6.1.5 b)", "valid", put(LSI, "SchemeTerritory", "ASIA")),
    ("6.3.10", "SchemeTerritory '12'", "invalid", put(LSI, "SchemeTerritory", "12")),
    ("6.3.11", "legal notice as multilingual strings", "valid", put(LSI, "PolicyOrLegalNotice", [{"LoTELegalNotice": {"lang": "en", "value": "Notice"}}])),
    ("6.3.11", "legal notice as bare string", "invalid", put(LSI, "PolicyOrLegalNotice", [{"LoTELegalNotice": "Notice"}])),
    ("6.3.11", "policy and notice mixed", "invalid", put(LSI, "PolicyOrLegalNotice", [{"LoTEPolicy": {"lang": "en", "uriValue": "https://x.eu"}}, {"LoTELegalNotice": {"lang": "en", "value": "N"}}])),
    ("6.3.11/6.1.4", "policy only in German", "invalid", put(LSI, "PolicyOrLegalNotice", [{"LoTEPolicy": {"lang": "de", "uriValue": "https://x.eu"}}])),
    ("6.3.12", "history period 70000 (no maximum in text)", "valid", lambda d: (LSI(d).__setitem__("HistoricalInformationPeriod", 70000), SI(d).__setitem__("ServiceStatus", "http://example.eu/s"))),
    ("6.3.12", "history period -1", "invalid", put(LSI, "HistoricalInformationPeriod", -1)),
    ("6.3.12", "history period 0 without ServiceStatus", "valid", put(LSI, "HistoricalInformationPeriod", 0)),
    ("6.6.0", "history period 65535 without ServiceStatus", "invalid", put(LSI, "HistoricalInformationPeriod", 65535)),
    ("6.3.13", "pointer qualifier without SchemeTerritory", "invalid", put(LSI, "PointersToOtherLoTE", [{"LoTELocation": "https://x.eu/l.json", "ServiceDigitalIdentities": [{"X509Certificates": [CERT]}], "LoTEQualifiers": [{"LoTEType": "http://x.eu/t", "SchemeOperatorName": ml("EC"), "MimeType": "application/jose"}]}])),
    ("6.3.13", "pointer without digital identity", "invalid", put(LSI, "PointersToOtherLoTE", [{"LoTELocation": "https://x.eu/l.json", "ServiceDigitalIdentities": [], "LoTEQualifiers": [{"LoTEType": "http://x.eu/t", "SchemeOperatorName": ml("EC"), "SchemeTerritory": "EU", "MimeType": "application/jose"}]}])),
    ("6.1.3", "date-time with fraction and offset", "invalid", put(LSI, "ListIssueDateTime", "2025-11-01T11:00:00.5+01:00")),
    ("6.1.3", "date-time 'tomorrow'", "invalid", put(LSI, "NextUpdate", "tomorrow")),
    ("6.3.15", "NextUpdate null (closed list)", "valid", put(LSI, "NextUpdate", None)),
    ("6.3.16", "DistributionPoints empty", "invalid", put(LSI, "DistributionPoints", [])),
    ("6.3.17", "scheme extension without criticality", "invalid", put(LSI, "SchemeExtensions", [{"foo": 1}])),
    ("6.3.17", "scheme extension with criticality", "valid", put(LSI, "SchemeExtensions", [{"Critical": False, "foo": 1}])),
    ("6.4.0", "empty TrustedEntitiesList", "invalid", put(lambda d: d["LoTE"], "TrustedEntitiesList", [])),
    ("6.4.2", "entity with no services", "invalid", put(lambda d: d["LoTE"]["TrustedEntitiesList"][0], "TrustedEntityServices", [])),
    ("6.4.3/6.7", "valid history instance", "valid", put(TS, "ServiceHistory", [HIST])),
    ("6.7", "history instance without StatusStartingTime", "invalid", put(TS, "ServiceHistory", [{k: v for k, v in HIST.items() if k != "StatusStartingTime"}])),
    ("6.5.0", "entity without TEInformationURI", "invalid", pop(TE, "TEInformationURI")),
    ("6.5.1/6.1.4", "TEName only in Dutch", "invalid", put(TE, "TEName", ml("Aanbieder", "nl"))),
    ("6.5.5", "TE extension without criticality (format open)", "valid", put(TE, "TEInformationExtensions", [{"foo": 1}])),
    ("6.5.5.1.1", "associated body without name", "invalid", put(TE, "TEInformationExtensions", [{"OtherAssociatedBodies": [{"AssociatedBodyTypeIdentifier": "http://x.eu/t"}]}])),
    ("6.6.0", "service without ServiceName", "invalid", pop(SI, "ServiceName")),
    ("6.6.0", "unknown service component", "invalid", put(SI, "Foo", 1)),
    ("6.6.3.0", "empty ServiceDigitalIdentity", "invalid", put(SI, "ServiceDigitalIdentity", {})),
    ("6.6.3.0", "identity key typo X509Certificate", "invalid", put(SI, "ServiceDigitalIdentity", {"X509Certificate": [CERT]})),
    ("6.6.3.1", "certificate as Base64 string", "valid", lambda d: None),
    ("6.6.3.1", "certificate wrapped in an object", "invalid", put(SI, "ServiceDigitalIdentity", {"X509Certificates": [{"val": CERT}]})),
    ("6.6.3.1", "certificate not Base64 ('%%%')", "invalid", put(SI, "ServiceDigitalIdentity", {"X509Certificates": ["%%%"]})),
    ("6.6.3.1", "certificate Base64 of wrong length (23 chars)", "invalid", put(SI, "ServiceDigitalIdentity", {"X509Certificates": ["MIIBszCCAVmgAwIBAgIUQ=="]})),
    ("6.6.3.3", "PublicKeyValue as JWK (format open)", "valid", put(SI, "ServiceDigitalIdentity", {"PublicKeyValues": [{"kty": "EC", "crv": "P-256", "x": "a", "y": "b"}]})),
    ("6.6.3.3", "PublicKeyValue as string (format open)", "valid", put(SI, "ServiceDigitalIdentity", {"PublicKeyValues": ["MFkwEwYHKoZIzj0CAQ"]})),
    ("6.6.3.4", "X509SKI in any format (format open)", "valid", put(SI, "ServiceDigitalIdentity", {"X509SKIs": ["40:FD:F7"]})),
    ("6.6.3.5", "OtherId as object (format open)", "valid", put(SI, "ServiceDigitalIdentity", {"OtherIds": [{"scheme": "did", "id": "did:web:x"}]})),
    ("6.6.3.x", "empty identifier list", "invalid", put(SI, "ServiceDigitalIdentity", {"X509SKIs": []})),
    ("6.6.4", "ServiceStatus not a URI", "invalid", put(SI, "ServiceStatus", "granted")),
    ("6.6.7", "ServiceSupplyPoints empty", "invalid", put(SI, "ServiceSupplyPoints", [])),
    ("6.6.7", "supply point with type URI", "valid", put(SI, "ServiceSupplyPoints", [{"ServiceType": "http://x.eu/t", "uriValue": "https://x.eu/api"}])),
    ("6.6.9.1", "ServiceUniqueIdentifier not a URI", "invalid", put(SI, "ServiceInformationExtensions", [{"ServiceUniqueIdentifier": "not a uri"}])),
    ("6.1.4/B.1", "lang 'EN' (upper case)", "invalid", put(TE, "TEName", ml("Provider", "EN"))),
    ("6.1.4/B.1", "lang '' (empty)", "invalid", put(TE, "TEName", ml("Provider", ""))),
    ("B.1", "transliteration 'bg-Latn' next to 'en'", "valid", put(TE, "TEName", ml("Provider") + ml("Dostavchik", "bg-Latn"))),
    ("B.2 4)", "text with line feed", "invalid", put(TE, "TEName", ml("Pro\nvider"))),
    ("B.2 3)", "text with leading UCS signature (BOM)", "invalid", put(TE, "TEName", ml("﻿Provider"))),
    ("B.2 5)", "private-use character U+E000", "invalid", put(TE, "TEName", ml("Provider"))),
    ("B.2 5)", "private-use plane 0F character", "invalid", put(TE, "TEName", ml("Pro\U000F0001vider"))),
    ("B.2 6)", "Tag Character U+E0041", "invalid", put(TE, "TEName", ml("Pro\U000E0041vider"))),
    ("B.2", "Greek text and emoji are allowed", "valid", put(TE, "TEName", ml("Ελλάδα 😀"))),
]


@pytest.mark.parametrize("schema", sorted(SCHEMAS))
@pytest.mark.parametrize("clause,label,expect,mutate", CASES, ids=[f"{c[0]} {c[1]}" for c in CASES])
def test_case(schema, clause, label, expect, mutate):
    d = base(); mutate(d)
    errs = list(validator(schema).iter_errors(d))
    assert (not errs) == (expect == "valid"), f"[{clause}] {label}: expected {expect}" + (f" - {errs[0].message[:200]}" if errs else "")
