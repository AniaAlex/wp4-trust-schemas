"""The schema checker (lote-schemas check) on the generated track schemas: every component the text requires is found
with the right name, place and cardinality. The XML binding matches the text completely; the JSON binding has two known
name differences (the JSON names of the address components), which stay pending until the text or Forge settles them."""
import collections

import pytest

from lote_schema_generator import check as c
from lote_schema_generator.paths import TRACK_GEN

# The two components whose JSON names differ from the text (each also shows as one EXTRA: the name the schema uses).
JSON_PENDING = {"6.3.5.1/PostalAddresses", "6.3.5.2/ElectronicAddress"}


@pytest.fixture(scope="module")
def reqs():
    return c.requirements_from_model()


def files(track, binding):
    g = TRACK_GEN[track]
    return [g + "lote_core.xsd", g + "lote_tie.xsd", g + "lote_sie.xsd"] if binding == "xml" else [g + "lote_core.schema.json"]


@pytest.mark.parametrize("track", ["explicit", "implicit"])
@pytest.mark.parametrize("binding", ["xml", "json"])
def test_track_schema_matches_text(reqs, track, binding):
    inv = c.inventory_xml(files(track, binding)) if binding == "xml" else c.inventory_json(files(track, binding))
    findings, _ = c.check(inv, reqs, c.scheme_overrides(track))
    failing = {f["id"] for f in findings if f["status"] in c.FAILING}
    expected = JSON_PENDING if binding == "json" else set()
    assert failing == expected, "\n".join(f"{f['status']} {f['id']}: {f.get('detail', '')}" for f in findings if f["status"] in c.FAILING)
    counts = collections.Counter(f["status"] for f in findings)
    assert counts["OK"] == (67 if binding == "xml" else 65)


def test_cli_exit_code(capsys):
    assert c.main(files("explicit", "xml") + ["--scheme", "explicit"]) == 0
    assert "Summary: OK 67" in capsys.readouterr().out
