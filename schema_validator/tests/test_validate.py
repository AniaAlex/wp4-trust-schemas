"""lote-validate on sample lists (tests/data, written from the generator's test builders): the verdict, the track, the
rules that fail, and the citation each failure carries."""
import filecmp
import json
from pathlib import Path

import pytest

from lote_schema_validator import Report, validate
from lote_schema_validator.validate import SCHEMAS, main

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
    ("implicit_list_direct.json", None, None, "explicit", DIRECT | {"EXP-ListAndSchemeInformation-required"}),
    ("implicit_list_direct.xml", None, None, "explicit", DIRECT),       # XSD stops at the first unexpected element
    ("D_with_json_signature.json", "D", None, "explicit", {"LoTE-Signature-not-in-json", "D-Signature-json-prohibited"}),
    ("H_without_signature.xml", "H", None, "explicit", {"H-Signature-xml-required"}),                      # H.4
    ("implicit_list_with_scheme_name.json", None, "explicit", "explicit", SCHEME_INFO),                    # Table 1
]


@pytest.mark.parametrize("name,profile,track,want_track,want_rules", CASES, ids=[c[0] for c in CASES])
def test_validate(name, profile, track, want_track, want_rules):
    r = validate(DATA / name, profile=profile, track=track)
    assert isinstance(r, Report)
    assert r.track == want_track
    assert {f.rule for f in r.findings} == want_rules, [f"{f.layer} {f.rule}: {f.message}" for f in r.findings]
    assert r.valid == (not want_rules)


@pytest.mark.parametrize("name,profile", [("D_with_json_signature.json", "D"), ("H_without_signature.xml", "H"),
                                          ("implicit_list_with_scheme_name.json", None), ("implicit_list_direct.json", None)])
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
    r = validate(f, track="explicit")
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
    assert main([str(DATA / "explicit_list.json"), "--explicit", "--no-profile"]) == 0


def test_cli(capsys):
    assert main([str(DATA / "D_pid_providers.json"), "--profile", "D"]) == 0
    assert "profile D (--profile D) - valid" in capsys.readouterr().out
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


def test_no_lote_type_no_profile():
    r = validate(DATA / "implicit_list_direct.json")
    assert r.profile is None and r.declared_profile is None and r.profile_reason == "it has no LoTEType"


def test_no_profile_overrides_lote_type():
    r = validate(DATA / "D_pid_providers.json", profile=False)
    assert r.profile is None and r.declared_profile == "D" and r.profile_reason == "--no-profile"


def test_wrong_profile_warns():
    r = validate(DATA / "D_pid_providers.json", profile="E")
    assert r.profile == "E" and r.declared_profile == "D"
    (w,) = r.warnings
    assert "(Annex D)" in w and "Did you mean --profile D?" in w
    assert "E-LoTEType-fixed" in {f.rule for f in r.findings}               # the findings are still those of E


def test_right_profile_does_not_warn():
    assert not validate(DATA / "H_without_signature.xml", profile="H").warnings


def test_cli_profile_flags(capsys):
    assert main([str(DATA / "D_pid_providers.json"), "--profile", "E"]) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[1].startswith("WARNING: ") and "Did you mean --profile D?" in out
    assert main([str(DATA / "D_pid_providers.json")]) == 0
    assert "profile D (from its LoTEType" in capsys.readouterr().out
    with pytest.raises(SystemExit):                                     # --profile and --no-profile exclude each other
        main([str(DATA / "D_pid_providers.json"), "--profile", "D", "--no-profile"])


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
