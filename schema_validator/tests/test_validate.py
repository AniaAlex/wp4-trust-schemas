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
    ("D_with_json_signature.json", "D", None, "explicit", {"Signature", "D-Signature-json-prohibited"}),   # 6.8.0, D.4
    ("H_without_signature.xml", "H", None, "explicit", {"H-Signature-xml-required"}),                      # H.4
    ("implicit_list_with_scheme_name.json", None, "implicit", "implicit", {"SchemeName"}),                 # Table 1 '/'
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
@pytest.mark.parametrize("sub", ["explicit/generated", "implicit/generated", "explicit/model", "implicit/model"])
def test_published_schemas_are_current(sub):
    """The package data is the generator's latest output: run `lote-schemas publish` if this fails."""
    cmp = filecmp.dircmp(Path(SCHEMAS) / sub, GENERATOR / sub)
    stale = []

    def walk(c, rel=""):
        stale.extend(rel + n for n in c.left_only + c.right_only + c.diff_files)
        for n, s in c.subdirs.items():
            walk(s, rel + n + "/")
    walk(cmp)
    assert not stale, f"published schemas differ from the generator's {sub}: {stale}"
