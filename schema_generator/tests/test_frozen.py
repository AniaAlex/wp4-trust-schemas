"""The frozen models do not change: the base model (both kinds of list), the two track differentials and the implicit
track are frozen since 2026-10-15, and the explicit track is edited by hand (docs/project_decisions_vs_etsi.md #4).

A failure here means a frozen file was edited. If the change is one the freeze allows (see the file's "frozen" entry:
a citation correction), update its hash below in the same commit, so the change is a visible decision."""
import hashlib
import json
from pathlib import Path

import pytest

from lote_schema_generator.paths import ROOT

FROZEN = {
    "base/model/lote_model.json": "d79e921e420870ab697bb76a2376411ec85b8e7e221006bc6b33db9217a2e5c2",
    "base/model/schemes/explicit.json": "d5fa0051bb02aed6ce9e5d19755de41c43efa5706bca81af3ce7a915a40f7cee",
    "base/model/schemes/implicit.json": "28bc117deee63b54bfbe3328786f15f1246aafded98a59abcf488108688e7511",
    "implicit/model/lote_model_implicit.json": "a9cd6235c07f3797d91ff644c4314aacb297f5ce1aecc5343bf119d33b42db9a",
}


@pytest.mark.parametrize("rel", FROZEN)
def test_frozen_file_unchanged(rel):
    data = (Path(ROOT) / rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == FROZEN[rel], f"{rel} is frozen; see its 'frozen' entry"
    assert json.loads(data)["status"] == "frozen", f"{rel} lost its frozen status"


def test_explicit_model_is_active():
    m = json.loads((Path(ROOT) / "explicit/model/lote_model_explicit.json").read_bytes())
    assert m["status"] == "active"
