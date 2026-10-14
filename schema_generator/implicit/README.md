# Implicit track: lists whose scheme is known out of band

ETSI TS 119 602 V1.1.1, clause 6.3.0 and Table 1, implicit column. The scheme is known to all parties by other means, so the list carries only the minimum about itself: "Scheme information can be implicitly known when, for instance, it is provided through another means, or the context of the transactions itself within which the LoTE is consumed assumes a specific scheme known by all parties" (p. 15, L897). Typical use: closed communities, pilots, internal lists. No EU profile uses this track, and Annex A provides no ETSI binding for it; these schemas are this project's binding, as clause 4.6 allows ("Different bindings can be defined, for instance, for an implicit scheme information compared to an explicit scheme information").

**Do not edit these files.** They are generated from the core model and the implicit differential; regenerate with the commands in [core/generated/README.md](../core/generated/README.md).

## Layout

| Folder | Content | Built by |
|---|---|---|
| [model/lote_model_implicit.json](model/lote_model_implicit.json) | The full model of this track (a snapshot): the core model with [docs/model/schemes/implicit.json](../model/schemes/implicit.json) applied | [build_schemes.py](../src/lote_schema_generator/build_schemes.py) |
| [generated/](generated/) | `lote_core.schema.json` (JSON), `lote_core.xsd` + `lote_tie.xsd` + `lote_sie.xsd` (XML), `lote_core.sch` (Schematron) | [gen_json.py](../src/lote_schema_generator/gen_json.py), [gen_xsd.py](../src/lote_schema_generator/gen_xsd.py) `--scheme implicit` |

## Two forms of an implicit list

Clause 6.3.0 allows both (L901, L912, L970):

```xml
<!-- with the component: it contains at least the five list elements -->
<ListOfTrustedEntities LoTETag="…"><ListAndSchemeInformation>
  <LoTEVersionIdentifier>1</LoTEVersionIdentifier> … <NextUpdate>…</NextUpdate>
</ListAndSchemeInformation> …</ListOfTrustedEntities>

<!-- without it: the five list elements directly in the list -->
<ListOfTrustedEntities LoTETag="…">
  <LoTEVersionIdentifier>1</LoTEVersionIdentifier> <LoTESequenceNumber>…</LoTESequenceNumber>
  <SchemeOperatorName>…</SchemeOperatorName> <ListIssueDateTime>…</ListIssueDateTime> <NextUpdate>…</NextUpdate>
…</ListOfTrustedEntities>
```

In JSON, the same keys sit in `ListAndSchemeInformation` or directly in `"LoTE"`. The rule `R-SchemeInfoPlacement` allows one form or the other, never both. Where the elements go when the component is absent is not defined by any ETSI binding; this placement (in the component's position, under the root) is this project's choice.

## What the implicit differential changes

| Component | Change | Source |
|---|---|---|
| `SchemeName`, `SchemeInformationURI`, `StatusDeterminationApproach`, `SchemeTypeCommunityRules`, `PolicyOrLegalNotice` | not allowed | Table 1, "/" in the implicit column (L997–L1002) |

`LoTEType`, `SchemeOperatorAddress` and `SchemeTerritory` stay optional ("O"). Because the forbidden elements are absent from the schemas, the core rule `R-Table1` cannot fire here: the snapshot lists it under `superseded`.

## Validate

```bash
lote-validate list.json --implicit
lote-validate list.json      # without a flag: inferred from the content
```
