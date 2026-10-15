"""The build chain, in order, and the hand-over of its outputs to the validator package.

    models (base/model/ frozen, implicit/model/ frozen, explicit/model/ edited by hand)
    -> gen_json / gen_xsd (base, explicit, implicit) -> gen_profiles_from_model -> [publish]

base/derive_tracks.py (core + differential -> track snapshots) is not part of the chain while the base model is frozen.

Every step runs as its own process (python -m lote_schema_generator.<step>), so a step that
fails a check stops the chain with that step's own error messages; the outputs of the steps before it stay as they are.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import EXPLICIT, ROOT, VALIDATOR_SCHEMAS

STEPS = [
    ("gen_json", ["--scheme", "base"]), ("gen_xsd", ["--scheme", "base"]),
    ("gen_json", ["--scheme", "explicit"]), ("gen_xsd", ["--scheme", "explicit"]),
    ("gen_json", ["--scheme", "implicit"]), ("gen_xsd", ["--scheme", "implicit"]),
    ("gen_profiles_from_model", []),           # profile JSON and Schematron, into explicit/generated/profiles/
]


def build(quiet=False):
    """Run the chain; return 0 on success, or the exit code of the first step that failed."""
    for step, args in STEPS:
        label = " ".join([step, *args])
        r = subprocess.run([sys.executable, "-m", f"lote_schema_generator.{step}", *args], capture_output=True, text=True)
        if r.returncode:
            print(f"FAILED  {label}\n{r.stdout}{r.stderr}", file=sys.stderr)
            return r.returncode
        if not quiet:
            last = (r.stdout.strip().splitlines() or [""])[-1].replace(ROOT, "")
            print(f"ok      {label:32} {last[:110]}")
    return 0


def publish(target=VALIDATOR_SCHEMAS, quiet=False):
    """Copy the explicit track into the validator's package data, in the same layout as in this project: explicit/model/
    (the model and the D-I overlays) and explicit/generated/ (base/ the track's schemas, profiles/ the profile schemas).
    The track's documentation (*.md) stays in the generator. The base model and the implicit track are frozen and not
    published (docs/project_decisions_vs_etsi.md #4). The target is replaced, so it holds no stale files."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(EXPLICIT, target / "explicit", ignore=shutil.ignore_patterns("*.md"))
    (target / "__init__.py").write_text('"""Generated schemas, published by `lote-schemas publish`. Do not edit."""\n')
    if not quiet:
        n = sum(1 for p in target.rglob("*") if p.is_file())
        print(f"published {n} files to {target}")
    return 0
