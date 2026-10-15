"""The build chain is reproducible: run on a copy of this project, it writes exactly the schemas that are committed here.
A difference means a generated file was edited by hand, or a change in a model or in the code was not rebuilt."""
import filecmp
import os
import shutil
from pathlib import Path

import pytest

from lote_schema_generator import pipeline
from lote_schema_generator.paths import ROOT

INPUTS = ["base", "reference", "explicit", "implicit"]
OUTPUTS = ["base/generated", "explicit/generated", "implicit/generated"]


def tree(d):
    return {p.relative_to(d) for p in Path(d).rglob("*") if p.is_file() and "__pycache__" not in p.parts}


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory):
    work = tmp_path_factory.mktemp("lote") / "project"
    for d in INPUTS:
        shutil.copytree(Path(ROOT) / d, work / d)
    old = os.environ.get("LOTE_SCHEMAS_ROOT")
    os.environ["LOTE_SCHEMAS_ROOT"] = str(work)          # the steps run as subprocesses and read their root from here
    try:
        assert pipeline.build(quiet=True) == 0
    finally:
        os.environ.pop("LOTE_SCHEMAS_ROOT") if old is None else os.environ.__setitem__("LOTE_SCHEMAS_ROOT", old)
    return work


@pytest.mark.parametrize("out", OUTPUTS)
def test_build_reproduces_committed_outputs(rebuilt, out):
    here, there = Path(ROOT) / out, rebuilt / out
    assert tree(here) == tree(there)
    differ = [str(f) for f in sorted(tree(here)) if not filecmp.cmp(here / f, there / f, shallow=False)]
    assert not differ, f"rebuilt files differ from the committed ones: {differ}"


def test_publish(tmp_path):
    assert pipeline.publish(tmp_path / "schemas", quiet=True) == 0
    got = tree(tmp_path / "schemas")
    for f in ["__init__.py", "explicit/generated/base/lote_core.xsd", "explicit/generated/profiles",
              "explicit/model/lote_model_explicit.json", "explicit/model/profiles"]:
        assert any(str(p).startswith(f) for p in got), f
    assert not any(str(p).startswith(("implicit", "model", "base")) for p in got)    # frozen tracks are not published
    assert not any(p.suffix == ".md" for p in got)                                     # docs stay in the generator
