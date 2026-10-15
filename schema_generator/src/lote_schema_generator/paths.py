"""Where the generator reads and writes: one place for every location of the schema_generator project.

The generator works on its project directory (the parent of src/): the models, the generated schemas and the reference
schemas live there, not inside the installed package. Install the package editable (pip install -e .) or
set LOTE_SCHEMAS_ROOT to the project directory.

Paths are strings ending in "/" where they name a directory, as the modules join them with "+".
"""
import os
from pathlib import Path

ROOT = os.environ.get("LOTE_SCHEMAS_ROOT") or str(Path(__file__).resolve().parents[2])
ROOT = ROOT.rstrip("/") + "/"

BASE = ROOT + "base/"                                              # the core model (both kinds of list), frozen
MODEL_DIR = BASE + "model/"
MODEL = MODEL_DIR + "lote_model.json"                             # the core model
SCHEMES_DIR = MODEL_DIR + "schemes/"                              # the explicit / implicit differentials
BASE_GEN = BASE + "generated/"                                    # generated schemas: both kinds of list

SNAPSHOT = {t: ROOT + f"{t}/model/lote_model_{t}.json" for t in ("explicit", "implicit")}   # explicit: edited; implicit: frozen
TRACK_GEN = {"explicit": ROOT + "explicit/generated/base/", "implicit": ROOT + "implicit/generated/"}
PROFILES_DIR = ROOT + "explicit/model/profiles/"                  # the annex D-I overlays on the explicit track
PROFILES_GEN = ROOT + "explicit/generated/profiles/"              # the profiles build on the explicit track

REFERENCE = ROOT + "reference/"
HANDWRITTEN_CORE = REFERENCE + "handwritten/1960201_json_schema_text_based.json"
HANDWRITTEN_PROFILES = REFERENCE + "handwritten/profiles/"

# where `lote-schemas publish` copies the schemas for the validator package (a sibling project by default)
VALIDATOR_SCHEMAS = os.environ.get("LOTE_VALIDATOR_SCHEMAS") or \
    str(Path(ROOT).parent / "schema_validator" / "src" / "lote_schema_validator" / "schemas")
