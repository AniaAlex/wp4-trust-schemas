"""The build chain, in order, and the hand-over of its outputs to the validator package.

    spec text -> sources.py -> build_model -> build_schemes -> build_profiles
              -> gen_json / gen_xsd (core, explicit, implicit) -> gen_profiles_from_model -> [publish]

Every step runs as its own process (python -m lote_schema_generator.<step>), so a step that fails a check stops the
chain with that step's own error messages; the outputs of the steps before it stay as they are.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from .paths import MODEL_DIR, ROOT, SNAPSHOT, TRACK_GEN, VALIDATOR_SCHEMAS

STEPS = [
    ("build_model", []),                       # core model, citations from sources.py
    ("build_schemes", []),                     # explicit and implicit tracks: differentials and snapshots
    ("build_profiles", []),                    # annex D-I overlays, on the explicit track
    ("gen_json", ["--scheme", "core"]), ("gen_xsd", ["--scheme", "core"]),
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
    """Copy what the validator needs into its package data: both tracks (snapshot model, schemas, profiles) and the
    model files it cites (scheme differentials, profile overlays). The target is replaced, so it holds no stale files."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    for track in ("explicit", "implicit"):
        shutil.copytree(Path(SNAPSHOT[track]).parent, target / track / "model")
        shutil.copytree(TRACK_GEN[track], target / track / "generated")
    shutil.copytree(Path(MODEL_DIR) / "schemes", target / "model" / "schemes")
    shutil.copytree(Path(MODEL_DIR) / "profiles", target / "model" / "profiles")
    shutil.copy2(Path(MODEL_DIR) / "lote_model.json", target / "model" / "lote_model.json")
    (target / "__init__.py").write_text('"""Generated schemas, published by `lote-schemas publish`. Do not edit."""\n')
    if not quiet:
        n = sum(1 for p in target.rglob("*") if p.is_file())
        print(f"published {n} files to {target}")
    return 0
