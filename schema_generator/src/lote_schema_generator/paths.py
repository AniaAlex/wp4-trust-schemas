"""Where the generator reads and writes: one place for every location of the schema_generator project.

The generator works on its project directory (the parent of src/): the spec text, the model, the generated schemas and
the reference schemas live there, not inside the installed package. Install the package editable (pip install -e .) or
set LOTE_SCHEMAS_ROOT to the project directory.

Paths are strings ending in "/" where they name a directory, as the modules join them with "+".
"""
import os
from pathlib import Path

ROOT = os.environ.get("LOTE_SCHEMAS_ROOT") or str(Path(__file__).resolve().parents[2])
ROOT = ROOT.rstrip("/") + "/"

SPEC = ROOT + "spec/ts_119602v010101p.txt"                       # the text of ETSI TS 119 602 V1.1.1

MODEL_DIR = ROOT + "model/"
MODEL = MODEL_DIR + "lote_model.json"                             # the core model (both kinds of list)
SCHEMES_DIR = MODEL_DIR + "schemes/"                              # the explicit / implicit differentials
PROFILES_DIR = MODEL_DIR + "profiles/"                            # the annex D-I overlays

CORE_GEN = ROOT + "core/generated/"                               # generated schemas: both kinds of list
SNAPSHOT = {t: ROOT + f"{t}/model/lote_model_{t}.json" for t in ("explicit", "implicit")}
TRACK_GEN = {t: ROOT + f"{t}/generated/" for t in ("explicit", "implicit")}
PROFILES_GEN = TRACK_GEN["explicit"] + "profiles/"                # the profiles build on the explicit track

REFERENCE = ROOT + "reference/"
FORGE = REFERENCE + "forge/"                                      # ETSI's Annex A bindings, as published on ETSI Forge
HANDWRITTEN_CORE = REFERENCE + "handwritten/1960201_json_schema_text_based.json"
HANDWRITTEN_PROFILES = REFERENCE + "handwritten/profiles/"

# where `lote-schemas publish` copies the schemas for the validator package (a sibling project by default)
VALIDATOR_SCHEMAS = os.environ.get("LOTE_VALIDATOR_SCHEMAS") or \
    str(Path(ROOT).parent / "schema_validator" / "src" / "lote_schema_validator" / "schemas")
