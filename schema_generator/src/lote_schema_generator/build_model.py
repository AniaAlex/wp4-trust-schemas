"""Build the abstract LoTE data model (model/lote_model.json).

sources.py says where the text defines every component (clause, text names, verbatim quotes). This script links the
model to those sources and adds what generators need in machine-readable form:
  - structures: which components a parent contains, in which order, with min/max occurrence;
  - value types: a small fixed vocabulary (uri, utc-datetime, multilang-texts, ...) defined once;
  - extensions;
  - constraints: rules across components, on the structure they constrain, in the format of the profile overlays.
Names are the names of the text. Where a binding uses another name or form, an explicit override records it.

Checks (the build fails otherwise):
  - every component source (sources.py) is used by the model;
  - every structure, value type and component reference resolves;
  - every quote added here is found verbatim in the spec (page and line computed);
  - occurrence in the model agrees with the core JSON schema, except for the planned changes listed in PLANNED;
  - every 'json' / 'xml' binding override says where it comes from: Forge (its evidence is found in the Forge schema),
    the text (its quote is found in the spec) or the project (with a reason);
  - constraint keys are unique; a constraint's check has a known type, names components of its structure and comes with
    an expression.
"""
import copy, json, os, sys

from . import spec_text as bm                                # spec index and quote normaliser
from .paths import FORGE as FORGE_DIR, HANDWRITTEN_CORE, MODEL, ROOT  # noqa: F401
from .sources import SOURCES                                 # where the text defines each component

OUT = MODEL
CORE_JSON = HANDWRITTEN_CORE                                 # the hand-written core schema, for the agreement check
FORGE = {"forge-xsd": [FORGE_DIR + "1960201_xml_schema/" + f for f in
                       ("1960201_xsd_schema.xsd", "1960201_xsd_schema_tie.xsd", "1960201_xsd_schema_sie.xsd")],
         "forge-json": [FORGE_DIR + "1960201_json_schema/1960201_json_schema.json"]}
N = "n"

# ISO 3166-1 alpha-2 codes as clause 6.1.5 a) adapts them: UK instead of GB, EL instead of GR, plus EU.
COUNTRY_A = [
    "AD", "AE", "AF", "AG", "AI", "AL", "AM", "AO", "AQ", "AR", "AS", "AT", "AU", "AW", "AX", "AZ", "BA", "BB", "BD", "BE",
    "BF", "BG", "BH", "BI", "BJ", "BL", "BM", "BN", "BO", "BQ", "BR", "BS", "BT", "BV", "BW", "BY", "BZ", "CA", "CC", "CD",
    "CF", "CG", "CH", "CI", "CK", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CW", "CX", "CY", "CZ", "DE", "DJ", "DK", "DM",
    "DO", "DZ", "EC", "EE", "EG", "EH", "EL", "ER", "ES", "ET", "EU", "FI", "FJ", "FK", "FM", "FO", "FR", "GA", "GD", "GE",
    "GF", "GG", "GH", "GI", "GL", "GM", "GN", "GP", "GQ", "GS", "GT", "GU", "GW", "GY", "HK", "HM", "HN", "HR", "HT", "HU",
    "ID", "IE", "IL", "IM", "IN", "IO", "IQ", "IR", "IS", "IT", "JE", "JM", "JO", "JP", "KE", "KG", "KH", "KI", "KM", "KN",
    "KP", "KR", "KW", "KY", "KZ", "LA", "LB", "LC", "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD", "ME",
    "MF", "MG", "MH", "MK", "ML", "MM", "MN", "MO", "MP", "MQ", "MR", "MS", "MT", "MU", "MV", "MW", "MX", "MY", "MZ", "NA",
    "NC", "NE", "NF", "NG", "NI", "NL", "NO", "NP", "NR", "NU", "NZ", "OM", "PA", "PE", "PF", "PG", "PH", "PK", "PL", "PM",
    "PN", "PR", "PS", "PT", "PW", "PY", "QA", "RE", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE", "SG", "SH", "SI",
    "SJ", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV", "SX", "SY", "SZ", "TC", "TD", "TF", "TG", "TH", "TJ", "TK",
    "TL", "TM", "TN", "TO", "TR", "TT", "TV", "TW", "TZ", "UA", "UG", "UK", "UM", "US", "UY", "UZ", "VA", "VC", "VE", "VG",
    "VI", "VN", "VU", "WF", "WS", "YE", "YT", "ZA", "ZM", "ZW",
]

# ------------------------------------------------------------------ value types (defined once, used by components)
VALUE_TYPES = {
    "integer": {"description": "Integer.", "source": "6.3.1/LoTEVersionIdentifier"},
    "positive-integer": {"description": "Integer >= 1.", "source": "6.3.2/LoTESequenceNumber"},
    "non-negative-integer": {"description": "Integer >= 0 (a duration; interpretation 1).", "source": "6.3.12/HistoricalInformationPeriod"},
    "uri": {"description": "URI per IETF RFC 3986, non-empty.", "source": "6.1.2/URI"},
    "uri-list": {"description": "Non-empty sequence of URIs.", "source": "6.3.16/DistributionPoints"},
    "utc-datetime": {"description": "ISO 8601 UTC date-time: YYYY-MM-DDThh:mm:ssZ, no fraction.", "source": "6.1.3/DateTime"},
    "plain-text": {"description": "Non-empty string without control, private-use or tag characters and without a UCS signature (Annex B.2).", "source": "B.2/PlainText"},
    "language-tag": {"description": "IETF RFC 5646 tag, primary subtag in lower case (interpretation 5).", "source": "6.1.4/MultiLangString"},
    "multilang-text": {"description": "One language-tagged plain-text string.", "source": "6.1.4/MultiLangString"},
    "multilang-uri": {"description": "One language-tagged URI (multilingual pointer).", "source": "6.1.4/MultiLangURI"},
    "multilang-texts": {"description": "Non-empty sequence of multilang-text with at least one 'en' entry.", "source": "6.1.4/English"},
    "multilang-uris": {"description": "Non-empty sequence of multilang-uri with at least one 'en' entry.", "source": "6.1.4/English"},
    "scheme-name": {"description": "multilang-texts whose values have the form 'CC:name'.", "source": "6.3.6/SchemeName"},
    "electronic-address": {"description": "multilang-uris containing a mailto: URI and a web-site (http/https) URI; tel: optional.", "source": "6.3.5.2/ElectronicAddress"},
    "country-code": {"description": "Upper-case country/territory code per 6.1.5 a), b) or c); GB and GR excluded.", "source": "6.1.5/CountryCode"},
    "country-code-a": {"description": "ISO 3166-1 alpha-2 code with UK for GB, EL for GR, plus EU (6.1.5 a only).", "source": "6.3.5.1/Country",
                       "codes": COUNTRY_A},
    "mime-type": {"description": "MIME type 'type/subtype'.", "source": "6.3.13/MimeType"},
    "base64": {"description": "Base64 (RFC 4648) without line breaks.", "source": "6.6.3.1/X509Certificate"},
    "string": {"description": "Non-empty string.", "source": "6.6.3.2/X509SubjectName"},
    "typed-uri": {"description": "URI optionally qualified by a service type URI.", "source": "6.6.7/ServiceSupplyPoints"},
    "open": {"description": "Format left open by the text; syntax-specific.", "source": "6.6.3.3/PublicKeyValue"},
    "signature": {"description": "AdES signature; syntax-specific (XAdES in XML, JAdES in JSON).", "source": "6.8/Signature"},
    "extension-list": {"description": "Non-empty sequence of extensions whose format is left open.", "source": "6.3.17/SchemeExtensions"},
}


def M(name, comp, min=0, max=1, value=None, structure=None, items=None, json=None, xml=None, note=None, quote=None,
      criticality=None, validation=None, validated_by=None):
    """A component of a structure.
    comp: source id (sources.py) that defines the component (citations, alternative names), or None with an own quote.
    value / structure: what the component holds; items: (item name, structure or value type, min items) for lists.
    json / xml: binding overrides (name, form) where a binding departs from the text name or default form."""
    m = {"name": name, "component": comp, "min": min, "max": max}
    if value: m["value"] = value
    if structure: m["structure"] = structure
    if items:
        iname, itype, imin = items
        m["items"] = {"name": iname, ("structure" if itype[0].isupper() else "value"): itype, "min": imin, "max": N}
    if criticality: m["criticality"] = criticality
    if validation: m["validation"] = validation              # "not-schema-based": checked by code, not by the schemas
    if validated_by: m["validated_by"] = validated_by
    if json: m["json"] = json
    if xml: m["xml"] = xml
    if note: m["note"] = note
    if quote: m["quote"] = quote
    return m


def S(clause, components, content="sequence", quote=None, comp=None, xml=None, json=None, note=None):
    s = {"clause": clause, "content": content, "components": components}
    for k, v in (("component", comp), ("quote", quote), ("xml", xml), ("json", json), ("note", note)):
        if v: s[k] = v
    return s


STRUCTURES = {
    "LoTE": S("5", [
        M("LoTETag", "6.2/LoTETag", 1, 1, "uri", xml={"form": "attribute", "from": "forge-xsd", "forge": 'attribute name="LOTETag"',
               "note": "Forge spells the attribute LOTETag; the text's name LoTETag is used (forge/errors.md)"},
          note="Required in both bindings (clause 5: exactly one tag). Any URI is accepted: the text registers no Tag URI "
               "value (etsi_defects.md #20). The Annex A JSON schema has no tag property; the text prevails (A.1)."),
        M("ListAndSchemeInformation", "6.3/ListAndSchemeInformation", 0, 1, structure="ListAndSchemeInformation",
          note="Optional in the core: implicit lists need not contain it, explicit lists shall (6.3.0; scheme overlays)."),
        M("TrustedEntitiesList", "6.4/TrustedEntitiesList", 0, 1, items=("TrustedEntity", "TrustedEntity", 1)),
        M("Signature", "6.8/Signature", 0, 1, "signature",
          xml={"name": "ds:Signature", "from": "forge-xsd", "forge": 'ref="ds:Signature"',
               "note": "Optional in XML: the text also allows an enveloping signature, where the list sits inside ds:Signature "
                       "(in its ds:Object) and carries no Signature component of its own. Annex H requires the enveloped form "
                       "for XML Pub-EAA lists (H.4).",
               "quote": "The AdES digital signature may either be present within the LoTE itself, when the signature format "
                        "provides for such a relationship between the signed data and the signature, or the signature itself "
                        "encapsulates the LoTE."},
          json={"max": "0", "from": "text",
                "quote": "The AdES digital signature may either be present within the LoTE itself, when the signature format provides "
                         "for such a relationship between the signed data and the signature, or the signature itself encapsulates the LoTE.",
                "note": "JAdES provides no such relationship and the Annex A JSON binding has no signature property: a JSON list is "
                        "signed by encapsulation (compact JAdES, D.4-I.4, H.4), not through the Signature component."},
          validation="not-schema-based",
          validated_by="a signature validator (not built yet): the envelope (compact JWS around a JSON list; ds:Signature in or "
                       "around an XML list), the header, the signing certificate and the cryptographic check",
          note="The schemas check only where the signature may sit; whether it is valid is checked by code, not by the model."),
    ], comp="5/LoTE", xml={"name": "ListOfTrustedEntities", "namespace": "http://uri.etsi.org/019602/v1#",
                             "from": "forge-xsd", "forge": 'element name="ListOfTrustedEntities"'}),

    "ListAndSchemeInformation": S("6.3.0", [
        M("LoTEVersionIdentifier", "6.3.1/LoTEVersionIdentifier", 1, 1, "integer"),
        M("LoTESequenceNumber", "6.3.2/LoTESequenceNumber", 1, 1, "positive-integer"),
        M("LoTEType", "6.3.3/LoTEType", 0, 1, "uri"),
        M("SchemeOperatorName", "6.3.4/SchemeOperatorName", 1, 1, "multilang-texts"),
        M("SchemeOperatorAddress", "6.3.5/SchemeOperatorAddress", 0, 1, structure="SchemeOperatorAddress"),
        M("SchemeName", "6.3.6/SchemeName", 0, 1, "scheme-name"),
        M("SchemeInformationURI", "6.3.7/SchemeInformationURI", 0, 1, "multilang-uris"),
        M("StatusDeterminationApproach", "6.3.8/StatusDeterminationApproach", 0, 1, "uri"),
        M("SchemeTypeCommunityRules", "6.3.9/SchemeTypeCommunityRules", 0, 1, "multilang-uris"),
        M("SchemeTerritory", "6.3.10/SchemeTerritory", 0, 1, "country-code"),
        M("PolicyOrLegalNotice", "6.3.11/PolicyOrLegalNotice", 0, 1, structure="PolicyOrLegalNotice"),
        M("HistoricalInformationPeriod", "6.3.12/HistoricalInformationPeriod", 0, 1, "non-negative-integer"),
        M("PointersToOtherLoTE", "6.3.13/PointersToOtherLoTE", 0, 1, items=("OtherLoTEPointer", "OtherLoTEPointer", 1)),
        M("ListIssueDateTime", "6.3.14/ListIssueDateTime", 1, 1, "utc-datetime"),
        M("NextUpdate", "6.3.15/NextUpdate", 1, 1, "utc-datetime", note="May be null: a closed LoTE.",
          json={"nullable": True, "from": "text", "quote": "available by the scheme operator or be null to indicate a closed LoTE.",
                "note": "Forge JSON allows only a date-time"},
          xml={"form": "element with optional dateTime child (empty = closed)", "from": "forge-xsd", "forge": 'name="dateTime" type="xsd:dateTime" minOccurs="0"'}),
        M("DistributionPoints", "6.3.16/DistributionPoints", 0, 1, "uri-list"),
        M("SchemeExtensions", "6.3.17/SchemeExtensions", 0, 1, "extension-list", criticality="required",
          note="Each extension shall indicate its criticality."),
    ], comp="6.3/ListAndSchemeInformation", note="Which components are required depends on implicit vs explicit scheme information: rule R-Table1."),

    "SchemeOperatorAddress": S("6.3.5.0", [
        M("PostalAddresses", "6.3.5.1/PostalAddresses", 1, 1, items=("PostalAddress", "PostalAddress", 1),
          json={"current_name": "SchemeOperatorPostalAddress", "decision": "pending: text name or Forge JSON name",
                "from": "forge-json", "forge": '"SchemeOperatorPostalAddress"'}),
        M("ElectronicAddress", "6.3.5.2/ElectronicAddress", 1, 1, "electronic-address",
          json={"current_name": "SchemeOperatorElectronicAddress", "decision": "pending: text name or Forge JSON name",
                "from": "forge-json", "forge": '"SchemeOperatorElectronicAddress"'}),
    ], comp="6.3.5/SchemeOperatorAddress"),

    "PostalAddress": S("6.3.5.1", [
        M("lang", None, 1, 1, "language-tag", xml={"form": "attribute xml:lang", "from": "forge-xsd", "forge": 'ref="xml:lang"'},
          quote="This component shall contain sequence(s) of multilingual PostalAddress components (see clause 6.1.4)."),
        M("StreetAddress", "6.3.5.1/StreetAddress", 1, 1, "plain-text"),
        M("Locality", "6.3.5.1/Locality", 0, 1, "plain-text"),
        M("StateOrProvince", "6.3.5.1/StateOrProvince", 0, 1, "plain-text"),
        M("PostalCode", "6.3.5.1/PostalCode", 0, 1, "plain-text"),
        M("Country", "6.3.5.1/Country", 1, 1, "country-code-a"),
    ], quote="The PostalAddress component shall contain the following elements:",
       note="A list of PostalAddress items needs at least one 'en' item (6.1.4)."),

    "PolicyOrLegalNotice": S("6.3.11", [
        M("LoTEPolicy", "6.3.11/PolicyOrLegalNotice", 1, N, "multilang-uri"),
        M("LoTELegalNotice", "6.3.11/LoTELegalNotice", 1, N, "multilang-text"),
    ], content="choice", comp="6.3.11/PolicyOrLegalNotice", note="Either branch needs at least one 'en' item (6.1.4)."),

    "OtherLoTEPointer": S("6.3.13", [
        M("LoTELocation", "6.3.13/LoTELocation", 1, 1, "uri"),
        M("ServiceDigitalIdentity", "6.3.13/ServiceDigitalIdentities", 1, N, structure="ServiceDigitalIdentity",
          json={"name": "ServiceDigitalIdentities", "form": "array", "from": "forge-json", "forge": '"ServiceDigitalIdentities"'},
          xml={"wrapper": "ServiceDigitalIdentities", "from": "forge-xsd", "forge": 'name="ServiceDigitalIdentities"'}),
        M("LoTEQualifiers", "6.3.13/LoTEQualifiers", 1, 1, items=("LoTEQualifier", "LoTEQualifier", 1)),
    ], quote="each OtherLoTEPointer element giving:",
       xml={"order": ["ServiceDigitalIdentity", "LoTELocation", "LoTEQualifiers"], "from": "forge-xsd",
            "forge": '<xsd:element ref="lote:ServiceDigitalIdentities" minOccurs="0"/>\n\t\t   <!--Specified in TS 119 602 v1.1.1 '
                     'clause 6.3.13 Pointers to other LoTEs item a) from Format-->\n\t\t\t<xsd:element name="LoTELocation"',
            "note": "XML element order of Forge (ServiceDigitalIdentities before LoTELocation); the text lists LoTELocation first "
                    "(6.3.13 a, b). The text decides what a list contains, the Forge binding the order of its elements."}),

    "LoTEQualifier": S("6.3.13", [
        M("LoTEType", "6.3.3/LoTEType", 1, 1, "uri"),
        M("SchemeOperatorName", "6.3.4/SchemeOperatorName", 1, 1, "multilang-texts"),
        M("SchemeTypeCommunityRules", "6.3.9/SchemeTypeCommunityRules", 0, 1, "multilang-uris"),
        M("SchemeTerritory", "6.3.10/SchemeTerritory", 1, 1, "country-code"),
        M("MimeType", "6.3.13/MimeType", 1, 1, "mime-type"),
    ], comp="6.3.13/LoTEQualifiers"),

    "TrustedEntity": S("6.4.1", [
        M("TrustedEntityInformation", None, 1, 1, structure="TrustedEntityInformation",
          quote="The TrustedEntityInformation component provides information about a trusted entity."),
        M("TrustedEntityServices", None, 1, 1, items=("TrustedEntityService", "TrustedEntityService", 1),
          quote="The TrustedEntityServices element, which shall be a sequence of TrustedEntityService elements."),
    ], comp="6.4.1/TrustedEntity"),

    "TrustedEntityService": S("6.4.3", [
        M("ServiceInformation", "6.6/ServiceInformation", 1, 1, structure="ServiceInformation"),
        M("ServiceHistory", "6.4.3/ServiceHistory", 0, 1, items=("ServiceHistoryInstance", "ServiceHistoryInstance", 1)),
    ], quote="The TrustedEntityService component provides information about a trusted entity service approved in"),

    "TrustedEntityInformation": S("6.5.0", [
        M("TEName", "6.5.1/TEName", 1, 1, "multilang-texts"),
        M("TETradeName", "6.5.2/TETradeName", 0, 1, "multilang-texts"),
        M("TEAddress", "6.5.3/TEAddress", 1, 1, structure="TEAddress"),
        M("TEInformationURI", "6.5.4/TEInformationURI", 1, 1, "multilang-uris"),
        M("TEInformationExtensions", "6.5.5/TEInformationExtensions", 0, 1, "extension-list", criticality="optional",
          note="Known extension: OtherAssociatedBodies."),
    ], quote="The TrustedEntityInformation component provides information about a trusted entity."),

    "TEAddress": S("6.5.3.0", [
        M("TEPostalAddress", "6.5.3.1/TEPostalAddress", 1, 1, items=("PostalAddress", "PostalAddress", 1)),
        M("TEElectronicAddress", "6.5.3.2/TEElectronicAddress", 1, 1, "electronic-address"),
    ], comp="6.5.3/TEAddress"),

    "AssociatedBody": S("6.5.5.1.1", [
        M("AssociatedBodyName", "6.5.5.1/AssociatedBodyName", 1, 1, "multilang-texts"),
        M("AssociatedBodyTradeName", "6.5.5.1/AssociatedBodyTradeName", 0, 1, "multilang-texts"),
        M("AssociatedBodyAddress", "6.5.5.1/AssociatedBodyAddress", 0, 1, structure="AssociatedBodyAddress"),
        M("AssociatedBodyInformationURI", "6.5.5.1/AssociatedBodyInformationURI", 0, 1, "multilang-uris"),
        M("AssociatedBodyTypeIdentifier", "6.5.5.1/AssociatedBodyTypeIdentifier", 0, 1, "uri"),
        M("AssociatedBodyInformationExtensions", "6.5.5.1/AssociatedBodyInformationExtensions", 0, 1, "extension-list",
          criticality="optional"),
    ], quote="The AssociatedBody component shall contain the below components:"),

    "AssociatedBodyAddress": S("6.5.5.1.4.0", [
        M("AssociatedBodyPostalAddress", None, 1, 1, items=("PostalAddress", "PostalAddress", 1),
          quote="The AssosciatedBodyPostalAddress element (see clause 6.5.5.1.4.1).",
          note="The text misspells the name 'AssosciatedBodyPostalAddress'."),
        M("AssociatedBodyElectronicAddress", None, 1, 1, "electronic-address",
          quote="The AssosciatedBodyElectronicAddress element (see clause 6.5.5.1.4.2).",
          note="The text misspells the name 'AssosciatedBodyElectronicAddress'."),
    ], comp="6.5.5.1/AssociatedBodyAddress"),

    "ServiceInformation": S("6.6.0", [
        M("ServiceTypeIdentifier", "6.6.1/ServiceTypeIdentifier", 0, 1, "uri"),
        M("ServiceName", "6.6.2/ServiceName", 1, 1, "multilang-texts"),
        M("ServiceDigitalIdentity", "6.6.3/ServiceDigitalIdentity", 1, 1, structure="ServiceDigitalIdentity"),
        M("ServiceStatus", "6.6.4/ServiceStatus", 0, 1, "uri"),
        M("StatusStartingTime", "6.6.5/StatusStartingTime", 0, 1, "utc-datetime"),
        M("SchemeServiceDefinitionURI", "6.6.6/SchemeServiceDefinitionURI", 0, 1, "multilang-uris"),
        M("ServiceSupplyPoints", "6.6.7/ServiceSupplyPoints", 0, 1, items=("ServiceSupplyPoint", "typed-uri", 1)),
        M("TEServiceDefinitionURI", "6.6.8/TEServiceDefinitionURI", 0, 1, "multilang-uris",
          json={"name": "ServiceDefinitionURI", "reason": "text contradicts itself (6.6.0 vs 6.6.8); Forge JSON name",
                "from": "forge-json", "forge": '"ServiceDefinitionURI"'}),
        M("ServiceInformationExtensions", "6.6.9/ServiceInformationExtensions", 0, 1, "extension-list", criticality="optional",
          note="Known extension: ServiceUniqueIdentifier."),
    ], comp="6.6/ServiceInformation"),

    "ServiceDigitalIdentity": S("6.6.3.0", [
        M("X509Certificate", "6.6.3.1/X509Certificate", 0, N, "base64", json={"name": "X509Certificates", "form": "array", "from": "forge-json", "forge": '"X509Certificates"'}),
        M("X509SubjectName", "6.6.3.2/X509SubjectName", 0, N, "string", json={"name": "X509SubjectNames", "form": "array", "from": "forge-json", "forge": '"X509SubjectNames"'}),
        M("PublicKeyValue", "6.6.3.3/PublicKeyValue", 0, N, "open", json={"name": "PublicKeyValues", "form": "array", "from": "forge-json", "forge": '"PublicKeyValues"'},
          xml={"name": "ds:KeyValue", "from": "forge-xsd", "forge": 'ref="ds:KeyValue"'}),
        M("X509SKI", "6.6.3.4/X509SKI", 0, N, "open", json={"name": "X509SKIs", "form": "array", "from": "forge-json", "forge": '"X509SKIs"'},
          xml={"type": "base64", "from": "forge-xsd", "forge": 'name="X509SKI" type="xsd:base64Binary"'}),
        M("OtherId", "6.6.3.5/OtherId", 0, N, "open", json={"name": "OtherIds", "form": "array", "from": "forge-json", "forge": '"OtherIds"'}),
    ], content="any-of", comp="6.6.3/ServiceDigitalIdentity",
       note="At least one identifier. XML wraps each identifier in a DigitalId element.", xml={"item_wrapper": "DigitalId", "from": "forge-xsd", "forge": 'name="DigitalId"'}),

    "ServiceHistoryInstance": S("6.7", [
        M("ServiceTypeIdentifier", "6.6.1/ServiceTypeIdentifier", 0, 1, "uri"),
        M("ServiceName", "6.6.2/ServiceName", 1, 1, "multilang-texts"),
        M("ServiceDigitalIdentity", "6.6.3/ServiceDigitalIdentity", 1, 1, structure="ServiceDigitalIdentity"),
        M("ServiceStatus", "6.6.4/ServiceStatus", 1, 1, "uri"),
        M("StatusStartingTime", "6.6.5/StatusStartingTime", 1, 1, "utc-datetime"),
        M("ServiceInformationExtensions", "6.6.9/ServiceInformationExtensions", 0, 1, "extension-list", criticality="optional"),
    ], comp="6.7/ServiceHistoryInstance"),
}

EXTENSIONS = {
    "OtherAssociatedBodies": {"component": "6.5.5.1/OtherAssociatedBodies", "in": "TEInformationExtensions",
                              "items": {"name": "AssociatedBody", "structure": "AssociatedBody", "min": 1, "max": N},
                              "xml": {"namespace": "http://uri.etsi.org/019602/v1/TrustedEntityExtensions", "from": "forge-xsd", "forge": 'targetNamespace="http://uri.etsi.org/019602/v1/TrustedEntityExtensions"'}},
    "ServiceUniqueIdentifier": {"component": "6.6.9.1/ServiceUniqueIdentifier", "in": "ServiceInformationExtensions",
                                "value": "uri",
                                "xml": {"namespace": "http://uri.etsi.org/019602/v1/ServiceInformationExtensions", "from": "forge-xsd", "forge": 'targetNamespace="http://uri.etsi.org/019602/v1/ServiceInformationExtensions"'}},
}


def C(key, clause, human, comp=None, quote=None, checkable="yes", check=None, expression=None, severity="error"):
    """A constraint in the format of the profile overlays (FHIR invariant: key, severity, human, expression) plus the
    project fields: clause, checkable (whether code could check it, and why not) and check (the rule in a structured form
    the generators translate). A constraint without check is a rules-layer requirement: listed, not enforced."""
    c = {"key": key, "severity": severity, "human": human, "expression": expression, "checkable": checkable,
         "clause": clause, "component": comp}
    if check: c["check"] = check
    if quote: c["quote"] = quote
    return c


EXPLICIT_IF = ["SchemeName", "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules", "PolicyOrLegalNotice"]
EXPLICIT_THEN = ["LoTEType", "SchemeOperatorAddress", "SchemeName", "SchemeInformationURI", "StatusDeterminationApproach",
                 "SchemeTypeCommunityRules", "SchemeTerritory", "PolicyOrLegalNotice"]
exists = lambda names, op: f" {op} ".join(f"{n}.exists()" for n in names)
exists_not = lambda names: " and ".join(f"{n}.empty()" for n in names)
DIRECT_NAMES = ["LoTEVersionIdentifier", "LoTESequenceNumber", "SchemeOperatorName", "ListIssueDateTime", "NextUpdate"]

# Constraints of the core model, on the structure they constrain (FHIR: an invariant sits on its context element).
CONSTRAINTS = {
    "LoTE": [
        C("R-English", "6.1.4", "Every multilingual sequence contains an entry with language 'en' (interpretation 2).",
          comp="6.1.4/English",
          expression="descendants().where(children().lang.exists()).all(children().where(lang = 'en').exists())",
          check={"type": "has-entry", "field": "lang", "match": {"equals": "en"},
                 "in": {"value_types": ["multilang-texts", "multilang-uris", "scheme-name", "electronic-address"],
                        "lists_of": ["PostalAddress"], "choices": ["PolicyOrLegalNotice"]}}),
        C("R-SchemeInfoPlacement", "6.3.0",
          "The list information is either in ListAndSchemeInformation or, in a list without that component (implicit scheme "
          "information), directly in the list: LoTEVersionIdentifier, LoTESequenceNumber, SchemeOperatorName, ListIssueDateTime "
          "and NextUpdate. Never both.",
          quote="In case the LoTE does not contain this component, information about the list itself shall be provided within "
                "the list directly through the presence of the LoTEVersionIdentifier, the LoTESequenceNumber, the "
                "SchemeOperatorName, the ListIssueDateTime, and the NextUpdate elements.",
          expression="(ListAndSchemeInformation.exists() and " + exists_not(DIRECT_NAMES) + ") or (ListAndSchemeInformation.empty() and "
                     + exists(DIRECT_NAMES, "and") + ")",
          check={"type": "either-or", "first": ["ListAndSchemeInformation"], "second": DIRECT_NAMES}),
        C("R-TrustedEntitiesPresence", "6.4.0", "TrustedEntitiesList is present exactly when one or more entities are or were approved.",
          quote="If no trusted entity is or was approved in the context of the list of trusted entities scheme, this component shall not be present.",
          checkable="no: depends on approvals outside the list"),
        C("R-Signed", "6.8.0",
          "The list is signed with an AdES digital signature at conformance level baseline B, within the list (Signature "
          "component) or encapsulating it.",
          quote="Lists of trusted entities shall be signed by means of an AdES digital signature at conformance level baseline B.",
          checkable="yes: by a signature validator (not built yet; not schema-based)"),
        C("R-SignerMatchesOperator", "6.8.0",
          "The signing certificate's C and O attributes match SchemeTerritory and one SchemeOperatorName value.",
          quote="shall match respectively the \"Scheme Territory\" and one of the \"Scheme operator name\" values.",
          checkable="yes: by a signature validator (not built yet), from the signing certificate"),
    ],
    "ListAndSchemeInformation": [
        C("R-Table1", "6.3.0",
          "If any of SchemeName, SchemeInformationURI, StatusDeterminationApproach, SchemeTypeCommunityRules, PolicyOrLegalNotice "
          "is present (explicit scheme information), then LoTEType, SchemeOperatorAddress, SchemeName, SchemeInformationURI, "
          "StatusDeterminationApproach, SchemeTypeCommunityRules, SchemeTerritory and PolicyOrLegalNotice are all required.",
          comp="6.3/Table1",
          expression=f"({exists(EXPLICIT_IF, 'or')}) implies ({exists(EXPLICIT_THEN, 'and')})",
          check={"type": "co-occurrence", "if_any_present": EXPLICIT_IF, "then_required": EXPLICIT_THEN}),
        C("R-SequenceIncrease", "6.3.2", "LoTESequenceNumber starts at 1 and increases with every release.",
          quote="The value shall be incremented at each subsequent release of the LoTE",
          checkable="partly: needs the previous list"),
        C("R-NextUpdateAfterIssue", "6.3.15", "NextUpdate (when not null) lies after ListIssueDateTime.",
          quote="The NextUpdate value shall be the Coordinated Universal Time (UTC) by which, at the latest, an update of the LoTE shall be issued.",
          checkable="yes: date comparison (not generated yet)"),
    ],
    "TrustedEntityService": [
        C("R-HistoryOrder", "6.4.4", "ServiceHistory instances are in descending order of status change date-time.",
          quote="information on the previous approval status shall be provided in descending order of status change date and time",
          checkable="yes: date comparison across history instances (not generated yet)"),
    ],
    "ServiceInformation": [
        C("R-StatusWithHistory", "6.6.0",
          "If HistoricalInformationPeriod is present with a non-zero value, every ServiceInformation contains ServiceStatus.",
          comp="6.6.0/StatusRequiredWithHistory",
          expression="%resource.ListAndSchemeInformation.HistoricalInformationPeriod >= 1 implies ServiceStatus.exists()",
          check={"type": "required-if", "if": {"path": "LoTE.ListAndSchemeInformation.HistoricalInformationPeriod", "min": 1},
                 "component": "ServiceStatus"}),
        C("R-StatusNotRetroactive", "6.6.5", "StatusStartingTime of a new current status is not before the list's (re)issuance.",
          quote="The date and time associated to the new current status of a listed service shall not be set before the date of (re)issuance of the list of trusted entities",
          checkable="partly: needs the previous list"),
    ],
    "ServiceDigitalIdentity": [
        C("R-PKIIdentity", "6.6.3.0",
          "A PKI-based service identity contains an X509Certificate or an X509SKI (6.6.0 says: at least one X509Certificate).",
          quote="When using PKI public-key technology, this component shall contain at least: one X509Certificate element or an X509SKI element.",
          checkable="partly: whether PKI is used is not stated in the list"),
    ],
}
CHECK_TYPES = ("co-occurrence", "required-if", "has-entry", "either-or")

# Clause 6.3.0: "In case the LoTE does not contain this component, information about the list itself shall be provided
# within the list directly" through these five elements. The core model therefore also allows them directly in LoTE, after
# ListAndSchemeInformation; constraint R-SchemeInfoPlacement allows one placement or the other, never both.
DIRECT = DIRECT_NAMES
_lsi = {c["name"]: c for c in STRUCTURES["ListAndSchemeInformation"]["components"]}
_at = next(i for i, c in enumerate(STRUCTURES["LoTE"]["components"]) if c["name"] == "ListAndSchemeInformation") + 1
STRUCTURES["LoTE"]["components"][_at:_at] = [
    {**copy.deepcopy(_lsi[n]), "min": 0, "note": " ".join(x for x in [_lsi[n].get("note"), "Direct placement: only in a list without "
     "ListAndSchemeInformation (implicit scheme information, 6.3.0)."] if x)} for n in DIRECT]

# Differences from the current hand-written core JSON schema that are intended.
PLANNED = {("SchemeOperatorAddress", "PostalAddresses"), ("SchemeOperatorAddress", "ElectronicAddress"), ("LoTE", "Signature"),
           ("LoTE", "ListAndSchemeInformation")} | {("LoTE", n) for n in DIRECT}   # optional component, direct placement


# ------------------------------------------------------------------ build and verify
def main():
    text, pos_line, page_of_line = bm.load_spec()
    errors, used = [], set()

    def cite(quote, where):
        k = text.find(bm.norm(quote))
        if k < 0:
            errors.append(f"{where}: quote not found in spec: {quote!r}"); return None
        return {"quote": quote, "page": page_of_line[pos_line[k] - 1], "line": pos_line[k]}

    def resolve_component(comp, where):
        if comp is None:
            return None
        if comp not in SOURCES:
            errors.append(f"{where}: unknown source id {comp!r} (sources.py)"); return None
        used.add(comp)
        src = SOURCES[comp]
        cites = []
        for q in src["quotes"]:                          # verified against the text; page and line computed
            k = text.find(bm.norm(q))
            if k < 0:
                errors.append(f"{where}: source {comp} quote not found in spec: {q!r}"); continue
            c = {"quote": q}
            if text.find(bm.norm(q), k + 1) >= 0:
                c["ambiguous"] = True                    # the sentence appears more than once; the first occurrence is cited
            c.update(line=pos_line[k], page=page_of_line[pos_line[k] - 1])
            cites.append(c)
        return {"id": comp, "clause": src["clause"], "text_names": src["names"], "citations": cites}

    out_structs = {}
    for sname, s in STRUCTURES.items():
        so = {k: v for k, v in s.items() if k not in ("components", "component", "quote")}
        so["source"] = resolve_component(s.get("component"), sname) if s.get("component") else None
        if s.get("quote"):
            so["citation"] = cite(s["quote"], sname)
        if not so["source"] and not so.get("citation"):
            errors.append(f"{sname}: no component and no quote")
        components = []
        for m in s["components"]:
            where = f"{sname}.{m['name']}"
            mo = {k: v for k, v in m.items() if k not in ("component", "quote")}
            mo["source"] = resolve_component(m["component"], where)
            if m.get("quote"):
                mo["citation"] = cite(m["quote"], where)
            if not mo["source"] and not mo.get("citation"):
                errors.append(f"{where}: no component and no quote")
            for ref in [m.get("structure"), (m.get("items") or {}).get("structure")]:
                if ref and ref not in STRUCTURES:
                    errors.append(f"{where}: unknown structure {ref!r}")
            for ref in [m.get("value"), (m.get("items") or {}).get("value")]:
                if ref and ref not in VALUE_TYPES:
                    errors.append(f"{where}: unknown value type {ref!r}")
            if m.get("validation") not in (None, "not-schema-based"):
                errors.append(f"{where}: unknown validation {m['validation']!r}")
            if m.get("validation") == "not-schema-based" and not m.get("validated_by"):
                errors.append(f"{where}: a not-schema-based component needs 'validated_by'")
            if not (m.get("value") or m.get("structure") or m.get("items")):
                errors.append(f"{where}: no value, structure or items")
            components.append(mo)
        so["components"] = components
        out_structs[sname] = so

    out_ext = {}
    for ename, e in EXTENSIONS.items():
        eo = dict(e); eo["source"] = resolve_component(e["component"], ename); del eo["component"]
        out_ext[ename] = eo
    keys = set()
    for sname, cs in CONSTRAINTS.items():
        if sname not in out_structs:
            errors.append(f"constraints on unknown structure {sname!r}"); continue
        out_cs = []
        for c in cs:
            where = f"{sname} constraint {c['key']}"
            if c["key"] in keys:
                errors.append(f"{where}: duplicate key")
            keys.add(c["key"])
            co = {k: v for k, v in c.items() if k not in ("component", "quote")}
            co["source"] = resolve_component(c["component"], where) if c["component"] else None
            if c.get("quote"):
                co["citation"] = cite(c["quote"], where)
            if not co["source"] and not co.get("citation"):
                errors.append(f"{where}: no component and no quote")
            ck = c.get("check")
            if ck:
                names = {x["name"] for x in out_structs[sname]["components"]}
                if ck["type"] not in CHECK_TYPES:
                    errors.append(f"{where}: unknown check type {ck['type']!r}")
                elif ck["type"] == "co-occurrence" and not set(ck["if_any_present"] + ck["then_required"]) <= names:
                    errors.append(f"{where}: co-occurrence names not in {sname}")
                elif ck["type"] == "required-if" and ck["component"] not in names:
                    errors.append(f"{where}: {ck['component']} not in {sname}")
                elif ck["type"] == "either-or" and not set(ck["first"] + ck["second"]) <= names:
                    errors.append(f"{where}: either-or names not in {sname}")
                elif ck["type"] == "has-entry" and not set(ck["in"]["value_types"]) <= set(VALUE_TYPES):
                    errors.append(f"{where}: unknown value types in 'in'")
                if not c.get("expression"):
                    errors.append(f"{where}: a checked constraint needs an expression")
            out_cs.append(co)
        out_structs[sname]["constraint"] = out_cs
    out_types = {}
    for t, v in VALUE_TYPES.items():
        out_types[t] = {"description": v["description"], **{k: x for k, x in v.items() if k not in ("description", "source")},
                        "source": resolve_component(v["source"], f"value type {t}")}

    # where each binding override comes from: Forge (the evidence must still be in the Forge file), the text (the quote is
    # verified and cited) or the project (a reason is required)
    forge_text = {k: "".join(open(f, encoding="utf-8").read() for f in fs) for k, fs in FORGE.items()}
    overrides = [(f"{n}.{b}", s[b]) for n, s in out_structs.items() for b in ("json", "xml") if s.get(b)]
    overrides += [(f"{n}.{c['name']}.{b}", c[b]) for n, s in out_structs.items() for c in s["components"]
                  for b in ("json", "xml") if c.get(b)]
    overrides += [(f"extension {n}.{b}", e[b]) for n, e in out_ext.items() for b in ("json", "xml") if e.get(b)]
    for n, st in out_structs.items():                      # an XML order lists exactly the structure's components
        order = (st.get("xml") or {}).get("order")
        if order and sorted(order) != sorted(c["name"] for c in st["components"]):
            errors.append(f"{n}.xml.order does not list exactly its components: {order}")
    for where, ov in overrides:
        src = ov.get("from")
        if src in FORGE:
            if not ov.get("forge") or ov["forge"] not in forge_text[src]:
                errors.append(f"{where}: Forge evidence {ov.get('forge')!r} not found in the {src} files")
        elif src == "text":
            if not ov.get("quote"):
                errors.append(f"{where}: from 'text' needs a quote")
            else:
                ov["citation"] = cite(ov.pop("quote"), where)
        elif src == "project":
            if not ov.get("reason"):
                errors.append(f"{where}: from 'project' needs a reason")
        else:
            errors.append(f"{where}: binding override without 'from' (forge-xsd, forge-json, text or project)")
        if ov.get("quote"):                               # a supporting quote on any override is verified and cited too
            ov["citation"] = cite(ov.pop("quote"), where)

    missing = [i for i, r in SOURCES.items() if r["kind"] == "component" and i not in used]
    errors += [f"source component not used by the model: {i}" for i in missing]
    errors += check_against_core_json()
    if errors:
        print("\n".join(errors)); sys.exit(1)

    model = {
        "model": "ETSI TS 119 602 V1.1.1 (2025-11) - List of Trusted Entities, abstract data model",
        "generated_by": "lote_schema_generator/build_model.py, citations from lote_schema_generator/sources.py",
        "conventions": {
            "names": "Component names are the names of the text. 'json' / 'xml' entries record where a binding uses another name or form.",
            "validation": "A component with 'validation': 'not-schema-based' is only placed by the model (where it may sit, how "
                          "often); its content is checked by code ('validated_by'), not by the generated schemas.",
            "binding_source": "Every 'json' / 'xml' entry says where it comes from: 'from': 'forge-xsd' / 'forge-json' with 'forge' = the text "
                              "found in the Forge schema (checked at build time), 'text' with a verified 'citation', or 'project' with a 'reason'.",
            "occurrence": "min/max per component; max 'n' = unbounded. 'items' describes a list component: the component itself holds a non-empty sequence of items.",
            "content": "sequence: components in order; choice: exactly one component; any-of: at least one component.",
            "tie_break": "Where the text contradicts itself, JSON follows the Forge JSON name and XML the Forge XML name.",
            "constraints": "Rules across components are 'constraint' entries on the structure they constrain, in the format of the "
                           "profile overlays (FHIR invariant: key, severity, human, expression; plus clause, checkable and check). "
                           "A constraint with a 'check' is enforced by the generated schemas; one without is a rules-layer requirement.",
        },
        "root": "LoTE",
        "value_types": out_types,
        "structures": out_structs,
        "extensions": out_ext,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False); f.write("\n")
    n_components = sum(len(s["components"]) for s in out_structs.values())
    n_constraints = sum(len(s.get("constraint", [])) for s in out_structs.values())
    print(f"wrote {OUT}: {len(out_structs)} structures, {n_components} components, {len(out_types)} value types, "
          f"{len(out_ext)} extensions, {n_constraints} constraints; covers all "
          f"{sum(r['kind'] == 'component' for r in SOURCES.values())} source components and {len(used)} sources in total")


def check_against_core_json():
    """Required/optional of every component, as the JSON binding names it, must match the core JSON schema."""
    core = json.load(open(CORE_JSON, encoding="utf-8"))
    defs = core["$defs"]
    json_def = {"LoTE": "LoTE", "PostalAddress": "PostalAddress", "OtherLoTEPointer": "OtherLoTEPointer",
                "LoTEQualifier": "LoTEQualifier", "AssociatedBody": "AssociatedBody", "TEAddress": "TEAddress",
                "AssociatedBodyAddress": None}
    errs = []
    for sname, s in STRUCTURES.items():
        dname = json_def.get(sname, sname)
        d = defs.get(dname) if dname else None
        if d is None:
            if sname == "AssociatedBodyAddress":                 # inline object in the core schema
                d = defs["AssociatedBody"]["properties"]["AssociatedBodyAddress"]
            elif sname in ("TrustedEntityService",):
                d = defs["TrustedEntityService"]
            else:
                errs.append(f"core JSON has no definition for structure {sname}"); continue
        props, req = d.get("properties", {}), set(d.get("required", []))
        if s["content"] in ("choice", "any-of"):
            continue                                             # branches, not required/optional components
        for m in s["components"]:
            jname = (m.get("json") or {}).get("name", m["name"])
            if (sname, m["name"]) in PLANNED:
                continue
            if m["name"] == "lang" or (m.get("xml") or {}).get("form") == "attribute xml:lang":
                jname = "lang"
            jmin = (m.get("json") or {}).get("min", m["min"])
            if jname not in props:
                errs.append(f"core JSON {dname}: no property {jname!r} (model {sname}.{m['name']})"); continue
            if (jname in req) != (jmin >= 1):
                errs.append(f"core JSON {dname}.{jname}: {'required' if jname in req else 'optional'}, model says min {jmin}")
    return errs


if __name__ == "__main__":
    main()
