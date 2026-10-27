"""lote-validate on sample lists (tests/data, written from the generator's test builders): the verdict, the track, the
rules that fail, and the citation each failure carries."""
import filecmp
import re
import json
from pathlib import Path

import pytest

from lote_schema_validator import Report, validate
from lote_schema_validator.validate import SCHEMAS, ProfileError, main

DATA = Path(__file__).parent / "data"
GENERATOR = Path(__file__).resolve().parents[2] / "schema_generator"

# Every list is validated as a scheme explicit list (the implicit track is frozen and not published). The implicit-shaped
# samples fail with the Table 1 rules: the five list elements may not sit directly in the list, and an explicit list
# needs ListAndSchemeInformation and the scheme information.
DIRECT = {"EXP-LoTEVersionIdentifier-prohibited", "EXP-LoTESequenceNumber-prohibited", "EXP-SchemeOperatorName-prohibited",
          "EXP-ListIssueDateTime-prohibited", "EXP-NextUpdate-prohibited"}
SCHEME_INFO = {"EXP-LoTEType-required", "EXP-SchemeOperatorAddress-required", "EXP-SchemeInformationURI-required",
               "EXP-StatusDeterminationApproach-required", "EXP-SchemeTypeCommunityRules-required",
               "EXP-SchemeTerritory-required", "EXP-PolicyOrLegalNotice-required"}

# (file, profile, track, expected track, the rules that fail: empty when the list is valid). profile False: the track
# only; the explicit_list samples declare the PID LoTEType, so without it they would be checked against Annex D.
CASES = [
    ("D_pid_providers.json", "D", None, "explicit", set()),
    ("D_pid_providers.xml", "D", None, "explicit", set()),
    ("H_pub_eaa_providers.xml", "H", None, "explicit", set()),
    ("explicit_list.json", False, None, "explicit", set()),
    ("explicit_list.xml", False, None, "explicit", set()),
    ("implicit_list_direct.json", False, None, "explicit", DIRECT | {"EXP-ListAndSchemeInformation-required"}),
    ("implicit_list_direct.xml", False, None, "explicit", DIRECT),      # XSD stops at the first unexpected element
    ("D_with_json_signature.json", "D", None, "explicit", {"LoTE-Signature-not-in-json", "D-Signature-json-prohibited"}),
    ("H_without_signature.xml", "H", None, "explicit", {"H-Signature-xml-required"}),                      # H.4
    ("implicit_list_with_scheme_name.json", False, "explicit", "explicit", SCHEME_INFO),                   # Table 1
]


@pytest.mark.parametrize("name,profile,track,want_track,want_rules", CASES, ids=[c[0] for c in CASES])
def test_validate(name, profile, track, want_track, want_rules):
    r = validate(DATA / name, profile=profile, track=track)
    assert isinstance(r, Report)
    assert r.track == want_track
    assert {f.rule for f in r.findings} == want_rules, [f"{f.layer} {f.rule}: {f.message}" for f in r.findings]
    assert r.valid == (not want_rules)


@pytest.mark.parametrize("name,profile", [("D_with_json_signature.json", "D"), ("H_without_signature.xml", "H"),
                                          ("implicit_list_with_scheme_name.json", False), ("implicit_list_direct.json", False)])
def test_every_failure_cites_the_text(name, profile):
    r = validate(DATA / name, profile=profile)
    for f in r.findings:
        assert f.source.get("ref") and f.source.get("page") and f.source.get("quote"), f


def test_citation_of_h4():
    (f,) = validate(DATA / "H_without_signature.xml", profile="H").findings
    assert f.source["ref"] == "H.4 Signature" and f.source["page"] == 66
    assert "the Signature component shall be present" in f.source["quote"]


def _xml(tmp_path, changes):
    text = (DATA / "explicit_list.xml").read_text(encoding="utf-8")
    for old, new in changes:
        assert old in text
        text = text.replace(old, new, 1)
    f = tmp_path / "list.xml"
    f.write_text(text, encoding="utf-8")
    return f


def _json(tmp_path, change):
    doc = json.loads((DATA / "explicit_list.json").read_text(encoding="utf-8"))
    change(doc)
    f = tmp_path / "list.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


NEXT_UPDATE = "<NextUpdate><dateTime>2026-06-01T00:00:00Z</dateTime></NextUpdate>"

# (what the list breaks, [(old, new)] in explicit_list.xml, the rule id, the clause or row the finding cites)
XML_CASES = [
    ("wrong root", [('<ListOfTrustedEntities xmlns="http://uri.etsi.org/019602/v1#"', '<TrustedEntitiesList'),
                    ("</ListOfTrustedEntities>", "</TrustedEntitiesList>")], "LoTE-root", "Clause 5"),
    ("attribute the spec does not define", [('<ListOfTrustedEntities ', '<ListOfTrustedEntities Version="x" ')],
     "LoTE-Version-not-allowed", "Clause 5"),
    ("element name not in the spec", [("<Country>BE</Country>", "<CountryName>BE</CountryName>")],
     "PostalAddress-Country-required", "Clause 6.3.5.1"),
    ("track forbids it here (max 0)", [("</ListAndSchemeInformation>", "</ListAndSchemeInformation>" + NEXT_UPDATE)],
     "EXP-NextUpdate-prohibited", "6.3.0 List information placed directly in the list"),
    ("allowed elsewhere, not here", [("<Country>BE</Country>", "<Country>BE</Country>" + NEXT_UPDATE)],
     "PostalAddress-NextUpdate-not-allowed", "Clause 6.3.5.1"),
    ("track requires it", [("<SchemeName><Name xml:lang=\"en\">EU:Example list</Name></SchemeName>", "")],
     "EXP-SchemeName-required", "Table 1 SchemeName"),
    ("empty value in a helper element", [('<URI xml:lang="en">https://op.eu</URI>', '<URI xml:lang="en"></URI>')],
     "SchemeOperatorAddress-ElectronicAddress-value", "Clause 6.3.5.2"),
]


@pytest.mark.parametrize("what,change,rule,ref", XML_CASES, ids=[c[0] for c in XML_CASES])
def test_xsd_errors_carry_model_ids(tmp_path, what, change, rule, ref):
    (f,) = [f for f in validate(_xml(tmp_path, change), track="explicit").findings if f.layer == "xsd"]
    assert (f.rule, f.source["ref"]) == (rule, ref), f
    assert f.source["quote"] and f.source["page"]


def test_xml_id_on_the_root_is_accepted(tmp_path):
    """Id is not in the text, but Forge allows it (project_decisions_vs_etsi.md #5)."""
    f = _xml(tmp_path, [('<ListOfTrustedEntities ', '<ListOfTrustedEntities Id="lote" ')])
    assert validate(f, profile=False).valid


def test_wrong_root_does_not_hide_the_rest(tmp_path):
    """A root that is not the LoTE root, around LoTE content: the wrong root is reported, and the rest of the list is
    still checked (XSD and profile Schematron), with locations as the file has them."""
    f = _xml(tmp_path, [('<ListOfTrustedEntities xmlns="http://uri.etsi.org/019602/v1#"',
                         '<lote:TrustedEntitiesList xmlns:lote="http://uri.etsi.org/019602/v1#" xmlns="http://uri.etsi.org/019602/v1#"'),
                        ("</ListOfTrustedEntities>", "</lote:TrustedEntitiesList>"),
                        ("<Country>BE</Country>", "<CountryName>BE</CountryName>")])
    r = validate(f, profile="D")
    rules = {x.rule for x in r.findings}
    assert r.root_corrected and {"LoTE-root", "PostalAddress-Country-required"} <= rules
    assert any(x.layer == "profile-D" for x in r.findings)               # Annex D rules ran under the wrong root
    assert all(x.location.startswith("/lote:TrustedEntitiesList") for x in r.findings), [x.location for x in r.findings]


def test_root_not_corrected_when_content_is_not_a_lote(tmp_path):
    f = tmp_path / "other.xml"
    f.write_text('<Invoice><Total>1</Total></Invoice>', encoding="utf-8")
    r = validate(f, profile=False, track="explicit")
    assert not r.root_corrected and [x.rule for x in r.findings if x.layer == "xsd"] == ["LoTE-root"]


def _drop_scheme_name(d):
    del d["LoTE"]["ListAndSchemeInformation"]["SchemeName"]


def _next_update_at_root(d):
    d["LoTE"]["NextUpdate"] = d["LoTE"]["ListAndSchemeInformation"]["NextUpdate"]


def _extra_in_postal_address(d):
    d["LoTE"]["ListAndSchemeInformation"]["SchemeOperatorAddress"]["SchemeOperatorPostalAddress"][0]["CountryName"] = "BE"


JSON_CASES = [
    ("wrong root", lambda d: d.update({"ListOfTrustedEntities": d.pop("LoTE")}), {"LoTE-root"}, "Clause 5"),
    ("track forbids it here (max 0)", _next_update_at_root, {"EXP-NextUpdate-prohibited"},
     "6.3.0 List information placed directly in the list"),
    ("track requires it", _drop_scheme_name, {"EXP-SchemeName-required"}, "Table 1 SchemeName"),
    ("property name not in the spec", _extra_in_postal_address, {"PostalAddress-CountryName-not-allowed"}, "Clause 6.3.5.1"),
]


@pytest.mark.parametrize("what,change,rules,ref", JSON_CASES, ids=[c[0] for c in JSON_CASES])
def test_json_schema_errors_carry_model_ids(tmp_path, what, change, rules, ref):
    findings = validate(_json(tmp_path, change), profile=False, track="explicit").findings      # the track's rules only
    assert {f.rule for f in findings} == rules, [f"{f.rule}: {f.message}" for f in findings]
    assert all(f.source["ref"] == ref and f.source["quote"] for f in findings), findings


def test_only_the_explicit_track():
    with pytest.raises(ValueError):
        validate(DATA / "explicit_list.json", track="implicit")
    with pytest.raises(SystemExit):                                     # --implicit is no longer an option
        main([str(DATA / "explicit_list.json"), "--implicit"])
    assert main([str(DATA / "D_pid_providers.json"), "--explicit"]) == 0


def test_cli(capsys):
    assert main([str(DATA / "D_pid_providers.json"), "--profile", "D"]) == 0
    out = capsys.readouterr().out
    assert "profile D (from its LoTEType" in out and out.splitlines()[0].endswith("- valid")
    assert main([str(DATA / "H_without_signature.xml"), "--profile", "H", "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["profile"] == "H" and out["findings"][0]["rule"] == "H-Signature-xml-required"


@pytest.mark.skipif(not GENERATOR.is_dir(), reason="the generator project is not next to this one")
@pytest.mark.parametrize("published,source", [("explicit", "explicit")])
def test_published_schemas_are_current(published, source):
    """The package data is the generator's latest output: run `lote-schemas publish` if this fails. The generator's
    documentation (*.md) is not published."""
    left, right = Path(SCHEMAS) / published, GENERATOR / source
    if right.is_file():
        assert left.is_file() and filecmp.cmp(left, right, shallow=False), f"{published} differs from the generator's {source}"
        return
    stale = []

    def walk(c, rel=""):
        stale.extend(rel + n for n in c.left_only + c.right_only + c.diff_files if not n.endswith(".md"))
        for n, s in c.subdirs.items():
            walk(s, rel + n + "/")
    walk(filecmp.dircmp(left, right))
    assert not stale, f"published {published} differs from the generator's {source}: {stale}"


# ------------------------------------------------------------------ profile: chosen from the list's LoTEType
@pytest.mark.parametrize("name,annex", [("D_pid_providers.json", "D"), ("D_pid_providers.xml", "D"),
                                        ("H_pub_eaa_providers.xml", "H")])
def test_profile_from_lote_type(name, annex):
    r = validate(DATA / name)
    assert r.profile == annex and r.declared_profile == annex and r.valid and not r.warnings
    assert r.profile_reason.startswith("from its LoTEType http://uri.etsi.org/19602/LoTEType/")


LOTL = "http://uri.etsi.org/19602/LoTLType/EUListOfTrustedLists"


def _retyped(tmp_path, name, lote_type):
    """A copy of a sample list with another LoTEType."""
    text = (DATA / name).read_text(encoding="utf-8")
    old = "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"
    assert old in text
    f = tmp_path / name
    f.write_text(text.replace(old, lote_type), encoding="utf-8")
    return f


def test_wrong_profile_is_replaced_by_the_declared_one():
    r = validate(DATA / "D_pid_providers.json", profile="E")
    assert r.profile == "D" and r.declared_profile == "D" and r.valid
    (w,) = r.warnings
    assert w.startswith("--profile E ignored:") and "Annex D" in w


def test_right_profile_does_not_warn():
    assert not validate(DATA / "H_without_signature.xml", profile="H").warnings


@pytest.mark.parametrize("name", ["explicit_list.json", "explicit_list.xml"])
def test_list_of_trusted_lists_is_profile_lotl(tmp_path, name):
    """No annex covers the LoTL (a WP4 LoTEType, project_decisions_vs_etsi.md #3): profile LoTL, the explicit track only."""
    f = _retyped(tmp_path, name, LOTL)
    for given in (None, "LoTL"):                                          # chosen from the LoTEType, or by --lotl
        r = validate(f, profile=given)
        assert r.profile == r.declared_profile == "LoTL" and r.valid and not r.warnings
        assert r.profile_reason == f"from its LoTEType {LOTL}"
    r = validate(f, profile="D")                                          # a --profile is overridden, with a warning
    assert r.profile == "LoTL" and r.warnings[0].startswith("--profile D ignored:")


def test_lotl_flag_behaves_as_a_profile(tmp_path):
    r = validate(DATA / "D_pid_providers.json", profile="LoTL")           # the list declares Annex D: D is used
    assert r.profile == "D" and r.valid and r.warnings[0].startswith("--lotl ignored:")
    r = validate(_retyped(tmp_path, "D_pid_providers.json", LOTL), profile="LoTL")     # declared LoTL: no warning
    assert r.profile == "LoTL" and not r.warnings


@pytest.mark.parametrize("lote_type", ["http://uri.etsi.org/19602/LoTEType/EUPIDProviderList",       # typo
                                       "https://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"])     # not exact
def test_unknown_lote_type_is_an_invalid_profile(tmp_path, lote_type):
    """Not exactly one of the seven LoTEType URIs: no profile, whatever the flags."""
    f = _retyped(tmp_path, "D_pid_providers.json", lote_type)
    for given in (None, "D", "LoTL"):
        with pytest.raises(ProfileError, match="invalid profile") as e:
            validate(f, profile=given)
        assert lote_type in str(e.value) and LOTL in str(e.value)
        assert "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList" in str(e.value)


def test_no_lote_type_is_an_invalid_profile():
    for given in (None, "D", "LoTL"):
        with pytest.raises(ProfileError, match="invalid profile: the list has no LoTEType"):
            validate(DATA / "implicit_list_direct.json", profile=given)


def test_cli_profile_flags(tmp_path, capsys):
    assert main([str(DATA / "D_pid_providers.json"), "--profile", "E"]) == 0     # D is used: the list is valid
    out = capsys.readouterr().out
    assert "profile D (from its LoTEType" in out and out.splitlines()[1].startswith("WARNING: --profile E ignored")
    with pytest.raises(SystemExit) as e:                                  # no profile can be chosen: usage error
        main([str(_retyped(tmp_path, "D_pid_providers.json", "http://example.org/x"))])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert 'invalid profile: the list\'s LoTEType is "http://example.org/x". The profiles must be:' in err and LOTL in err
    with pytest.raises(SystemExit):                                       # --no-profile no longer exists
        main([str(DATA / "D_pid_providers.json"), "--no-profile"])
    with pytest.raises(SystemExit) as e:                                  # --profile and --lotl exclude each other
        main([str(DATA / "D_pid_providers.json"), "--lotl", "--profile", "D"])
    assert e.value.code == 2
    assert main([str(DATA / "D_pid_providers.json"), "--lotl"]) == 0      # overridden by the declared Annex D


# ------------------------------------------------------------------ XML signature structure: H.4 2)-3), and WP4 for D-G, I
SIG = (DATA / "H_pub_eaa_providers.xml").read_text(encoding="utf-8")
SIG = SIG[SIG.index("<ds:Signature"):SIG.index("</ds:Signature>") + len("</ds:Signature>")]
EXC = "http://www.w3.org/2001/10/xml-exc-c14n#"
SIG_CASES = [
    ("reference by Id", [('URI=""', 'URI="#list"')], "sig-ref-uri"),
    ("one transform", [('<ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>', "")], "sig-transforms"),
    ("inclusive canonicalization", [(f'<ds:CanonicalizationMethod Algorithm="{EXC}"/>',
                                     '<ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>')],
     "sig-c14n"),
]


def _signed(tmp_path, name, changes, add_signature=False):
    text = (DATA / name).read_text(encoding="utf-8")
    if add_signature:
        text = text.replace("</ListOfTrustedEntities>", SIG + "</ListOfTrustedEntities>")
    for old, new in changes:
        assert old in text
        text = text.replace(old, new, 1)
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return f


@pytest.mark.parametrize("what,changes,rule", SIG_CASES, ids=[c[0] for c in SIG_CASES])
def test_h_signature_structure(tmp_path, what, changes, rule):
    """H.4 2)-3) is the text's rule for XML Pub-EAA lists: one finding per mistake, citing H.4."""
    (f,) = validate(_signed(tmp_path, "H_pub_eaa_providers.xml", changes)).findings
    assert f.rule == f"H-{rule}" and f.location.endswith("/ds:Signature")
    assert f.source["ref"] == "H.4 Signature" and "from" not in f.source and not f.message.startswith("WP4 rule")


@pytest.mark.parametrize("what,changes,rule", SIG_CASES, ids=[c[0] for c in SIG_CASES])
def test_wp4_signature_structure_in_d(tmp_path, what, changes, rule):
    """Annex D defines no XML signature: the same checks apply as a WP4 rule, still citing H.4."""
    (f,) = validate(_signed(tmp_path, "D_pid_providers.xml", changes, add_signature=True)).findings
    assert f.rule == f"D-{rule}" and f.source["ref"] == "H.4 Signature" and f.source["from"] == "wp4"
    assert f.message.startswith("WP4 rule (project_decisions_vs_etsi.md #2): ")


def test_d_xml_signature_stays_optional_and_conforming_one_passes(tmp_path):
    assert validate(DATA / "D_pid_providers.xml").valid                                   # no ds:Signature: no finding
    assert validate(_signed(tmp_path, "D_pid_providers.xml", [], add_signature=True)).valid  # the H.4 form passes


# ------------------------------------------------------------------ not checked: the rules-layer requirements
def test_not_checked_lists_the_rules_layer_with_their_fields():
    r = validate(DATA / "D_pid_providers.json")
    nc = {n.rule: n for n in r.not_checked}
    assert {"D-te-name", "D-removal", "R-SequenceIncrease", "R-Signed", "D-sig"} <= set(nc)
    assert not {"R-English", "R-StatusWithHistory"} & set(nc)            # they have a check
    n = nc["D-te-name"]
    assert (n.status, n.reason) == ("no", "official-records") and n.reason_text and n.source["quote"]
    assert n.occurrences == [{"location": "/LoTE/TrustedEntitiesList/0/TrustedEntityInformation/TEName",
                              "value": "en: Provider BE"}]
    assert not nc["R-Signed"].in_json                                   # a JSON list is signed by encapsulation
    assert not nc["D-removal"].occurrences                              # the sample has no ServiceStatus
    assert (nc["D-ptr-self"].instrument, nc["D-ptr-self"].reason) == ("json-schema", "publication-url")  # in part
    assert (nc["R-Signed"].instrument, nc["R-Signed"].reason) == ("signature-verifier", None)
    assert nc["R-NextUpdateAfterIssue"].instrument == "code"                            # the JSON side of a date check
    assert [n.status for n in r.not_checked] == sorted((n.status for n in r.not_checked),
                                                       key=["no", "yes"].index)
    for n in r.not_checked:
        assert n.status == "yes" or n.reason, n.rule


def test_not_checked_in_xml():
    nc = {n.rule: n for n in validate(DATA / "H_pub_eaa_providers.xml").not_checked}
    assert nc["H-te-name"].occurrences[0]["location"] == \
        "/lote:ListOfTrustedEntities/lote:TrustedEntitiesList/lote:TrustedEntity/lote:TrustedEntityInformation/lote:TEName"
    assert nc["R-NextUpdateAfterIssue"].occurrences[0]["value"] == "2026-05-01T10:00:00Z"   # inside NextUpdate/dateTime
    assert nc["R-Signed"].occurrences[0]["location"] == "/lote:ListOfTrustedEntities/ds:Signature"
    assert (nc["R-NextUpdateAfterIssue"].instrument, nc["H-sig"].instrument) == ("schematron", "signature-verifier")


def test_not_checked_in_the_reports(capsys):
    main([str(DATA / "D_pid_providers.json")])
    out = capsys.readouterr().out
    assert "Not checked (" in out and "D-te-name  [official-records:" in out
    main([str(DATA / "D_pid_providers.json"), "--json"])
    rules = {n["rule"] for n in json.loads(capsys.readouterr().out)["not_checked"]}
    assert "D-te-name" in rules


# ------------------------------------------------------------------ certificate checks (Annex H, decisions #6)
def _cert(org="Provider BE", key=None, cn="Service"):
    """A self-signed test certificate, base64 DER: organizationName org (None: none), the given or a new EC key."""
    import base64
    import datetime
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = key or ec.generate_private_key(ec.SECP256R1())
    attrs = [x509.NameAttribute(NameOID.COUNTRY_NAME, "BE")]
    attrs += [x509.NameAttribute(NameOID.ORGANIZATION_NAME, org)] if org else []
    name = x509.Name(attrs + [x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    day = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(day)
            .not_valid_after(day + datetime.timedelta(days=3650)).sign(key, hashes.SHA256()))
    return base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()


CERT_RULES = {"H-sdi-org", "H-sdi-key", "R-X509Certificate"}
FAKE_CERT = "MIIBszCCAVmgAwIBAgIUQQ=="                 # base64, so the schemas accept it, but only 16 bytes: no certificate


def _h_json(tmp_path, certs, te_name=None):
    """The siros Annex H list (JSON) with the first service's certificates and, optionally, TEName replaced."""
    doc = json.loads((DATA / "siros_pub_tl.json").read_text(encoding="utf-8"))
    te = doc["LoTE"]["TrustedEntitiesList"][0]
    te["TrustedEntityServices"][0]["ServiceInformation"]["ServiceDigitalIdentity"] = {"X509Certificates": certs}
    if te_name:
        te["TrustedEntityInformation"]["TEName"] = te_name
    p = tmp_path / "h.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return [f for f in validate(p).findings if f.rule in CERT_RULES]


def test_certificate_of_a_real_list_matches():
    assert not [f for f in validate(DATA / "siros_pub_tl.json").findings if f.rule in CERT_RULES]
    assert not [f for f in validate(DATA / "H_pub_eaa_providers.xml").findings if f.rule in CERT_RULES]


def test_organization_name_matches_any_te_name_value(tmp_path):
    names = [{"lang": "en", "value": "Provider BE"}, {"lang": "fr", "value": "Fournisseur BE"}]
    assert not _h_json(tmp_path, [{"val": _cert("Fournisseur BE")}], names)            # decision #6: any language
    assert not _h_json(tmp_path, [_cert("Provider BE")], names)                         # a plain string is accepted too


@pytest.mark.parametrize("org,why", [("Other Org", "is not one of the TEName values"),
                                     ("provider be", "is not one of the TEName values"),   # strictly: case counts
                                     (None, "has no organizationName")])
def test_organization_name_must_match(tmp_path, org, why):
    (f,) = _h_json(tmp_path, [{"val": _cert(org)}], [{"lang": "en", "value": "Provider BE"}])
    assert f.rule == "H-sdi-org" and why in f.message and f.source["page"] == 65
    assert f.location.endswith("/ServiceDigitalIdentity/X509Certificates/0")


def test_several_certificates_one_key_and_subject(tmp_path):
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    te = [{"lang": "en", "value": "Provider BE"}]
    assert not _h_json(tmp_path, [_cert(key=key), _cert(key=key)], te)                  # renewed: same key and subject
    found = _h_json(tmp_path, [_cert(), _cert(cn="Other")], te)                         # two keys, two subjects
    assert [f.rule for f in found] == ["H-sdi-key", "H-sdi-key"]
    assert "2 different public keys" in found[0].message and "different subject names" in found[1].message


def test_value_that_is_not_a_certificate(tmp_path):
    (f,) = _h_json(tmp_path, [FAKE_CERT], [{"lang": "en", "value": "Provider BE"}])
    assert f.rule == "R-X509Certificate" and f.source["ref"] == "Clause 6.6.3.1" and f.source["line"] == 2170


@pytest.mark.parametrize("name,profile", [("D_pid_providers.json", None), ("D_pid_providers.xml", None),
                                          ("D_pid_providers.json", "LoTL")])
def test_every_list_decodes_its_certificates(tmp_path, name, profile):
    """R-X509Certificate (6.6.3.1) is a core rule: it applies to every list, not only to Annex H, and to every
    ServiceDigitalIdentity (the services' and the pointers' to other lists)."""
    p = _retyped(tmp_path, name, LOTL) if profile else tmp_path / name
    text = p.read_text(encoding="utf-8") if profile else (DATA / name).read_text(encoding="utf-8")
    good = re.search(r"MII[A-Za-z0-9+/=]{100,}", text).group(0)              # the list's (real) certificate
    p.write_text(text.replace(good, FAKE_CERT), encoding="utf-8")
    r = validate(p)
    assert r.profile == (profile or "D")
    found = [f for f in r.findings if f.rule in CERT_RULES]
    assert [f.rule for f in found] == ["R-X509Certificate"] * 2 and len(r.findings) == 2
    assert any("PointersToOtherLoTE" in f.location for f in found)
    assert any("ServiceInformation" in f.location for f in found)
    assert "R-X509Certificate" not in {n.rule for n in r.not_checked}             # checked: not in "Not checked"


def test_certificate_checks_in_xml(tmp_path):
    xml = (DATA / "H_pub_eaa_providers.xml").read_text(encoding="utf-8")
    good = re.search(r"<X509Certificate>([^<]+)</X509Certificate>", xml).group(1)
    p = tmp_path / "h.xml"
    p.write_text(xml.replace(good, _cert("Other Org")), encoding="utf-8")
    (f,) = [f for f in validate(p).findings if f.rule in CERT_RULES]
    assert f.rule == "H-sdi-org" and f.location.endswith("lote:ServiceDigitalIdentity/lote:DigitalId/lote:X509Certificate")
    nc = {n.rule for n in validate(DATA / "H_pub_eaa_providers.xml").not_checked}
    assert not {"H-sdi-org", "H-sdi-key"} & nc                                       # checked now: not in "Not checked"
