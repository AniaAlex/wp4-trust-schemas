# schema_generator

Generates the LoTE schemas (JSON Schema, XSD, Schematron) from the text of ETSI TS 119 602 V1.1.1 (2025-11). Every rule in the schemas is traced to a verbatim quote of the text (clause or annex row, page, line).

## Layout

| Path | Content |
|---|---|
| [src/lote_schema_generator/](src/lote_schema_generator/) | The generator (Python package) and the `lote-schemas` command |
| [tests/](tests/) | pytest suites: core JSON and XML, profiles JSON and XML, the two tracks, the schema checker, the build (reproduces the committed outputs) |
| [spec/](spec/) | The text of TS 119 602 (txt, used to verify every quote; pdf) |
| [model/](model/) | The core model (`lote_model.json`), the track differentials (`schemes/`), the annex D–I overlays (`profiles/`), Annex C (`registered_uris.json`) |
| [core/generated/](core/generated/) | Generated schemas for both kinds of list (Table 1 as rules) |
| [explicit/](explicit/) | The explicit track: model snapshot, generated schemas, and the D–I profiles (`generated/profiles/`) |
| [implicit/](implicit/) | The implicit track: model snapshot and generated schemas |
| [reference/](reference/) | ETSI's Forge schemas (`forge/`, with `errors.md`) and the earlier hand-written schemas (`handwritten/`), used by the build's agreement checks and as comparison |

## The chain

```
spec/ + sources.py ─► build_model ─► model/lote_model.json
                      build_schemes ─► model/schemes/*.json ─► explicit|implicit/model/ (snapshots)
                      build_profiles ─► model/profiles/*.json (on the explicit track)
                      gen_json, gen_xsd (core, explicit, implicit) ─► */generated/
                      gen_profiles_from_model ─► explicit/generated/profiles/
```

Every step checks its input and stops with an error if a check fails: quotes not found in the text, a profile or track that does not only narrow its base, a binding override without its source, unknown check types.

## Install and use

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"     # editable: the generator works on this directory

lote-schemas build                    # run the whole chain
lote-schemas build --publish          # ... and copy the results into ../schema_validator (package data)
lote-schemas publish --to DIR         # copy the current results elsewhere
lote-schemas check explicit/generated/lote_core.xsd explicit/generated/lote_tie.xsd explicit/generated/lote_sie.xsd --scheme explicit
pytest                                # all test suites
```

The generator reads and writes this project directory; set `LOTE_SCHEMAS_ROOT` to use another one.

## Where to change what

| Change | Edit |
|---|---|
| a citation of the text | `src/lote_schema_generator/sources.py` |
| structures, components, value types, binding overrides, core constraints | `build_model.py` |
| a difference between the explicit and the implicit track | `build_schemes.py` |
| an annex rule | `build_profiles.py` |
| how a binding expresses the model | `gen_json.py`, `gen_xsd.py`, `gen_profiles_from_model.py` |

Never edit the generated files (`model/*.json`, `*/model/`, `*/generated/`): they are overwritten by the next build. The model is documented in [model/README.md](model/README.md); decisions and spec defects in [../docs/](../docs/).
