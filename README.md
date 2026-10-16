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

## Profiles

TS 119 602 defines six EU profiles, Annexes D–I. Each narrows the explicit track: fixed URIs, required and prohibited components, extra rules. A list names its profile by its `LoTEType`; validate it with `lote-validate <list> --profile <annex>`.

| Annex | List of | `LoTEType` | Binding the annex allows | Validate | Files |
|---|---|---|---|---|---|
| D | providers of person identity data (PID) | `http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList` | JSON | `.venv/bin/lote-validate list.json --profile D` | `D_pid_providers` |
| E | wallet providers | `…/LoTEType/EUWalletProvidersList` | JSON | `.venv/bin/lote-validate list.json --profile E` | `E_wallet_providers` |
| F | providers of wallet relying party access certificates (WRPAC) | `…/LoTEType/EUWRPACProvidersList` | JSON | `.venv/bin/lote-validate list.json --profile F` | `F_wrpac_providers` |
| G | providers of wallet relying party registration certificates (WRPRC) | `…/LoTEType/EUWRPRCProvidersList` | JSON | `.venv/bin/lote-validate list.json --profile G` | `G_wrprc_providers` |
| H | public sector bodies issuing electronic attestation of attributes (Pub-EAA) | `…/LoTEType/EUPubEAAProvidersList` | JSON or XML | `.venv/bin/lote-validate list.json --profile H`<br>`.venv/bin/lote-validate list.xml --profile H` | `H_pub_eaa_providers` |
| I | registrars and registers | `…/LoTEType/EURegistrarsAndRegistersList` | JSON | `.venv/bin/lote-validate list.json --profile I` | `I_registrars_and_registers` |
| – | List of Trusted Lists (no annex) | – | – | `.venv/bin/lote-validate list.json --explicit` | – |

- **Files:** each profile is an overlay in [schema_generator/explicit/model/profiles/](schema_generator/explicit/model/profiles/) (`<name>.json`), generated into [schema_generator/explicit/generated/profiles/](schema_generator/explicit/generated/profiles/) as `lote_profile_<name>.json` (JSON Schema) and `.sch` (Schematron).
- **XML for D–G and I:** the annexes allow only JSON, but XML profiles are generated for all six, as content checks ([decisions #1](docs/project_decisions_vs_etsi.md#1-xml-profiles-for-annexes-that-allow-only-json)).
- **No profile:** the List of Trusted Lists has no annex; validate it with `--explicit` ([decisions #3](docs/project_decisions_vs_etsi.md#3-wp4-lists-are-explicit-the-implicit-track-is-not-used-in-wp4)).

## Commands

Run from the repository root after the Quick start install. Every command has `--help`.

**`lote-validate <list>`**: validate a list (`.xml` or `.json`). Exit code 0 if valid, 1 if there are findings.

| Flag | Effect |
|---|---|
| `--profile {D,E,F,G,H,I}` | also apply the annex profile (implies `--explicit`) |
| `--explicit` | validate as an explicit list (Table 1, explicit column); the default and only track |
| `--json` | print the findings as JSON instead of text |

```bash
.venv/bin/lote-validate list.json --profile D --json > report.json
```

**`lote-schemas`** (generator; run inside `schema_generator/`):

| Command | Effect |
|---|---|
| `lote-schemas build` | run the whole generation chain: base, explicit and implicit schemas, the D–I profiles |
| `lote-schemas build --publish` | then copy the explicit track into the validator package (use after every model change) |
| `lote-schemas build --quiet` | the same, with less output |
| `lote-schemas publish [--to DIR]` | only copy the generated schemas (default: the validator package) |
| `lote-schemas check <schemas…> [--scheme explicit\|implicit] [--model M] [--json] [--show-ok]` | check an XSD or JSON Schema, e.g. Forge's, against the requirements of the model; `--show-ok` also lists the components that match |

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
