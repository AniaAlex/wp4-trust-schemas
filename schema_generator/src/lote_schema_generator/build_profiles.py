"""Build the profile overlays (Annexes D-I) and the registered URIs (Annex C) on top of the explicit track of the LoTE
model (explicit/model/lote_model_explicit.json, built by build_schemes.py): every annex requires a scheme explicit list (x.1).

Semantics follow FHIR profiling (a StructureDefinition with derivation "constraint" and a differential), which is
also how ISO 20022 usage guidelines restrict a base message:
  - each profile is a differential: a list of elements, each addressing a core-model path;
  - an element may only NARROW the base: raise min, lower max (max "0" = prohibited), fix a value (fixed[x]),
    restrict values to a value set (binding, strength "required"), or add invariants (constraint: key, severity,
    human, expression in FHIRPath over the abstract model, evaluated from the element at the element's path, as in
    FHIR; null when not machine-checkable). A repeating component (e.g. a multilingual sequence) is a repeating element,
    so checks across its entries sit on the parent element.
TS 119 602 clause 4.7 states the same rule: "LoTE profile cannot however make the presence of a mandatory component
optional or conditioned."

Outputs: model/registered_uris.json, model/profiles/<letter>_<name>.json.
Checks (the build fails otherwise):
  - every quote is found verbatim inside its own annex (Annex C for registered URIs); page and line are computed;
  - every path resolves in the explicit track (explicit/model/lote_model_explicit.json);
  - every element only narrows the explicit track (min, max, fixed only on optional/allowed components, ...);
  - every fixed URI of Tables x.1 is a registered URI of Annex C;
  - a binding of one syntax on an element ('json' / 'xml') says where it comes from (text with a quote found in the
    annex, wp4 or project with a reason);
  - every element agrees with the generated profile schema in core/profiles/ (const, enum, required, prohibited).
"""
import json, os, re, sys

from . import spec_text as bm                              # spec index and quote normaliser
from .build_schemes import allowed
from .paths import HANDWRITTEN_PROFILES, MODEL_DIR, SNAPSHOT

MODEL = SNAPSHOT["explicit"]                                # the profiles narrow the explicit track (x.1)
BASE = "model/schemes/explicit.json"
OUT_DIR = MODEL_DIR
PROFILE_SCHEMAS = HANDWRITTEN_PROFILES                     # the hand-written profiles, for the agreement check
E = "http://uri.etsi.org/19602/"
EU27 = "AT|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|HR|HU|IE|IT|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK"
EU27_ISO = EU27.replace("EL", "GR")

LSI = "LoTE.ListAndSchemeInformation"
TEI = "LoTE.TrustedEntitiesList.TrustedEntity.TrustedEntityInformation"
SVC = "LoTE.TrustedEntitiesList.TrustedEntity.TrustedEntityServices.TrustedEntityService"
SI = SVC + ".ServiceInformation"
HIST = SVC + ".ServiceHistory.ServiceHistoryInstance"

# ------------------------------------------------------------------ Annex C: registered URIs (value sets)
REGISTERED = {
    "LoTEType": ("C.2.1", [E + "LoTEType/EUPIDProvidersList", E + "LoTEType/EUWalletProvidersList",
                           E + "LoTEType/EUWRPACProvidersList", E + "LoTEType/EUWRPRCProvidersList",
                           E + "LoTEType/EUPubEAAProvidersList", E + "LoTEType/EURegistrarsAndRegistersList"]),
    "StatusDeterminationApproach": ("C.2.2", [E + "PIDProvidersList/StatusDetn/EU", E + "WalletProvidersList/StatusDetn/EU",
                                              E + "WRPACProvidersList/StatusDetn/EU", E + "WRPRCrovidersList/StatusDetn/EU",
                                              E + "PubEAAProvidersList/StatusDetn/EU", E + "RegistrarsAndRegistersList/StatusDetn/EU"]),
    "SchemeTypeCommunityRules": ("C.2.3", [E + "PIDProviders/schemerules/EU", E + "WalletProvidersList/schemerules/EU",
                                           E + "WRPACProvidersList/schemerules/EU", E + "WRPRCProvidersList/schemerules/EU",
                                           E + "PubEAAProvidersList/schemerules/EU", E + "RegistrarsAndRegistersList/schemerules/EU"]),
}

# ------------------------------------------------------------------ per-annex parameters
ANNEX = {
    "D": dict(file="D_pid_providers", title="PID providers list", typ="EUPIDProvidersList", sda="PIDProvidersList",
              rules="PIDProviders", te="PIDProvider", svc=["PID/Issuance", "PID/Revocation"]),
    "E": dict(file="E_wallet_providers", title="Wallet providers list", typ="EUWalletProvidersList", sda="WalletProvidersList",
              rules="WalletProvidersList", te="WalletProvider", svc=["WalletSolution/Issuance", "WalletSolution/Revocation"]),
    "F": dict(file="F_wrpac_providers", title="WRPAC providers list", typ="EUWRPACProvidersList", sda="WRPACProvidersList",
              rules="WRPACProvidersList", te="WRPACProvider", svc=["WRPAC/Issuance", "WRPAC/Revocation"]),
    "G": dict(file="G_wrprc_providers", title="WRPRC providers list", typ="EUWRPRCProvidersList", sda="WRPRCrovidersList",
              rules="WRPRCProvidersList", te="WRPRCProvider", svc=["WRPRC/Issuance", "WRPRC/Revocation"]),
    "H": dict(file="H_pub_eaa_providers", title="Pub-EAA providers list", typ="EUPubEAAProvidersList", sda="PubEAAProvidersList",
              rules="PubEAAProvidersList", te="PubEAAProvider", svc=["PubEAA/Issuance", "PubEAA/Revocation"]),
    "I": dict(file="I_registrars_and_registers", title="List of registrars and registers", typ="EURegistrarsAndRegistersList",
              sda="RegistrarsAndRegistersList", rules="RegistrarsAndRegistersList", te="Registrar", svc=["Register"]),
}
PROFILE_SCHEMA_FILE = {"D": "lote_profile_D_pid_providers.json", "E": "lote_profile_E_wallet_providers.json",
                       "F": "lote_profile_F_wrpac_providers.json", "G": "lote_profile_G_wrprc_providers.json",
                       "H": "lote_profile_H_pub_eaa_providers.json", "I": "lote_profile_I_registrars_and_registers.json"}


def el(row, path, quote, **f):
    """One differential element; the FHIR fields (min, max, fixedUri, fixedInteger, fixedString, binding, constraint)
    carry its meaning. A constraint with expression None is a rules-layer requirement (not machine-checkable)."""
    e = {"row": row, "path": path}
    e.update(f)
    e["_quote"] = quote
    return e


STRUCTURAL = (("max", "prohibited"), ("fixedUri", "fixed"), ("fixedInteger", "fixed"), ("fixedString", "fixed"),
              ("binding", "values"), ("min", "required"))


def rule_ids(a, e):
    """The ids of the rules an element yields, as reported by the generated schemas: '<annex>-<component>-<what>' for each
    structural field (required, prohibited, fixed, values), the constraint key for each invariant. The element's own
    id (FHIR ElementDefinition.id) is the first of them."""
    segs = [s for s in e["path"].split(".") if s not in ("uriValue", "value")]
    ids = []
    for field, what in STRUCTURAL:
        if field in e and not (field == "max" and e[field] != "0") and not (field == "min" and e[field] < 1):
            rid = f"{a}-{segs[-1]}-{what}"
            if rid not in ids:
                ids.append(rid)
    for b in ("xml", "json"):                             # rules of one binding only
        ov = e.get(b) or {}
        if ov.get("min", 0) >= 1:
            ids.append(f"{a}-{segs[-1]}-{b}-required")
        if ov.get("max") == "0":
            ids.append(f"{a}-{segs[-1]}-{b}-prohibited")
    return ids + [c["key"] for c in e.get("constraint", [])]


def inv(key, human, expression=None, checkable="yes", check=None):
    """A FHIR-style invariant. expression: FHIRPath over the abstract model, or None when not machine-checkable.
    check: the same rule in a small structured form that generators translate to JSON Schema and Schematron:
      {"type": "contains", "component": M or ".", "nested": [list components], "field": F, "match": spec}
          the list M (or the element itself) has an entry (reached through the nested lists) whose F matches spec;
      {"type": "min-items", "component": M, "min": n};
      {"type": "months-after", "component": M, "base": B, "months": n}: date-time M, when present, is at most n months
          after date-time B (Schematron only: JSON Schema cannot compare two values).
    A match spec is {"equals": v} | {"startsWith": [...], "notStartsWith": [...]} | {"prefix": p, "codes": [...], "rest": bool}
    (p + one of the codes, followed by more characters when rest is true)."""
    c = {"key": key, "severity": "error", "human": human, "expression": expression, "checkable": checkable}
    if check:
        c["check"] = check
    return c


ETSI_TE = "http://uri.etsi.org/19602/ListOfTrustedEntities/"
WEB = {"startsWith": ["http://", "https://"], "notStartsWith": [ETSI_TE]}


def ms_uri(te):
    return {"prefix": f"{ETSI_TE}{te}/", "codes": EU27.split("|"), "rest": False}


def explicit_quote(a):
    """x.1 General requirements: the list is scheme explicit. That is why every profile builds on the explicit track
    (model/schemes/explicit.json), which makes the eight explicit-only components required."""
    return ("shall comply with either the scheme explicit XML schema definition" if a == "H"
            else "shall comply with the scheme explicit JSON schema definition specified in Annex A")


def rows(a):
    p, X = ANNEX[a], a
    T1, T2, T3 = f"Table {X}.1", f"Table {X}.2", f"Table {X}.3"
    out = []
    # ---------------- Table x.1: scheme information
    out += [
        el(f"{T1} LoTE version identifier", f"{LSI}.LoTEVersionIdentifier",
           'The value of the LoTEVersionIdentifier component shall be "1".', fixedInteger=1),
        el(f"{T1} LoTE sequence number", f"{LSI}.LoTESequenceNumber",
           'LoTESequenceNumber component number set to "1".',
           constraint=[inv(f"{X}-seq-1", "The first instance of the list is issued with LoTESequenceNumber 1.", None, "partly: needs the list history")]),
        el(f"{T1} LoTE type", f"{LSI}.LoTEType", E + "LoTEType/" + p["typ"], fixedUri=E + "LoTEType/" + p["typ"]),
        el(f"{T1} Status determination approach", f"{LSI}.StatusDeterminationApproach",
           E + p["sda"] + "/StatusDetn/EU", fixedUri=E + p["sda"] + "/StatusDetn/EU",
           **({"acceptAlso": [E + "WRPRCProvidersList/StatusDetn/EU"],
               "comment": "Fixed to the text's spelling 'WRPRCrovidersList' (also in Annex C.2.2). acceptAlso: the corrected "
                          "'WRPRCProvidersList' is accepted too (etsi_defects.md #13), a deliberate deviation."}
              if a == "G" else {})),
        el(f"{T1} Scheme type/community/rules", f"{LSI}.SchemeTypeCommunityRules.uriValue",
           E + p["rules"] + "/schemerules/EU", fixedUri=E + p["rules"] + "/schemerules/EU"),
        el(f"{T1} Scheme territory", f"{LSI}.SchemeTerritory",
           'The value of the SchemeTerritory component shall be "EU".', fixedString="EU"),
        el(f"{T1} Next update", LSI,
           "The maximum value between the list issue date and time and the next update shall be 6 months.",
           constraint=[inv(f"{X}-next-6m", "NextUpdate is at most 6 months after ListIssueDateTime.",
                           "NextUpdate.empty() or NextUpdate <= ListIssueDateTime + 6 months",
                           "yes: date arithmetic (Schematron; not expressible in JSON Schema)",
                           {"type": "months-after", "component": "NextUpdate", "base": "ListIssueDateTime", "months": 6})]),
    ]
    if a == "H":
        out += [
            el(f"{T1} Scheme information URI", f"{LSI}.SchemeInformationURI",
               "The SchemeInformationURI component shall contain a URI where",
               constraint=[inv("H-sch-info", "One URI where users can receive information about the list.", None, "no: content of the page")]),
            el(f"{T1} Historical information period", f"{LSI}.HistoricalInformationPeriod",
               "The HistoricalInformationPeriod component shall be present with", min=1, fixedInteger=65535),
            el(f"{T1} Pointers to other LoTEs", f"{LSI}.PointersToOtherLoTE",
               "The PointersToOtherLoTE component shall not be present.", max="0"),
        ]
    else:
        out += [
            el(f"{T1} Scheme information URI", f"{LSI}.SchemeInformationURI",
               "The SchemeInformationURI component shall contain:",
               constraint=[inv(f"{X}-sch-info", "One URI for information about the list and one where all previous instances can be "
                                                "retrieved; one URI may serve both, so the count is not enforced.", None,
                               "no: content of the pages")]),
            el(f"{T1} Historical information period", f"{LSI}.HistoricalInformationPeriod",
               "The HistoricalInformationPeriod component shall not be present", max="0"),
            el(f"{T1} Pointers to other LoTEs", f"{LSI}.PointersToOtherLoTE",
               "The PointersToOtherLoTE component shall contain a pointer to the present", min=1,
               constraint=[inv(f"{X}-ptr-self", "One pointer designates this list itself (identified here by its LoTEType qualifier).",
                               f"OtherLoTEPointer.LoTEQualifiers.LoTEQualifier.where(LoTEType = '{E}LoTEType/{p['typ']}').exists()",
                               "partly: that the location is this list itself needs the publication URL",
                               {"type": "contains", "component": ".", "nested": ["LoTEQualifiers"], "field": "LoTEType",
                                "match": {"equals": f"{E}LoTEType/{p['typ']}"}})]),
        ]
    # ---------------- Table x.2: TE information
    cc_regex = f"^http://uri\\\\.etsi\\\\.org/19602/ListOfTrustedEntities/{p['te']}/({EU27})$"
    out.append(el(f"{T2} TE name", f"{TEI}.TEName", "The value of the TEName component shall be the name of the",
                  constraint=[inv(f"{X}-te-name", "TEName is the (legal) name of the listed provider.", None, "no: needs official records")]))
    if a == "H":
        out += [
            el(f"{T2} TE trade name", f"{TEI}.TETradeName", "The TETradeName component shall include:", min=1),
            el(f"{T2} TE trade name (registration identifier)", f"{TEI}.TETradeName",
               "An official registration identifier as registered in official records,",
               constraint=[inv("H-trade-id", "Includes the official registration identifier where one exists "
                                             "(organizationIdentifier / serialNumber semantics of ETSI EN 319 412-1).", None,
                               "no: needs official records")]),
            el(f"{T2} TE trade name (law reference)", TEI, '"OJ:" for the scheme part; followed by',
               constraint=[inv("H-trade-oj", "One entry references the Union or national law: 'OJ:' + 'EU' or the ISO 3166-1 code "
                                             "of the Member State (Greece = GR, not EL: not denoted 'CC') + an identifier of the law.",
                               f"TETradeName.where(value.matches('^OJ:(EU|{EU27_ISO}).+$')).exists()", "yes",
                               {"type": "contains", "component": "TETradeName", "field": "value",
                                "match": {"prefix": "OJ:", "codes": ["EU"] + EU27_ISO.split("|"), "rest": True}})]),
            el(f"{T2} TE address", f"{TEI}.TEAddress", "contact email and contact phone number",
               constraint=[inv("H-te-tel", "The electronic address contains a contact phone number (tel: URI).",
                               "TEElectronicAddress.where(uriValue.startsWith('tel:')).exists()", "yes",
                               {"type": "contains", "component": "TEElectronicAddress", "field": "uriValue", "match": {"startsWith": ["tel:"]}})]),
            el(f"{T2} TE address (Member State URI)", f"{TEI}.TEAddress",
               '"CC" is replaced by the ISO 3166-1 [2] Alpha 2 code of the Member State which is responsible for that',
               constraint=[inv("H-te-cc", "The electronic address contains http://uri.etsi.org/19602/ListOfTrustedEntities/PubEAAProvider/CC "
                                          "for the responsible Member State ('CC' field: Greece = EL, clause 6.1.5). Placed here by "
                                          "Table H.2; the other annexes place it under TE information URI (etsi_defects.md #14).",
                               f"TEElectronicAddress.where(uriValue.matches('{cc_regex}')).exists()", "yes",
                               {"type": "contains", "component": "TEElectronicAddress", "field": "uriValue", "match": ms_uri(p["te"])})]),
            el(f"{T2} TE address (web-site)", f"{TEI}.TEAddress",
               '"CC" is replaced by the ISO 3166-1 [2] Alpha 2 code of the Member State which is responsible for that',
               constraint=[inv("H-te-web", "Because Table H.2 places the ETSI Member State URI in the electronic address, the "
                                           "web-site that clause 6.3.5.2 requires must be another http(s) URI.",
                               f"TEElectronicAddress.where(uriValue.matches('^https?://') and uriValue.startsWith('{ETSI_TE}').not()).exists()",
                               "yes", {"type": "contains", "component": "TEElectronicAddress", "field": "uriValue", "match": WEB})]),
            el(f"{T2} TE information URI", f"{TEI}.TEInformationURI", "The TEInformationURI component shall contain the URL of the", constraint=[inv("H-te-info", "The URL of the page with policies, terms and conditions.", None,
                                              "no: content of the page")]),
        ]
    else:
        trade = ("The TETradeName component shall include, where applicable," if a == "I"
                 else "The TETradeName component shall include an official registration")
        out += [
            el(f"{T2} TE trade name", f"{TEI}.TETradeName", trade,
               constraint=[inv(f"{X}-trade", "Where applicable, the registration number of the registrar." if a == "I" else
                               "The official registration identifier where one exists (organizationIdentifier / serialNumber "
                               "semantics of ETSI EN 319 412-1).", None, "no: needs official records")]),
            el(f"{T2} TE address", f"{TEI}.TEAddress", "contact email and contact phone number",
               constraint=[inv(f"{X}-te-tel", "The electronic address contains a contact phone number (tel: URI).",
                               "TEElectronicAddress.where(uriValue.startsWith('tel:')).exists()", "yes",
                               {"type": "contains", "component": "TEElectronicAddress", "field": "uriValue", "match": {"startsWith": ["tel:"]}})]),
            el(f"{T2} TE information URI", TEI, "The TEInformationURI component shall contain:",
               constraint=[
                   inv(f"{X}-te-info-count", "At least the policy page (a) and the Member State URI (c).", "TEInformationURI.count() >= 2",
                       "yes", {"type": "min-items", "component": "TEInformationURI", "min": 2}),
                   inv(f"{X}-te-info-a", "(a) An http(s) page with the provider's policies, terms and conditions.",
                       "TEInformationURI.where(uriValue.matches('^https?://') and "
                       "uriValue.startsWith('http://uri.etsi.org/19602/ListOfTrustedEntities/').not()).exists()",
                       "partly: that the page holds the policies is not checkable",
                       {"type": "contains", "component": "TEInformationURI", "field": "uriValue", "match": WEB})]),
            el(f"{T2} TE information URI (Member State URI)", TEI,
               '"CC" is replaced by the ISO 3166-1 [2] Alpha 2 code of the Member State which is responsible for that',
               constraint=[inv(f"{X}-te-cc", f"(c) http://uri.etsi.org/19602/ListOfTrustedEntities/{p['te']}/CC for the responsible "
                                             "Member State ('CC' field: Greece = EL, clause 6.1.5).",
                               f"TEInformationURI.where(uriValue.matches('{cc_regex}')).exists()", "yes",
                               {"type": "contains", "component": "TEInformationURI", "field": "uriValue", "match": ms_uri(p["te"])})]),
        ]
    if a in "DE":
        out.append(el(f"{T2} TE information extensions", f"{TEI}.TEInformationExtensions",
                      "Where applicable, the OtherAssociatedBody extension shall be used",
                      constraint=[inv(f"{X}-assoc", "Where applicable, OtherAssociatedBodies names the associated body "
                                      + ("responsible for associating the PID with the wallet unit." if a == "D"
                                         else "responsible for the provision of the wallet solution."), None, "no: 'where applicable'")]))
    # ---------------- Table x.3: service information
    svc_quote = "to the exclusion of any other"
    out.append(el(f"{T3} Service type identifier", f"{SI}.ServiceTypeIdentifier", svc_quote,
                  binding={"strength": "required", "valueSet": [E + "SvcType/" + s for s in p["svc"]]}))
    if a == "E":
        out.append(el(f"{T3} Service name", f"{SI}.ServiceName", "The value of the ServiceName component shall be the name of a wallet", constraint=[inv("E-svc-name", "The name of a wallet solution as published in the Official Journal.",
                                                     None, "no: needs the Official Journal")]))
    if a == "I":
        out.append(el(f"{T3} Service name", f"{SI}.ServiceName",
                      "The ServiceName component shall contain the name of the register for which",
                      constraint=[inv("I-svc-name", "The name of the register the registrar is responsible for.", None,
                                      "no: needs official records")]))
    if a == "H":
        out += [
            el(f"{T3} Service digital identity", f"{SI}.ServiceDigitalIdentity",
               "The ServiceDigitalIdentity component may contain one or more X.509",
               constraint=[inv("H-sdi-key", "Multiple certificates all relate to the same public key and have identical subject names.",
                               None, "partly: needs certificate parsing")]),
            el(f"{T3} Service digital identity (organizationName)", f"{SI}.ServiceDigitalIdentity",
               "The organizationName attribute present in the subject name shall strictly",
               constraint=[inv("H-sdi-org", "Each certificate's subject has organizationName, strictly matching TEName.", None,
                               "partly: needs certificate parsing")]),
            el(f"{T3} Service current status", f"{SI}.ServiceStatus", "The ServiceStatus component shall be present.", min=1),
            el(f"{T3} Service current status (values)", f"{SI}.ServiceStatus",
               "The following values may be used to the exclusion of any other:",
               binding={"strength": "required", "valueSet": [E + "PubEAAProvidersList/SvcStatus/notified",
                                                            E + "PubEAAProvidersList/SvcStatus/withdrawn"]}),
            el(f"{T3} Service current status (withdrawal)", f"{SI}.ServiceStatus", "shall have their current status set to", constraint=[inv("H-withdrawn", "When an entity is no longer a provider, all its services are set to withdrawn.",
                                              None, "no: operational process")]),
            el(f"{T3} Current status starting date and time", f"{SI}.StatusStartingTime",
               "shall not be set before the date of (re)issuance of the LoTE",
               constraint=[inv("H-start", "The starting time of a new current status is not before the (re)issuance of the list.",
                               None, "partly: needs the previous list")]),
            el(f"{T3} History information (SKI)", f"{HIST}.ServiceDigitalIdentity.X509SKI",
               "shall contain at least the X509SKI component.", min=1),
            el(f"{T3} History information (no certificate)", f"{HIST}.ServiceDigitalIdentity.X509Certificate",
               "shall not contain an X509Certificate component.", max="0"),
        ]
    else:
        cert_q = {"D": "for which the certified identity data include the name", "E": "certified identity data includes the name",
                  "F": "the information required to distinguish", "G": "the information required to distinguish",
                  "I": "for which the certified identity data include"}[a]
        cert_h = ("Where applicable, the certificates carry the information that distinguishes "
                  + ("access" if a == "F" else "registration") + " certificates from other certificates."
                  if a in "FG" else "The certificates certify the TEName and, where applicable, the TETradeName registration number.")
        out += [
            el(f"{T3} Service digital identity", f"{SI}.ServiceDigitalIdentity.X509Certificate",
               "The ServiceDigitalIdentity component shall contain one or more", min=1),
            el(f"{T3} Service digital identity (certificate content)", f"{SI}.ServiceDigitalIdentity", cert_q,
               constraint=[inv(f"{X}-sdi-content", cert_h, None, "partly: needs certificate parsing")]),
            el(f"{T3} Service current status", f"{SI}.ServiceStatus", "The ServiceStatus component shall not be used.", max="0"),
            el(f"{T3} Service current status (removal)", f"{SI}.ServiceStatus", "removed from the",
               constraint=[inv(f"{X}-removal", "An entity or service that loses its approval is removed from the list.", None,
                               "no: operational process")]),
            el(f"{T3} Current status starting date and time", f"{SI}.StatusStartingTime",
               "The StatusStartingTime component shall not be used.", max="0"),
            el(f"{T1} Historical information period (consequence)", f"{SVC}.ServiceHistory",
               "historical information is not kept in the list", max="0",
               comment="Derived: history is not kept (Table x.1), and clause 6.4.3 says ServiceHistory 'shall not be present' "
                       "when history is not retained."),
        ]
    if a == "E":
        out.append(el(f"{T3} Service information extensions", f"{SI}.ServiceInformationExtensions.ServiceUniqueIdentifier",
                      "The ServiceUniqueIdentifier extension shall be used to provide the", min=1,
                      constraint=[inv("E-sui", "The reference number of the wallet solution as published in the Official Journal.",
                                      None, "no: needs the Official Journal")]))
    if a == "I":
        out += [
            el(f"{T3} Service supply points", f"{SI}.ServiceSupplyPoints",
               "The ServiceSupplyPoint component shall contain the URI where the register is", min=1),
            el(f"{T3} Service supply points (authenticity)", f"{SI}.ServiceSupplyPoints", "shall be able to be authenticated using", constraint=[inv("I-ssp-auth", "Register data obtained there can be authenticated with a listed certificate.",
                                              None, "partly: needs the register data")]),
        ]
    sig_q = ("When a JSON binding is used to issue the Pub-EAA providers list, the list shall be signed by means of a compact"
             if a == "H" else "shall be signed by means of a compact JAdES Baseline B signature")
    json_b = {"max": "0", "from": "text", "quote": sig_q,
              "note": "In JSON the list is signed by encapsulation: a compact JAdES Baseline B signature (ETSI TS 119 182-1) "
                      "whose payload is the list; the published file is the compact JWS (header.payload.signature). The "
                      "Signature component is not used in JSON (6.8.0). WP4 currently signs JSON lists with a detached JWS in "
                      "JSON serialization next to LoTE ({\"LoTE\": ..., \"signature\": {protected, signature}}): neither compact "
                      "nor encapsulating, to be reported once a signature validator exists."}
    if a == "H":
        xml_b = {"name": "ds:Signature", "min": 1, "from": "text",
                 "quote": "When an XML binding is used to issue the Pub-EAA providers list, the Signature component shall be present with a",
                 "note": "An enveloped XAdES Baseline B signature (H.4 1), with the transforms enveloped-signature and exclusive "
                         "C14N (H.4 2-3): checked by the signature validator."}
    else:
        xml_b = {"name": "ds:Signature", "from": "wp4",
                 "reason": f"Annex {a} allows JSON only ({a}.1). WP4 also validates XML lists of this annex for their content, "
                           "with the core's XML binding of the signature: ds:Signature inside the list (enveloped) or the list "
                           "inside the signature (enveloping), 6.8.0. Such a list does not conform by format (project_decisions_vs_etsi.md #1).",
                 "note": "Optional, as in the core."}
    out.append(el(f"{X}.4 Signature", "LoTE.Signature", sig_q, json=json_b, xml=xml_b,
                  validation="not-schema-based",
                  validated_by="a signature validator (not built yet): envelope, header, signing certificate, cryptographic check",
                  constraint=[inv(f"{X}-sig", "Signed with a compact JAdES Baseline B signature (ETSI TS 119 182-1)"
                                  + (" when issued in JSON; in XML an enveloped XAdES Baseline B signature (H.4 1-4)." if a == "H" else "."),
                                  None, "yes: with a JAdES / XAdES verifier")]))
    return out


# ------------------------------------------------------------------ model navigation
class Model:
    def __init__(self, m):
        self.m = m

    def resolve(self, path):
        """Return (component, structure name) for a model path, or raise ValueError."""
        segs = path.split(".")
        if segs[0] != self.m["root"]:
            raise ValueError(f"path must start with {self.m['root']}")
        struct, component, pending_items = self.m["root"], None, None
        for s in segs[1:]:
            if pending_items is not None:                      # inside a list component: the next segment is the item
                if s != pending_items["name"]:
                    raise ValueError(f"expected list item {pending_items['name']!r}, got {s!r}")
                struct, pending_items = pending_items.get("structure"), None
                component = {"name": s, "min": 1, "max": "n", "item": True}
                continue
            if component is not None and component.get("value") in ("multilang-texts", "multilang-uris", "electronic-address") \
                    and s in ("uriValue", "value", "lang"):
                component = {"name": s, "min": 1, "max": 1, "pseudo": True}
                continue
            if component is not None and component.get("value") == "extension-list":
                ext = self.m["extensions"].get(s)
                if not ext or ext["in"] != component["name"]:
                    raise ValueError(f"{s!r} is not an extension of {component['name']}")
                component = {"name": s, "min": 0, "max": 1, "extension": True}
                continue
            if struct is None:
                raise ValueError(f"cannot descend into {component['name']!r}")
            hits = [x for x in self.m["structures"][struct]["components"] if x["name"] == s]
            if not hits:
                raise ValueError(f"{struct} has no component {s!r}")
            component = hits[0]
            struct = component.get("structure")
            pending_items = component.get("items")
        return component


def max_val(v):
    return float("inf") if v in ("n", "*") else int(v)


# ------------------------------------------------------------------ comparison with the generated JSON profile schemas
def json_node(schema, model, path):
    """Locate the JSON-schema node of a model path inside a profile schema (properties / items)."""
    node = schema["properties"]["LoTE"]
    segs = path.split(".")[1:]
    struct, pending = model.m["root"], None
    for i, s in enumerate(segs):
        if pending is not None:
            node, struct, pending = node.get("items", {}), pending.get("structure"), None
            continue
        if s in ("uriValue", "value", "lang"):
            return node.get("items", {}).get("properties", {}).get(s, {}), node.get("items", {})
        component = next((x for x in model.m["structures"].get(struct or "", {}).get("components", []) if x["name"] == s), None)
        jname = ((component or {}).get("json") or {}).get("name", s)
        parent = node
        node = node.get("properties", {}).get(jname)
        if node is None:
            return None, parent
        if component:
            struct, pending = component.get("structure"), component.get("items")
    return node, parent


def check_against_profile_schema(a, elements, model):
    schema = json.load(open(PROFILE_SCHEMAS + PROFILE_SCHEMA_FILE[a], encoding="utf-8"))
    errs = []
    for e in elements:
        node, parent = json_node(schema, model, e["path"])
        name = e["path"].split(".")[-1]
        component = model.resolve(e["path"])
        jname = (component.get("json") or {}).get("name", name)
        if e["path"] == "LoTE.Signature":
            continue
        if e.get("max") == "0" and not (node is not None and node.get("not") == {}):
            errs.append(f"{a} {e['row']}: prohibited in the overlay, not 'not: {{}}' in {PROFILE_SCHEMA_FILE[a]}")
        if e.get("min") == 1 and not component.get("item"):
            req = (parent or {}).get("required", [])
            if jname not in req and not (e["path"].endswith("ServiceUniqueIdentifier")):
                errs.append(f"{a} {e['row']}: required in the overlay, {jname!r} not in 'required' of the profile schema")
        for fk in ("fixedUri", "fixedInteger", "fixedString"):
            if fk in e:
                got = (node or {}).get("const", (node or {}).get("enum"))
                if got != e[fk] and not (isinstance(got, list) and e[fk] in got):
                    errs.append(f"{a} {e['row']}: fixed {e[fk]!r}, profile schema has {got!r}")
        if "binding" in e:
            got = (node or {}).get("enum")
            if sorted(got or []) != sorted(e["binding"]["valueSet"]):
                errs.append(f"{a} {e['row']}: value set {e['binding']['valueSet']}, profile schema has {got}")
    return errs


# ------------------------------------------------------------------ build
def main():
    model = Model(allowed(json.load(open(MODEL, encoding="utf-8"))))
    text, pos_line, page_of_line = bm.load_spec()
    order = "CDEFGHI"
    heads = {x: text.rfind(f"Annex {x} (normative)") for x in order}
    seg = {x: (heads[x], heads[order[i + 1]] if i + 1 < len(order) else len(text)) for i, x in enumerate(order)}
    errors = []

    def cite(quote, annex, where):
        s, e = seg[annex]
        k = text.find(bm.norm(quote), s, e)
        if k < 0:
            errors.append(f"{where}: quote not found in Annex {annex}: {quote!r}"); return None
        return {"quote": quote, "page": page_of_line[pos_line[k] - 1], "line": pos_line[k]}

    # Annex C
    registered = {"description": "Registered URIs of ETSI TS 119 602 V1.1.1 Annex C.2 (EU specific LoTE profiles), as value sets.",
                  "valueSets": {}}
    for vs, (clause, uris) in REGISTERED.items():
        registered["valueSets"][vs] = {"clause": clause, "codes": [{"code": u, "citation": cite(u, "C", f"{vs} {u}")} for u in uris]}
    all_registered = {c["code"] for v in registered["valueSets"].values() for c in v["codes"]}

    os.makedirs(OUT_DIR + "profiles", exist_ok=True)
    summary = []
    for a, p in ANNEX.items():
        elements = [{"id": rule_ids(a, e)[0], **e} for e in rows(a)]
        seen = {}
        for e in elements:
            for rid in rule_ids(a, e):
                if rid in seen:
                    errors.append(f"{a} {e['row']}: rule id {rid} already used by {seen[rid]}")
                seen[rid] = e["row"]
        for e in elements:
            e["citation"] = cite(e.pop("_quote"), a, f"{a} {e['row']}")
            for bnd in ("json", "xml"):                   # a binding of one syntax: where it comes from, and its quote
                ov = e.get(bnd)
                if not ov:
                    continue
                where = f"{a} {e['row']} {bnd}"
                if ov.get("from") not in ("text", "wp4", "project"):
                    errors.append(f"{where}: 'from' must be text, wp4 or project")
                if ov.get("from") in ("wp4", "project") and not ov.get("reason"):
                    errors.append(f"{where}: from {ov.get('from')!r} needs a reason")
                if ov.get("from") == "text" and not ov.get("quote"):
                    errors.append(f"{where}: from 'text' needs a quote")
                if ov.get("quote"):
                    ov["citation"] = cite(ov.pop("quote"), a, where)
            try:
                base = model.resolve(e["path"])
            except ValueError as ex:
                errors.append(f"{a} {e['row']}: path {e['path']}: {ex}"); e["_bad_path"] = True; continue
            # only narrow the base (FHIR derivation 'constraint'; TS 119 602 clause 4.7)
            if "min" in e and e["min"] < base["min"]:
                errors.append(f"{a} {e['row']}: lowers min {base['min']} -> {e['min']}")
            if "max" in e and max_val(e["max"]) > max_val(base["max"]):
                errors.append(f"{a} {e['row']}: raises max {base['max']} -> {e['max']}")
            if e.get("max") == "0" and base["min"] >= 1:
                errors.append(f"{a} {e['row']}: prohibits a mandatory component")
            if "fixedUri" in e and any(k in e["fixedUri"] for k in ("/LoTEType/", "/StatusDetn/", "/schemerules/")) \
                    and e["fixedUri"] not in all_registered:
                errors.append(f"{a} {e['row']}: fixed URI {e['fixedUri']} is not registered in Annex C")
        errors.extend(check_against_profile_schema(a, [e for e in elements if not e.get("_bad_path")], model))
        doc = {
            "id": f"lote-profile-{a}",
            "title": f"ETSI TS 119 602 V1.1.1 Annex {a} - {p['title']}",
            "derivation": "constraint",
            "baseDefinition": BASE,
            "baseCitation": cite(explicit_quote(a), a, f"{a} base definition"),
            "annex": a,
            "lotetype": E + "LoTEType/" + p["typ"],
            "differential": {"element": elements},
        }
        with open(OUT_DIR + f"profiles/{p['file']}.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False); f.write("\n")
        counts = {}                                       # rules by type, read from the FHIR fields
        for e in elements:
            for rid in rule_ids(a, e):
                what = rid.rsplit("-", 1)[-1] if rid.rsplit("-", 1)[-1] in ("required", "prohibited", "fixed", "values") else \
                    "invariant" if next(c for c in e["constraint"] if c["key"] == rid)["expression"] else "rules-layer"
                counts[what] = counts.get(what, 0) + 1
        summary.append(f"  Annex {a}: {len(elements)} elements, rules " + str(dict(sorted(counts.items()))))

    if errors:
        print("\n".join(errors)); sys.exit(1)
    with open(OUT_DIR + "registered_uris.json", "w", encoding="utf-8") as f:
        json.dump(registered, f, indent=2, ensure_ascii=False); f.write("\n")
    print("wrote model/registered_uris.json (" + ", ".join(f"{k} {len(v['codes'])}" for k, v in registered["valueSets"].items()) + ")")
    print("wrote model/profiles/:")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
