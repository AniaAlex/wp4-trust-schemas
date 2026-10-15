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

# (file, profile, track, expected track, the rules that fail: empty when the list is valid)
CASES = [
    ("D_pid_providers.json", "D", None, "explicit", set()),
    ("D_pid_providers.xml", "D", None, "explicit", set()),
    ("H_pub_eaa_providers.xml", "H", None, "explicit", set()),
    ("explicit_list.json", None, None, "explicit", set()),
    ("explicit_list.xml", None, None, "explicit", set()),
    ("implicit_list_direct.json", None, None, "implicit", set()),        # 6.3.0: no ListAndSchemeInformation
    ("implicit_list_direct.xml", None, None, "implicit", set()),
    ("D_with_json_signature.json", "D", None, "explicit", {"LoTE-Signature-not-in-json", "D-Signature-json-prohibited"}),
    ("H_without_signature.xml", "H", None, "explicit", {"H-Signature-xml-required"}),                      # H.4
    ("implicit_list_with_scheme_name.json", None, "implicit", "implicit", {"IMP-SchemeName-prohibited"}),  # Table 1 '/'
]


@pytest.mark.parametrize("name,profile,track,want_track,want_rules", CASES, ids=[c[0] for c in CASES])
def test_validate(name, profile, track, want_track, want_rules):
    r = validate(DATA / name, profile=profile, track=track)
    assert isinstance(r, Report)
    assert r.track == want_track
    assert {f.rule for f in r.findings} == want_rules, [f"{f.layer} {f.rule}: {f.message}" for f in r.findings]
    assert r.valid == (not want_rules)


@pytest.mark.parametrize("name,profile", [("D_with_json_signature.json", "D"), ("H_without_signature.xml", "H"),
                                          ("implicit_list_with_scheme_name.json", None)])
def test_every_failure_cites_the_text(name, profile):
    r = validate(DATA / name, profile=profile, track=None if profile else "implicit")
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
    ("attribute the spec does not define", [('<ListOfTrustedEntities ', '<ListOfTrustedEntities Id="x" ')],
     "LoTE-Id-not-allowed", "Clause 5"),
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
    findings = validate(_json(tmp_path, change), track="explicit").findings
    assert {f.rule for f in findings} == rules, [f"{f.rule}: {f.message}" for f in findings]
    assert all(f.source["ref"] == ref and f.source["quote"] for f in findings), findings


def test_profile_cannot_be_implicit():
    with pytest.raises(ValueError):
        validate(DATA / "D_pid_providers.json", profile="D", track="implicit")


def test_cli(capsys):
    assert main([str(DATA / "D_pid_providers.json"), "--profile", "D"]) == 0
    assert "profile D - valid" in capsys.readouterr().out
    assert main([str(DATA / "H_without_signature.xml"), "--profile", "H", "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["profile"] == "H" and out["findings"][0]["rule"] == "H-Signature-xml-required"


@pytest.mark.skipif(not GENERATOR.is_dir(), reason="the generator project is not next to this one")
@pytest.mark.parametrize("published,source", [
    ("explicit/base", "explicit/generated/base"), ("explicit/profiles", "explicit/generated/profiles"),
    ("implicit", "implicit/generated"),
    ("model/lote_model.json", "base/model/lote_model.json"),
    ("model/explicit/lote_model_explicit.json", "explicit/model/lote_model_explicit.json"),
    ("model/implicit/lote_model_implicit.json", "implicit/model/lote_model_implicit.json"),
    ("model/explicit/profiles", "explicit/model/profiles"),
])
def test_published_schemas_are_current(published, source):
    """The package data is the generator's latest output: run `lote-schemas publish` if this fails."""
    left, right = Path(SCHEMAS) / published, GENERATOR / source
    if right.is_file():
        assert left.is_file() and filecmp.cmp(left, right, shallow=False), f"{published} differs from the generator's {source}"
        return
    stale = []

    def walk(c, rel=""):
        stale.extend(rel + n for n in c.left_only + c.right_only + c.diff_files)
        for n, s in c.subdirs.items():
            walk(s, rel + n + "/")
    walk(filecmp.dircmp(left, right))
    assert not stale, f"published {published} differs from the generator's {source}: {stale}"
