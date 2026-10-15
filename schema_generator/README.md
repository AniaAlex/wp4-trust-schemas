# schema_generator

Generates the LoTE schemas (JSON Schema, XSD, Schematron) from JSON models of ETSI TS 119 602 V1.1.1 (2025-11). The models are written by hand and proofread against the text ([../docs/spec/](../docs/spec/)); every rule in them carries a verbatim quote of the text (clause or annex row, page, line).

## Layout

| Path | Content |
|---|---|
| [src/lote_schema_generator/](src/lote_schema_generator/) | The generator (Python package) and the `lote-schemas` command |
| [tests/](tests/) | pytest suites: core JSON and XML, profiles JSON and XML, the two tracks, the schema checker, the build (reproduces the committed outputs) |
| [base/](base/) | **Frozen.** The core model, for both kinds of list: `model/` (`lote_model.json`, the track differentials in `schemes/`, Annex C in `registered_uris.json`), `generated/` (its schemas, Table 1 as rules) and [derive_tracks.py](base/derive_tracks.py), which derived the two track models before the freeze |
| [explicit/](explicit/) | The explicit track, **where the work happens**: `model/` (its model, edited by hand, and the annex D–I overlays in `profiles/`), `generated/base/` (its schemas) and `generated/profiles/` (the D–I profiles) |
| [implicit/](implicit/) | **Frozen.** The implicit track: `model/` (its model) and `generated/` (its schemas) |
| [reference/](reference/) | ETSI's Forge schemas (`forge/`, with `errors.md`) and the earlier hand-written schemas (`handwritten/`), used by the tests as comparison |

## The chain

```
base/model/lote_model.json               frozen  ─► gen_json, gen_xsd --scheme base     ─► base/generated/
explicit/model/lote_model_explicit.json  edited  ─► gen_json, gen_xsd --scheme explicit ─► explicit/generated/base/
implicit/model/lote_model_implicit.json  frozen  ─► gen_json, gen_xsd --scheme implicit ─► implicit/generated/
explicit model + explicit/model/profiles/        ─► gen_profiles_from_model             ─► explicit/generated/profiles/
```

The models are written by hand (with Claude's help) and proofread against the text: a quote, page or line in them is checked by reading it against [../docs/spec/ts_119602v010101p.txt](../docs/spec/ts_119602v010101p.txt). Since 2026-10-15 the base model, the track differentials and the implicit model are frozen ([tests/test_frozen.py](tests/test_frozen.py) guards them) and the explicit model is edited directly ([../docs/project_decisions_vs_etsi.md #4](../docs/project_decisions_vs_etsi.md#4-the-base-model-and-the-implicit-track-are-frozen-the-explicit-track-is-edited-directly)). [base/derive_tracks.py](base/derive_tracks.py) is kept for unfreezing; it is not part of the build.

## Install and use

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"     # editable: the generator works on this directory

lote-schemas build                    # generate the schemas from the models
lote-schemas build --publish          # ... and copy explicit/ into ../schema_validator (package data)
lote-schemas publish --to DIR         # copy the current results elsewhere
lote-schemas check explicit/generated/base/lote_core.xsd explicit/generated/base/lote_tie.xsd explicit/generated/base/lote_sie.xsd --scheme explicit
pytest                                # all test suites
```

The generator reads and writes this project directory; set `LOTE_SCHEMAS_ROOT` to use another one.

## Where to change what

| Change | Edit |
|---|---|
| structures, components, value types, binding overrides, constraints, citations | `explicit/model/lote_model_explicit.json` |
| the base model or the implicit track | nothing: frozen (a citation correction only, with its hash in `tests/test_frozen.py`) |
| an annex rule | `explicit/model/profiles/<X>_*.json` |
| how a binding expresses the model | `gen_json.py`, `gen_xsd.py`, `gen_profiles_from_model.py` |

Never edit the generated files (`*/generated/`): they are overwritten by the next build. The model is documented in [base/model/README.md](base/model/README.md); decisions and spec defects in [../docs/](../docs/).
