# Explicit track: lists that describe their scheme

ETSI TS 119 602 V1.1.1, clause 6.3.0 and Table 1, explicit column. The list describes the scheme it is issued under, so anyone can use it without outside knowledge: "In case the scheme information is explicit the LoTE shall contain this component" (p. 15, L903). All six EU profiles (Annexes D–I) require explicit lists ("shall comply with the scheme explicit … schema definition", D.1–I.1).

**Do not edit these files.** They are generated from the core model and the explicit differential; regenerate with the commands in [core/generated/README.md](../core/generated/README.md).

## Layout

| Folder | Content | Built by |
|---|---|---|
| [model/lote_model_explicit.json](model/lote_model_explicit.json) | The full model of this track (a snapshot): the core model with [docs/model/schemes/explicit.json](../model/schemes/explicit.json) applied | [build_schemes.py](../src/lote_schema_generator/build_schemes.py) |
| [generated/](generated/) | `lote_core.schema.json` (JSON), `lote_core.xsd` + `lote_tie.xsd` + `lote_sie.xsd` (XML), `lote_core.sch` (Schematron) | [gen_json.py](../src/lote_schema_generator/gen_json.py), [gen_xsd.py](../src/lote_schema_generator/gen_xsd.py) `--scheme explicit` |
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
