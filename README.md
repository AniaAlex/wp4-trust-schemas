# wp4-trust-schemas

Schemas for lists of trusted entities (ETSI TS 119 602 V1.1.1, LoTE), generated from JSON models of the specification, and a validator that reports every failure with the sentence of the text it breaks. WP4 (WE BUILD).

## Two packages

| Package | Distribution | Command | What it does |
|---|---|---|---|
| [schema_generator/](schema_generator/) | `wp4-lote-schema-generator` | `lote-schemas` | JSON models (core, explicit and implicit tracks, annex D–I profiles) → JSON Schema, XSD, Schematron |
| [schema_validator/](schema_validator/) | `wp4-lote-schema-validator` | `lote-validate` | validates a list (XML or JSON) against the generated schemas, with citations |

The validator does not depend on the generator: it ships a copy of the generated schemas as package data, written by `lote-schemas publish`.

```
schema_generator/                         schema_validator/
  model/      core model, tracks, profiles  src/lote_schema_validator/
                                              validate.py
  core/ explicit/ implicit/                   schemas/   <- lote-schemas publish
    model/ generated/                       tests/  (data/: sample lists)
  src/lote_schema_generator/
  tests/
  reference/  Forge, earlier hand-written schemas
docs/         the text (spec/: txt, pdf), project decisions vs ETSI, ETSI defects
```

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -e "schema_generator[dev]" -e "schema_validator[dev]"

.venv/bin/lote-validate list.xml --profile D       # validate a list
cd schema_generator && ../.venv/bin/lote-schemas build --publish && ../.venv/bin/pytest   # rebuild, publish, test
cd ../schema_validator && ../.venv/bin/pytest
```

After a change to the model or the generator: `lote-schemas build --publish`, then run both test suites. The validator's `test_published_schemas_are_current` fails when its schemas are older than the generator's output.

## Rules of the project

- **The text comes first.** Every rule in the schemas carries a verbatim quote of TS 119 602 (clause or annex row, page, line), proofread against [docs/spec/](docs/spec/). The models are written by hand; the schemas are generated from them.
- **XML element order follows Forge**, where the text gives none.
- Where the project departs from ETSI's text or Forge schemas, the reason is in [docs/project_decisions_vs_etsi.md](docs/project_decisions_vs_etsi.md); defects found in the text are in [docs/etsi_defects.md](docs/etsi_defects.md).
- **No signature validator yet:** the schemas check only where a signature may or must sit, not whether it is valid.

## Docs

| File | Content |
|---|---|
| [docs/etsi_defects.md](docs/etsi_defects.md) | Defects found in the text of TS 119 602 |
| [docs/project_decisions_vs_etsi.md](docs/project_decisions_vs_etsi.md) | Decisions where the project differs from ETSI text or Forge |
| [schema_generator/base/model/README.md](schema_generator/base/model/README.md) | The model: structures, components, bindings, constraints |
