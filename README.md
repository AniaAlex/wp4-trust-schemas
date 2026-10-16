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

.venv/bin/lote-validate list.xml                  # validate a list (its profile is chosen from its LoTEType)
cd schema_generator && ../.venv/bin/lote-schemas build --publish && ../.venv/bin/pytest   # rebuild, publish, test
cd ../schema_validator && ../.venv/bin/pytest
```

After a change to the model or the generator: `lote-schemas build --publish`, then run both test suites. The validator's `test_published_schemas_are_current` fails when its schemas are older than the generator's output.

## Concepts

> **Experimental.** This approach is being tried out in this repository: the model format, the rule ids and the generated schemas may still change. The project initially covered the base, explicit and implicit models. At this stage the base and implicit models are frozen, and work continues only on the explicit model ([decisions #4](docs/project_decisions_vs_etsi.md#4-the-base-model-and-the-implicit-track-are-frozen-the-explicit-track-is-edited-directly)).

- **The model: an abstract (platform-independent) data model.** One JSON file describes the LoTE as the text does: structures, their components with occurrence (`min`/`max`), value types and the sentence of the spec each comes from, independent of XML or JSON. In model-driven engineering this is a *platform-independent model* (OMG MDA); the JSON and XML bindings are the *platform-specific* forms, the same split as ISO 20022's logical model and its message schemas. Each structure's content (`sequence`, `choice`, `any-of`) is a regular expression over its components, so the model is a *regular tree grammar*, the formalism behind XML Schema.
- **The model as a graph: a directed acyclic graph (DAG).** Structures are defined once and referenced by name, so they form a graph: the structures are the nodes, "has a component of" the edges (`TEAddress → PostalAddress`). It is *directed* (container to contained) and *acyclic*: no structure contains itself, directly or through others, because TS 119 602 defines nothing recursive (other lists are pointed to by URI, `PointersToOtherLoTE`, not embedded). It is not a tree, because structures are shared: `PostalAddress` and `ServiceDigitalIdentity` each have three parents, as the text refers to one definition from several clauses. Sharing is usual in schema languages (XSD named types, JSON Schema `$defs`, ISO 20022 components); having no cycles is typical of record-like exchange formats, not of all (HTML and FHIR `Extension` are recursive). Consequences: the generators' walk from `LoTE` always ends; a shared structure becomes one XSD `complexType` / one `$defs` entry; every list is a finite tree, the DAG unfolded ([explicit_schema.md](schema_generator/explicit/explicit_schema.md) draws it). No test enforces the acyclicity yet.
- **The algorithm: model-to-text transformation.** The generators walk the model and write each binding's schema (*code generation*, MDA's model-to-text step): a structure becomes an XSD `complexType` / a JSON object, `min`/`max` become `minOccurs`/`maxOccurs` / `required` and arrays, value types become simple types. Tracks and profiles are *differentials*: a track's differential is applied to the base to give a *snapshot* (the full model of the track); a profile is generated as an extra *constraint layer* over the track's schema (JSON Schema `allOf`, Schematron assertions next to the XSD). The validator runs the transformation backwards (*traceability*): each schema error is mapped back to its place in the model, and so to the sentence it breaks.
- **Ids as an index (potential use).** Every rule has a stable id that leads to the sentence of the text it enforces: core constraints (`R-English`), track rules (`EXP-SchemeName-required`), profile rules (`D-LoTEType-fixed`, `D-te-tel`, `H-sig-ref-uri`), schema-error ids derived from the model (`<Structure>-<Component>-required`, e.g. `LoTE-LoTETag-required`), and model source ids (`6.6.1/ServiceTypeIdentifier`). The same ids appear in the models, the generated schemas and the validator's findings, and the decisions and defect lists refer to them. They could therefore be collected into an index (rule id → clause or annex row, page, line, quote, where it is checked, related decisions and defects) for semantic indexing, e.g. as context for an AI agent or a skill that explains validation findings. Not built yet; about 600 ids exist today.
- **FHIR profiling, for the annexes.** HL7 FHIR describes a profile as a [StructureDefinition](https://hl7.org/fhir/R4/structuredefinition.html) with `derivation: constraint`, a `baseDefinition` and a `differential` of [ElementDefinitions](https://hl7.org/fhir/R4/elementdefinition.html), each narrowing one `path` (`min`/`max`, `fixed[x]`, `binding`, `constraint` invariants); see [Profiling](https://hl7.org/fhir/R4/profiling.html). Each annex D–I is written this way, as a differential on the explicit track. The idea fits clause 4.7: a profile may only narrow, never relax ("LoTE profile cannot however make the presence of a mandatory component optional or conditioned"). The overlays use FHIR's field names and rules, not FHIR resources, and add their own fields: the citation, a structured `check` for the generator, and `from`/`reason` for WP4 rules. Details: [base/model/README.md](schema_generator/base/model/README.md), [explicit/terminology.md](schema_generator/explicit/terminology.md).

## Profiles

TS 119 602 defines six EU profiles, Annexes D–I. Each narrows the explicit track: fixed URIs, required and prohibited components, extra rules. A list names its profile by its `LoTEType`, which must be exactly the URI of its annex: `lote-validate <list>` applies that profile. `--profile <annex>` is used only for a list whose `LoTEType` names no annex; if the list declares another annex, the declared one is used, with a warning.

| Annex | List of | `LoTEType` | Binding the annex allows | Validate | Files |
|---|---|---|---|---|---|
| D | providers of person identity data (PID) | `http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList` | JSON | `.venv/bin/lote-validate list.json` | `D_pid_providers` |
| E | wallet providers | `…/LoTEType/EUWalletProvidersList` | JSON | `.venv/bin/lote-validate list.json` | `E_wallet_providers` |
| F | providers of wallet relying party access certificates (WRPAC) | `…/LoTEType/EUWRPACProvidersList` | JSON | `.venv/bin/lote-validate list.json` | `F_wrpac_providers` |
| G | providers of wallet relying party registration certificates (WRPRC) | `…/LoTEType/EUWRPRCProvidersList` | JSON | `.venv/bin/lote-validate list.json` | `G_wrprc_providers` |
| H | public sector bodies issuing electronic attestation of attributes (Pub-EAA) | `…/LoTEType/EUPubEAAProvidersList` | JSON or XML | `.venv/bin/lote-validate list.json`<br>`.venv/bin/lote-validate list.xml` | `H_pub_eaa_providers` |
| I | registrars and registers | `…/LoTEType/EURegistrarsAndRegistersList` | JSON | `.venv/bin/lote-validate list.json` | `I_registrars_and_registers` |
| `LoTL` | List of Trusted Lists (no annex) | `http://uri.etsi.org/19602/LoTLType/EUListOfTrustedLists` (WP4) | – | `.venv/bin/lote-validate list.json` (explicit track only) | – |

- **Files:** each profile is an overlay in [schema_generator/explicit/model/profiles/](schema_generator/explicit/model/profiles/) (`<name>.json`), generated into [schema_generator/explicit/generated/profiles/](schema_generator/explicit/generated/profiles/) as `lote_profile_<name>.json` (JSON Schema) and `.sch` (Schematron).
- **XML for D–G and I:** the annexes allow only JSON, but XML profiles are generated for all six, as content checks ([decisions #1](docs/project_decisions_vs_etsi.md#1-xml-profiles-for-annexes-that-allow-only-json)).
- **The List of Trusted Lists (profile `LoTL`):** no annex covers it, so a list with its `LoTEType` (a WP4 value, not in the text) is checked against the explicit track only. Any other `LoTEType`, or none, is an invalid profile: validation stops and lists the seven valid URIs ([decisions #3](docs/project_decisions_vs_etsi.md#3-wp4-lists-are-explicit-the-implicit-track-is-not-used-in-wp4)).

## Commands

Run from the repository root after the Quick start install. Every command has `--help`.

**`lote-validate <list>`**: validate a list (`.xml` or `.json`). Exit code 0 if valid, 1 if there are findings, 2 on a usage error, including an invalid profile (a `LoTEType` that is missing or not one of the seven URIs).

| Flag | Effect |
|---|---|
| (none) | apply the profile the list's `LoTEType` names: an annex D–I, or `LoTL` for the List of Trusted Lists (explicit track only). A missing `LoTEType`, or one that is not exactly one of these seven URIs, stops with `error: invalid profile: … The profiles must be:` and the seven URIs (exit 2) |
| `--profile {D,E,F,G,H,I}` | the annex profile you expect. The list's `LoTEType` decides: if it declares another profile, that one is used, with a warning; if it is invalid, the error above |
| `--lotl` | the same, expecting profile `LoTL` (List of Trusted Lists: explicit track, no annex; a WP4 type). Excludes `--profile` |
| `--explicit` | temporarily not in use, since only the explicit track is used |
| `--json` | print the findings as JSON instead of text |

```bash
.venv/bin/lote-validate list.json --json > report.json
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
