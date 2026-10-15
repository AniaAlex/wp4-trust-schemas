"""Tests of the JSON profiles (Annexes D-I): the generated profiles (on the explicit track) and the earlier hand-written
ones are held to the same cases, per annex: the valid example, the annex's invalid mutations, and every other annex's list."""
import copy, json, os, pathlib
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from lote_schema_generator.paths import ROOT as _ROOT, HANDWRITTEN_CORE, HANDWRITTEN_PROFILES  # noqa: F401
ROOT = pathlib.Path(_ROOT)
# Two variants, each a core schema with its profiles: the earlier hand-written ones and the generated ones (explicit track).
VARIANTS = {"handwritten": (pathlib.Path(HANDWRITTEN_CORE), pathlib.Path(HANDWRITTEN_PROFILES)),
            "generated": (ROOT / "explicit" / "generated" / "base" / "lote_core.schema.json", ROOT / "explicit" / "generated" / "profiles")}
E = "http://uri.etsi.org/19602/"
ml = lambda v: [{"lang": "en", "value": v}]
mu = lambda *us: [{"lang": "en", "uriValue": u} for u in us]
addr = [{"lang": "en", "StreetAddress": "Rue de la Loi 200", "Locality": "Brussels", "Country": "BE"}]
CERT = "MIIBszCCAVmgAwIBAgIUQQ=="

P = {  # annex: (file, LoTEType, SDA, rules, TE uri, svc prefix)
 "D": ("lote_profile_D_pid_providers.json", "EUPIDProvidersList", "PIDProvidersList/StatusDetn/EU", "PIDProviders/schemerules/EU", "PIDProvider", "PID"),
 "E": ("lote_profile_E_wallet_providers.json", "EUWalletProvidersList", "WalletProvidersList/StatusDetn/EU", "WalletProvidersList/schemerules/EU", "WalletProvider", "WalletSolution"),
 "F": ("lote_profile_F_wrpac_providers.json", "EUWRPACProvidersList", "WRPACProvidersList/StatusDetn/EU", "WRPACProvidersList/schemerules/EU", "WRPACProvider", "WRPAC"),
 "G": ("lote_profile_G_wrprc_providers.json", "EUWRPRCProvidersList", "WRPRCrovidersList/StatusDetn/EU", "WRPRCProvidersList/schemerules/EU", "WRPRCProvider", "WRPRC"),
 "H": ("lote_profile_H_pub_eaa_providers.json", "EUPubEAAProvidersList", "PubEAAProvidersList/StatusDetn/EU", "PubEAAProvidersList/schemerules/EU", "PubEAAProvider", "PubEAA"),
 "I": ("lote_profile_I_registrars_and_registers.json", "EURegistrarsAndRegistersList", "RegistrarsAndRegistersList/StatusDetn/EU", "RegistrarsAndRegistersList/schemerules/EU", "Registrar", None),
}

def example(a):
    _, lt, sda, rules, teu, svc = P[a]
    lsi = {"LoTEVersionIdentifier": 1, "LoTESequenceNumber": 1, "LoTEType": E+"LoTEType/"+lt,
        "SchemeOperatorName": ml("European Commission"),
        "SchemeOperatorAddress": {"SchemeOperatorPostalAddress": addr, "SchemeOperatorElectronicAddress": mu("mailto:x@ec.europa.eu", "https://ec.europa.eu")},
        "SchemeName": ml("EU:" + lt), "SchemeInformationURI": mu("https://ec.europa.eu/lote/info", "https://ec.europa.eu/lote/history"),
        "StatusDeterminationApproach": E+sda, "SchemeTypeCommunityRules": mu(E+rules), "SchemeTerritory": "EU",
        "PolicyOrLegalNotice": [{"LoTEPolicy": {"lang": "en", "uriValue": "https://ec.europa.eu/policy"}}],
        "ListIssueDateTime": "2025-11-01T10:00:00Z", "NextUpdate": "2026-05-01T10:00:00Z"}
    ptr = [{"LoTELocation": "https://ec.europa.eu/lote.json", "ServiceDigitalIdentities": [{"X509Certificates": [CERT]}],
            "LoTEQualifiers": [{"LoTEType": E+"LoTEType/"+lt, "SchemeOperatorName": ml("EC"), "SchemeTerritory": "EU", "MimeType": "application/jose"}]}]
    elec = mu("mailto:c@p.be", "https://p.be", "tel:+3221234567")
    tei = {"TEName": ml("Provider BE"), "TEAddress": {"TEPostalAddress": addr, "TEElectronicAddress": elec},
           "TEInformationURI": mu("https://p.be/terms", E+f"ListOfTrustedEntities/{teu}/BE")}
    si = {"ServiceTypeIdentifier": E+(f"SvcType/{svc}/Issuance" if svc else "SvcType/Register"),
          "ServiceName": ml("Service"), "ServiceDigitalIdentity": {"X509Certificates": [CERT]}}
    if a == "H":
        lsi["HistoricalInformationPeriod"] = 65535
        tei["TETradeName"] = ml("OJ:BE:2020-123")
        tei["TEAddress"]["TEElectronicAddress"] = elec + mu(E+f"ListOfTrustedEntities/{teu}/BE")
        tei["TEInformationURI"] = mu("https://p.be/terms")
        si["ServiceStatus"] = E+"PubEAAProvidersList/SvcStatus/notified"
        si["StatusStartingTime"] = "2025-11-01T10:00:00Z"
    else:
        lsi["PointersToOtherLoTE"] = ptr
    if a == "E": si["ServiceInformationExtensions"] = [{"Critical": False, "ServiceUniqueIdentifier": "urn:eu:wallet:ref:123"}]
    if a == "I": si["ServiceSupplyPoints"] = [{"uriValue": "https://registry.be/api"}]
    return {"LoTE": {"LoTETag": "http://uri.etsi.org/19602/LoTETag", "ListAndSchemeInformation": lsi, "TrustedEntitiesList": [{"TrustedEntityInformation": tei, "TrustedEntityServices": [{"ServiceInformation": si}]}]}}

L = lambda d: d["LoTE"]["ListAndSchemeInformation"]
TE = lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityInformation"]
SI = lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityServices"][0]["ServiceInformation"]
def pop(k): return lambda o: o.pop(k)
def put(k, v): return lambda o: o.__setitem__(k, v)

common = [
  ("version 2", L, put("LoTEVersionIdentifier", 2)),
  ("wrong LoTEType", L, put("LoTEType", E+"LoTEType/EUPIDProvidersList_X")),
  ("wrong StatusDeterminationApproach", L, put("StatusDeterminationApproach", "http://example.eu/sda")),
  ("wrong SchemeTypeCommunityRules", L, put("SchemeTypeCommunityRules", mu("http://example.eu/rules"))),
  ("territory BE", L, put("SchemeTerritory", "BE")),
  ("implicit scheme info", L, lambda o: [o.pop(k) for k in ["SchemeName","SchemeInformationURI","StatusDeterminationApproach","SchemeTypeCommunityRules","PolicyOrLegalNotice"]]),
  ("wrong service type", SI, put("ServiceTypeIdentifier", E+"SvcType/Other")),
  ("no phone in TE address", lambda d: TE(d)["TEAddress"], lambda o: o.__setitem__("TEElectronicAddress", mu("mailto:c@p.be", "https://p.be") + ([] if o is None else [u for u in o["TEElectronicAddress"] if "ListOfTrustedEntities" in u["uriValue"]]))),
]
not_h = [
  ("HistoricalInformationPeriod present", L, put("HistoricalInformationPeriod", 0)),
  ("no PointersToOtherLoTE", L, pop("PointersToOtherLoTE")),
  ("pointer not to itself", L, lambda o: o["PointersToOtherLoTE"][0]["LoTEQualifiers"][0].__setitem__("LoTEType", E+"LoTEType/Other")),
  ("ServiceStatus present", SI, put("ServiceStatus", E+"x")),
  ("StatusStartingTime present", SI, put("StatusStartingTime", "2025-11-01T10:00:00Z")),
  ("identity by SKI only", SI, put("ServiceDigitalIdentity", {"X509SKIs": ["AAEC"]})),
  ("no Member State URI in TEInformationURI", TE, put("TEInformationURI", mu("https://p.be/terms", "https://p.be/more"))),
  ("ServiceHistory present (cl. 6.4.3)", lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityServices"][0], put("ServiceHistory", [{"ServiceName": ml("S"), "ServiceDigitalIdentity": {"X509Certificates": [CERT]}, "ServiceStatus": E+"x", "StatusStartingTime": "2025-01-01T00:00:00Z"}])),
  ("Member State URI with non-EU code US", TE, lambda o: o["TEInformationURI"][1].__setitem__("uriValue", o["TEInformationURI"][1]["uriValue"][:-2] + "US")),
  ("Member State URI with GR (6.1.5 says EL)", TE, lambda o: o["TEInformationURI"][1].__setitem__("uriValue", o["TEInformationURI"][1]["uriValue"][:-2] + "GR")),
  ("Member State URI with EL", TE, lambda o: o["TEInformationURI"][1].__setitem__("uriValue", o["TEInformationURI"][1]["uriValue"][:-2] + "EL"), "valid"),
  ("Member State URI with 'Belgium'", TE, lambda o: o["TEInformationURI"][1].__setitem__("uriValue", o["TEInformationURI"][1]["uriValue"][:-2] + "Belgium")),
]
only = {
 "E": [("no ServiceUniqueIdentifier ext", SI, pop("ServiceInformationExtensions"))],
 "G": [("SDA with corrected spelling", L, put("StatusDeterminationApproach", E+"WRPRCProvidersList/StatusDetn/EU"), "valid")],
 "H": [("no HistoricalInformationPeriod", L, pop("HistoricalInformationPeriod")),
       ("history period 10", L, put("HistoricalInformationPeriod", 10)),
       ("PointersToOtherLoTE present", L, put("PointersToOtherLoTE", [])),
       ("no ServiceStatus", SI, pop("ServiceStatus")),
       ("status not in list", SI, put("ServiceStatus", E+"PubEAAProvidersList/SvcStatus/granted")),
       ("no law reference in TETradeName", TE, put("TETradeName", ml("VATBE-0123456789"))),
       ("law reference OJ:US (not EU/MS)", TE, put("TETradeName", ml("OJ:US:2020-1"))),
       ("law reference OJ:GR (ISO code)", TE, put("TETradeName", ml("OJ:GR:2020-1")), "valid"),
       ("law reference OJ:EU", TE, put("TETradeName", ml("OJ:EU:2024/1183")), "valid"),
       ("website is only the ETSI URI", lambda d: TE(d)["TEAddress"], put("TEElectronicAddress", mu("mailto:c@p.be", "tel:+32", E+"ListOfTrustedEntities/PubEAAProvider/BE"))),
       ("Member State URI with US in TE address", lambda d: TE(d)["TEAddress"], put("TEElectronicAddress", mu("mailto:c@p.be", "https://p.be", "tel:+32", E+"ListOfTrustedEntities/PubEAAProvider/US"))),
       ("no Member State URI in TE address", lambda d: TE(d)["TEAddress"], put("TEElectronicAddress", mu("mailto:c@p.be", "https://p.be", "tel:+32"))),
       ("identity without certificate (allowed)", SI, put("ServiceDigitalIdentity", {"X509SKIs": ["AAEC"]}), "valid"),
       ("history with certificate", lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityServices"][0], put("ServiceHistory", [{"ServiceName": ml("S"), "ServiceDigitalIdentity": {"X509SKIs": ["AAEC"], "X509Certificates": [CERT]}, "ServiceStatus": E+"PubEAAProvidersList/SvcStatus/notified", "StatusStartingTime": "2025-01-01T00:00:00Z"}])),
       ("history with SKI only (allowed)", lambda d: d["LoTE"]["TrustedEntitiesList"][0]["TrustedEntityServices"][0], put("ServiceHistory", [{"ServiceName": ml("S"), "ServiceDigitalIdentity": {"X509SKIs": ["AAEC"]}, "ServiceStatus": E+"PubEAAProvidersList/SvcStatus/notified", "StatusStartingTime": "2025-01-01T00:00:00Z"}]), "valid")],
 "I": [("no ServiceSupplyPoints", SI, pop("ServiceSupplyPoints"))],
}


_V = {}


def profile_validator(variant, a):
    if (variant, a) not in _V:
        core_path, profile_dir = VARIANTS[variant]
        core = json.load(open(core_path, encoding="utf-8"))
        reg = Registry().with_resource("file://" + str(core_path.resolve()), Resource.from_contents(core))
        path = (profile_dir / P[a][0]).resolve()
        schema = json.load(open(path, encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        _V[(variant, a)] = (Draft202012Validator({**schema, "$id": "file://" + str(path)}, registry=reg, format_checker=FormatChecker()),
                            Draft202012Validator(core, format_checker=FormatChecker()))
    return _V[(variant, a)]


def cases(a):
    return [("valid example", lambda d: d, lambda o: None, "valid")] + \
        [c + ("invalid",) if len(c) == 3 else c for c in common + (not_h if a != "H" else []) + only.get(a, [])]


PARAMS = [(v, a, i, c[0]) for v in VARIANTS for a in P for i, c in enumerate(cases(a))]


@pytest.mark.parametrize("variant,a,i,label", PARAMS, ids=[f"{v}-{a}-{lbl}" for v, a, i, lbl in PARAMS])
def test_profile_case(variant, a, i, label):
    v, _ = profile_validator(variant, a)
    _, sel, f, expect = cases(a)[i]
    d = example(a); f(sel(d))
    errs = list(v.iter_errors(d))
    assert (not errs) == (expect == "valid"), f"Annex {a} {label}: expected {expect}" + (f" - {errs[0].message[:200]}" if errs else "")


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("a,b", [(a, b) for a in P for b in P if a != b])
def test_rejects_other_annex(variant, a, b):
    v, _ = profile_validator(variant, a)
    assert list(v.iter_errors(example(b))), f"Annex {a} profile accepts the Annex {b} list"


@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("a", sorted(P))
def test_example_valid_against_core(variant, a):
    _, core_v = profile_validator(variant, a)
    errs = list(core_v.iter_errors(example(a)))
    assert not errs, errs[0].message[:200] if errs else ""
