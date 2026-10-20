"""Every 'checkable' in the explicit model and the profile overlays is {status, instrument, reason, note}, every field
present, null where it does not apply: status yes / no (decidable from the list alone); instrument, per binding {xml,
json}, from the model's checkable_instruments, set for every yes rule and for a no rule with a 'check' (the part it
checks), and matching what the generator makes of the check; reason from
checkable_reasons, set exactly for the no rules. A core rules-layer constraint names its 'components', which exist in its
structure."""
import glob
import json

import pytest

from lote_schema_generator.paths import PROFILES_DIR, SNAPSHOT

MODEL = json.load(open(SNAPSHOT["explicit"], encoding="utf-8"))
REASONS = MODEL["checkable_reasons"]
INSTRUMENTS = MODEL["checkable_instruments"]
FILES = [SNAPSHOT["explicit"]] + sorted(glob.glob(PROFILES_DIR + "*.json"))


def checkables(o, where=""):
    if isinstance(o, dict):
        if "checkable" in o and "key" in o:
            yield f"{where}{o['key']}", o
        for v in o.values():
            yield from checkables(v, where)
    elif isinstance(o, list):
        for v in o:
            yield from checkables(v, where)


ENTRIES = [(f"{fn.rsplit('/', 1)[-1]}:{k}", c) for fn in FILES
           for k, c in checkables(json.load(open(fn, encoding="utf-8")))]


def test_entries_found():
    assert len(ENTRIES) > 100


@pytest.mark.parametrize("where,c", ENTRIES, ids=[w for w, _ in ENTRIES])
def test_checkable_shape(where, c):
    ck = c["checkable"]
    assert isinstance(ck, dict) and list(ck) == ["status", "instrument", "reason", "note"], ck
    assert ck["status"] in ("yes", "no")
    if ck["instrument"] is not None:
        assert list(ck["instrument"]) == ["xml", "json"] and set(ck["instrument"].values()) <= set(INSTRUMENTS)
    if ck["status"] == "yes":
        assert ck["instrument"] and ck["reason"] is None
    else:
        assert ck["reason"] in REASONS, f"unknown reason {ck['reason']!r}: add it to checkable_reasons"
        assert (ck["instrument"] is None) == (not c.get("check")), "a no rule has an instrument exactly when it has a check"
    t = (c.get("check") or {}).get("type")
    if c.get("xpath"):                                    # an XML-only rule (ds:Signature): no JSON counterpart
        assert ck["instrument"] == {"xml": "schematron", "json": "not-applicable"} and ck["note"]
    elif t:                                               # what the generators make of the check
        assert ck["instrument"] == {"xml": "schematron", "json": "code" if t == "months-after" else "json-schema"}
    assert ck["note"] is None or (isinstance(ck["note"], str) and ck["note"])


def test_every_reason_and_instrument_is_used():
    assert set(REASONS) <= {c["checkable"]["reason"] for _, c in ENTRIES}
    assert set(INSTRUMENTS) <= {i for _, c in ENTRIES for i in (c["checkable"]["instrument"] or {}).values()}


def test_core_rules_layer_components_exist():
    for sname, st in MODEL["structures"].items():
        names = {c["name"] for c in st["components"]}
        for c in st.get("constraint", []):
            assert set(c.get("components", [])) <= names, (c["key"], sname)
