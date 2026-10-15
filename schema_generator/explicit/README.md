# Explicit track: lists that describe their scheme

ETSI TS 119 602 V1.1.1, clause 6.3.0 and Table 1, explicit column. The list describes the scheme it is issued under, so anyone can use it without outside knowledge: "In case the scheme information is explicit the LoTE shall contain this component" (p. 15, L903). All six EU profiles (Annexes D–I) require explicit lists ("shall comply with the scheme explicit … schema definition", D.1–I.1).

The model in [model/](model/) is **the source of this track and is edited by hand** (since 2026-10-15; the base model and the implicit track are frozen, see [project_decisions_vs_etsi.md #4](../../docs/project_decisions_vs_etsi.md#4-the-base-model-and-the-implicit-track-are-frozen-the-explicit-track-is-edited-directly)). It started as the core model with the explicit column of Table 1 applied; its `scheme` entries still record those changes. **Do not edit [generated/](generated/)**: regenerate it with the commands in [base/generated/README.md](../base/generated/README.md).

## Layout

| Folder | Content | Made by |
|---|---|---|
| [model/lote_model_explicit.json](model/lote_model_explicit.json) | The full model of this track (a snapshot): the core model with [base/model/schemes/explicit.json](../base/model/schemes/explicit.json) applied, now edited directly | by hand |
| [generated/base/](generated/base/) | `lote_core.schema.json` (JSON), `lote_core.xsd` + `lote_tie.xsd` + `lote_sie.xsd` (XML), `lote_core.sch` (Schematron) | [gen_json.py](../src/lote_schema_generator/gen_json.py), [gen_xsd.py](../src/lote_schema_generator/gen_xsd.py) `--scheme explicit` |
| [explicit_schema.md](explicit_schema.md) | The structure of an explicit list, drawn as a tree | by hand |
| [terminology.md](terminology.md) | How the model is built (structures, components, value types); content modes (`sequence`, `choice`, `any-of`) with examples and their XSD / JSON form; the fields a profile element uses to narrow the model | by hand |
| [known_gaps.md](known_gaps.md) | Open issues in the explicit track, with risk and proposed fix | by hand |
| [model/profiles/](model/profiles/) | The annex D–I overlays (FHIR-style differentials on this track) | by hand |
| [generated/profiles/](generated/profiles/) | The six EU profiles D–I, JSON and Schematron, built on this track | [gen_profiles_from_model.py](../src/lote_schema_generator/gen_profiles_from_model.py) |

## What the explicit differential changes

| Component | Change | Source |
|---|---|---|
| `ListAndSchemeInformation` | required | 6.3.0, L903 |
| `LoTEType`, `SchemeInformationURI`, `StatusDeterminationApproach`, `SchemeTypeCommunityRules`, `SchemeTerritory`, `PolicyOrLegalNotice` | required | 6.3.0 Semantics, L981 |
| `SchemeOperatorAddress`, `SchemeName` | required | Table 1 only (L996, L997); the Semantics paragraph omits them ([etsi_defects.md](../../docs/etsi_defects.md) #19) |
| the five list elements directly in the list | not allowed | derived: the direct placement (L912) is only for a list without `ListAndSchemeInformation` |

Because these are structure here (required or absent elements), the core rules `R-Table1` and `R-SchemeInfoPlacement` are not needed: the snapshot lists them under `superseded`.

## Validate

```bash
lote-validate list.json --explicit
lote-validate list.xml --profile D      # a profile implies --explicit
```
