# LoTE data model

> **Frozen since 2026-10-15.** This model, the differentials in [schemes/](schemes/) and the implicit track no longer change; the explicit track is edited directly in [explicit/model/lote_model_explicit.json](../../explicit/model/lote_model_explicit.json). See [project_decisions_vs_etsi.md #4](../../../docs/project_decisions_vs_etsi.md#4-the-base-model-and-the-implicit-track-are-frozen-the-explicit-track-is-edited-directly). The text below describes the model as frozen; its conventions apply to the explicit model as well.

[lote_model.json](lote_model.json) is the machine-readable abstract data model of ETSI TS 119 602 V1.1.1 (2025-11): every component of the text with its parent, occurrence, value type and citation, independent of XML or JSON. It is meant as the single source from which both bindings (core JSON Schema and core XSD) can be generated.

Written by hand (with Claude's help) and proofread against the text, [docs/spec/ts_119602v010101p.txt](../../../docs/spec/ts_119602v010101p.txt): every quote, page and line in a `source` or `citation` is checked by reading it there. The same applies to the track differentials ([schemes/](schemes/)) and the profile overlays ([explicit/model/profiles/](../../explicit/model/profiles/)). The track models ([explicit/model/](../../explicit/model/), [implicit/model/](../../implicit/model/)) are derived from this model and the differentials by [derive_tracks.py](../derive_tracks.py); do not edit them. The schemas are generated from these files:

```bash
cd schema_generator && .venv/bin/lote-schemas build
```

## Contents

| Section | Content |
|---|---|
| `value_types` | 23 value types defined once (`uri`, `utc-datetime`, `multilang-texts`, `base64`, `country-code`, `open`, …), each with its source in the text. |
| `structures` | 16 structures (`LoTE`, `ListAndSchemeInformation`, `PostalAddress`, `ServiceInformation`, …) and their 83 components, in the order of the text. `LoTE` holds `ListAndSchemeInformation` (optional) and, for implicit lists without it, the five list elements directly (clause 6.3.0). |
| `extensions` | `OtherAssociatedBodies` and `ServiceUniqueIdentifier`, with the extension list they plug into. |
| `constraint` (on a structure) | 11 rules across components, each on the structure it constrains, in the same format as the profile overlays' constraints (see Constraints below). |

A component (an entry of a structure's `components`) looks like this:

```json
{
  "name": "X509Certificate",
  "min": 0, "max": "n",
  "value": "base64",
  "json": {"name": "X509Certificates", "form": "array"},
  "source": {"id": "6.6.3.1/X509Certificate", "citations": [{"quote": "The X509Certificate component shall be a Base64 string.", "page": 34, "line": 2166}]}
}
```

## Conventions

- **Precedence: the text first; for element order, Forge.** What a list contains, how many times and with which values is decided by the text of TS 119 602: it prevails over the Annex A schemas ("the present document shall prevail as the authoritative source", A.1 and A.2.1). Where the text and Forge disagree on content, we follow the text and record Forge's error in [forge/errors.md](../../reference/forge/errors.md) (e.g. the mandatory `LoTETag`, certificates as plain Base64). The **order** of XML elements is a matter of the binding, not of the text, which only lists components: there we follow the Forge XSD, so XML lists are interchangeable with lists written to ETSI's schema. Where Forge's order differs from the text's listing, the structure records it as `xml.order` with `from: "forge-xsd"` and the Forge text as evidence; today one structure: `OtherLoTEPointer`, where Forge puts `ServiceDigitalIdentities` before `LoTELocation` (the text lists the location first, 6.3.13 a, b). JSON objects have no order.
- **Names** are the text's names. A `json` or `xml` entry records where a binding uses another name or form (plural arrays in JSON, attributes and wrappers in XML).
- **Structures and components:** a structure is the content of a text component (e.g. `PostalAddress`); its `components` are the text components it contains, each in its place with its occurrence (`min` / `max`). One structure can be used by several components: `PostalAddress` is the structure of `PostalAddresses`, `TEPostalAddress` and `AssociatedBodyPostalAddress`.
- **Occurrence:** `min` / `max`, with `max: "n"` for unbounded. A component with `items` holds a non-empty sequence of those items.
- **Content** of a structure: `sequence` (components in order), `choice` (exactly one), `any-of` (at least one).
- **Where a binding comes from:** every `json` / `xml` override says its source in `from`, so a reader can tell the text's requirements from the syntax choices:

  | `from` | Meaning | Proof | Overrides |
  |---|---|---|---|
  | `forge-xsd` | Taken from ETSI's XML binding (Annex A.2.1) | `forge`: the text found in [forge/1960201_xml_schema/](../../reference/forge/1960201_xml_schema/), e.g. `name="DigitalId"`, the element order of `OtherLoTEPointer` | 13 |
  | `forge-json` | Taken from ETSI's JSON binding (Annex A.1) | `forge`: the text found in [forge/1960201_json_schema/](../../reference/forge/1960201_json_schema/), e.g. `"X509Certificates"` | 9 |
  | `text` | Required by the spec text, where Forge differs | `citation`: verified quote, page and line (`NextUpdate` may be null, 6.3.15) | 2 |
  | `project` | Our own decision | `reason` | 0 (the last one, `LoTETag` optional in JSON, was removed on 2026-10-09: the text prevails) |

  The counts include the copies on the five list elements that an implicit list may place directly in the list (`NextUpdate` brings its two overrides).

  Any override may also carry a supporting quote from the text, as `citation` (e.g. the XML `Signature` note that the text also allows an enveloping signature, 6.8.0, line 2417).

  Where we keep Forge's form but not its name, the override says so in `note` (Forge's attribute is `LOTETag`, the text's is `LoTETag`).
- **Text contradictions:** JSON follows the Forge JSON name, XML the Forge XML name (e.g. `TEServiceDefinitionURI` → JSON `ServiceDefinitionURI`).
- **Interpretations** that apply to one binding only are overrides with a reason and `from: "project"`. None is in use: `LoTETag` used to be optional in JSON (interpretation 3) and is now required in both bindings, as clause 5 says.
- **Validation outside the schemas:** a component with `"validation": "not-schema-based"` is only placed by the model (where it may sit, how often); its content is checked by code named in `validated_by`, not by the generated schemas. Today: `Signature`. In XML the schemas allow `ds:Signature` in the list (the enveloped form, 6.8.1); in JSON the component is not part of the binding (`json.max: "0"`, from the text): JAdES provides no relationship for a signature within the LoTE (6.8.0, line 2417), so a JSON list is signed by encapsulation, as compact JAdES in the EU profiles (D.4–I.4, H.4). Envelope, header, signing certificate and cryptographic check are the validator's signature layer.
- **Constraints:** rules across components are `constraint` entries on the structure they constrain, in the format of the profile overlays: FHIR's invariant fields `key`, `severity`, `human`, `expression` (FHIRPath), plus the project's `clause`, `checkable`, `check` and the citation. A constraint with a `check` is translated by the generators, by check type; one without is a rules-layer requirement, listed in the generated schemas and not enforced:

  | Structure | Constraint | Check → JSON / XML | Checkable |
  |---|---|---|---|
  | `LoTE` | `R-English` (6.1.4): every multilingual sequence has an `en` entry | `has-entry` → `contains` / Schematron | yes |
  | `LoTE` | `R-SchemeInfoPlacement` (6.3.0): the list information in `ListAndSchemeInformation` or directly in the list, never both | `either-or` → `oneOf` / Schematron | yes |
  | `LoTE` | `R-TrustedEntitiesPresence` (6.4.0) | — | no: depends on approvals outside the list |
  | `LoTE` | `R-SignerMatchesOperator` (6.8.0) | — | partly: needs the signing certificate decoded |
  | `ListAndSchemeInformation` | `R-Table1` (6.3.0): explicit scheme information | `co-occurrence` → `if`/`then` / Schematron | yes |
  | `ListAndSchemeInformation` | `R-SequenceIncrease` (6.3.2) | — | partly: needs the previous list |
  | `ListAndSchemeInformation` | `R-NextUpdateAfterIssue` (6.3.15) | — | yes, not generated yet |
  | `TrustedEntityService` | `R-HistoryOrder` (6.4.4) | — | yes, not generated yet |
  | `ServiceInformation` | `R-StatusWithHistory` (6.6.0) | `required-if` → `if`/`then` / Schematron | yes |
  | `ServiceInformation` | `R-StatusNotRetroactive` (6.6.5) | — | partly: needs the previous list |
  | `ServiceDigitalIdentity` | `R-PKIIdentity` (6.6.3.0) | — | partly: whether PKI is used is not stated |

  All have `severity: "error"` (every one is a "shall"). The core Schematron also has three patterns that are not model constraints yet: lower-case language tags (6.1.4), no `GB`/`GR` (6.1.5) and `mailto:` + web-site entries in electronic addresses (6.3.5.2); in JSON these are part of the value types.
- **Pending decision:** the scheme operator address uses the text names `PostalAddresses` / `ElectronicAddress`; the current core JSON uses `SchemeOperatorPostalAddress` / `SchemeOperatorElectronicAddress` (`json.current_name`).

## Proofreading checklist

Nothing checks the models automatically any more; when editing one, check by hand that:

- every structure, value type and source reference resolves, and every quote is found verbatim in the text, at the page and line given;
- constraint keys are unique; a constraint's `check` has a known type (`co-occurrence`, `required-if`, `has-entry`), names components of its structure and comes with an `expression`;
- every `json` / `xml` override has a `from`; Forge evidence is found in the Forge schema files, `text` overrides have a quote, `project` overrides a reason;
- the track models are rebuilt (`lote-schemas build` runs [derive_tracks.py](../derive_tracks.py) first), never edited by hand.

The generators still stop on what they cannot read (an unknown value type or check type), and the tests in [tests/](../../tests/) hold the generated schemas to the text's cases.

## Generated from the model

[gen_json.py](../../src/lote_schema_generator/gen_json.py) and [gen_xsd.py](../../src/lote_schema_generator/gen_xsd.py) generate the JSON Schema, the XSD (with the two extension schemas) and the Schematron rules, with `--scheme base|explicit|implicit`: the core (both kinds of list) into [base/generated/](../generated/), each track into its own folder (see Tracks below). The generated core JSON passes the same 76 core tests as the hand-written schema; the generated XSD + Schematron pass 30 XML tests and score 67/67 in the checker. See [base/generated/README.md](../generated/README.md).

[gen_profiles_from_model.py](../../src/lote_schema_generator/gen_profiles_from_model.py) generates the six profiles from the explicit track and the overlays in [profiles/](../../explicit/model/profiles/): JSON Schema and Schematron, into [explicit/generated/profiles/](../../explicit/generated/profiles/). Both pass the same 162 profile cases; the XML side has 30 more, for the 6-month `NextUpdate` rule (192). Each checkable invariant carries a structured `check` that the generator translates to JSON `contains` / `minItems` and to XPath. The `months-after` check (`NextUpdate` at most 6 months after `ListIssueDateTime`) compares two values, which JSON Schema cannot do: it becomes a Schematron assertion and, in the JSON profile, a `$comment` entry.

## Lightweight 

ISO 20022 and FHIR

## Tracks: explicit and implicit scheme information

Clause 6.3.0 and Table 1 distinguish lists that describe their scheme (**explicit**) from lists whose scheme is known out of band (**implicit**); clause 4.6 foresees a binding for each. The core model allows both; each kind is a **track**: a differential on the core, as the profiles are, and a snapshot (the full model of the track), from which the track's schemas are generated. The differential is written by hand; the snapshot is derived from the core and the differential by [derive_tracks.py](../derive_tracks.py), the first step of `lote-schemas build`.

| Track | Differential | Snapshot | Schemas | What it changes |
|---|---|---|---|---|
| Explicit | [schemes/explicit.json](schemes/explicit.json) | [explicit/model/](../../explicit/model/) | [explicit/generated/base/](../../explicit/generated/base/) (+ [profiles](../../explicit/generated/profiles/) D–I) | `ListAndSchemeInformation` and the eight explicit-only components required (L903, L981, Table 1); the direct placement not allowed |
| Implicit | [schemes/implicit.json](schemes/implicit.json) | [implicit/model/](../../implicit/model/) | [implicit/generated/](../../implicit/generated/) | the five components marked "/" in Table 1 not allowed; `ListAndSchemeInformation` optional, the list information may sit directly in the list (L901, L912) |

- **Snapshot:** `min` raises the occurrence, `max: "0"` keeps the component with `max: 0` (the generators leave it out, so the track's schemas do not allow it); a changed component, required or forbidden, records the rule in `scheme` (id, row, citation), so a validation report cites Table 1. Core constraints the track's structure already decides move to `superseded` (explicit: `R-Table1`, `R-SchemeInfoPlacement`; implicit: `R-Table1`).
- **When editing:** every quote is found exactly once in the text. `derive_tracks.py` stops (and writes nothing) if a path does not resolve, a change would touch a structure used more than once, an element widens the core or has no citation.
- **Validation:** [tools/lote_validate.py](../../../schema_validator/src/lote_schema_validator/validate.py) `--explicit` / `--implicit`, or the track inferred from the content; `--profile` implies `--explicit`.
- **Text reading:** clause 6.3.0 is read as consistent: an implicit list need not contain `ListAndSchemeInformation` (L901); without it, the five list elements sit directly in the list (L912); with it, it contains at least those five (L970). The placement of the direct elements is not defined by any ETSI binding (Annex A binds explicit lists only); the tracks place them in the component's position under the root.

## Profiles (Annexes D–I)

Each profile is an **overlay** on the explicit track (every annex requires a scheme explicit list, D.1–I.1): it lists only what its annex changes, one element per table row. Its `baseDefinition` is the explicit model, [explicit/model/lote_model_explicit.json](../../explicit/model/lote_model_explicit.json), and `baseCitation` quotes the annex sentence that requires it. Written by hand.

| File | Content |
|---|---|
| [registered_uris.json](registered_uris.json) | Annex C.2 as value sets: LoTE types, status determination approaches, scheme type/community/rules (6 URIs each, each quoted from Annex C). |
| [profiles/D_pid_providers.json](../../explicit/model/profiles/D_pid_providers.json) … [profiles/I_registrars_and_registers.json](../../explicit/model/profiles/I_registrars_and_registers.json) | One differential per annex, 23–28 elements each (the eight explicit-only components are required by the explicit track, not repeated per annex). |

### Semantics

The overlays follow FHIR profiling: a profile has `derivation: "constraint"`, a `baseDefinition` (the explicit model) and a `differential` of elements, each addressing a `path` in that model. An element may only **narrow** the base, exactly as clause 4.7 requires ("LoTE profile cannot however make the presence of a mandatory component optional or conditioned"). The files use FHIR's field names and rules; they are not FHIR resources.

| Element field | Meaning | FHIR | ISO 20022 usage guideline | Rule id in the generated schemas |
|---|---|---|---|---|
| `min: 1` | must be present (optional in the core) | `ElementDefinition.min` | restriction of multiplicity | `<annex>-<component>-required` |
| `max: 0` | must not be present | `ElementDefinition.max = "0"` | element removed (multiplicity 0) | `<annex>-<component>-prohibited` |
| `fixedUri` / `fixedInteger` / `fixedString` | must have exactly this value | `fixed[x]` | fixed value | `<annex>-<component>-fixed` |
| `binding` (`strength: "required"`, `valueSet`) | must be one of these values | `binding` to a ValueSet | restriction of a code set | `<annex>-<component>-values` |
| `constraint` with an `expression` | a checkable condition, in FHIRPath, evaluated from the element at `path` | invariant (`key`, `severity`, `human`, `expression`) | usage rule | the constraint `key` |
| `constraint` with `expression: null` | a requirement no schema can check (`checkable`: yes / partly / no, with the reason) | invariant without expression | textual usage rule | the constraint `key` (listed, not checked) |

Every element carries the table `row` and a `citation` (quote, page, line) found **inside its own annex**: most sentences repeat across the six annexes, so a document-wide search would cite the wrong one.

#### FHIR vs project fields

The overlays take FHIR's profiling fields where FHIR has one, and add their own fields for traceability to the text and for generating schemas. What an element does is read from these FHIR fields alone; there is no separate label (an earlier `kind` label repeated the FHIR fields and was removed, as was the `kind` of the core model's former `rules` list, now constraints in this same format). A **rules-layer** requirement is a `constraint` with `expression: null`: the project's name for it; its nearest equivalents are a FHIR invariant without an expression and an ISO 20022 textual rule.

**From FHIR** (`StructureDefinition` / `ElementDefinition`)

| Field | Where | Notes / deviation from FHIR |
|---|---|---|
| `id`, `title` | profile | as in FHIR |
| `derivation` | profile | always `"constraint"` |
| `baseDefinition` | profile | a file path (`explicit/model/lote_model_explicit.json`, the explicit track, itself a narrowing of the base model), not a canonical URL |
| `differential.element` | profile | as in FHIR |
| `id` | element | FHIR `ElementDefinition.id`, but not path-based: the id of the element's first rule (`D-LoTEType-fixed`, or the constraint key such as `D-te-tel`); unique per annex. The generated schemas report failures under these ids |
| `path` | element | a path in the LoTE model (`LoTE.ListAndSchemeInformation.LoTEType`), not in a FHIR resource |
| `min`, `max` | element | `max: 0` = prohibited, as FHIR's `max = "0"`; both are numbers here (FHIR writes `max` as a string) |
| `fixedUri`, `fixedInteger`, `fixedString` | element | FHIR `fixed[x]` |
| `binding.strength`, `binding.valueSet` | element | `strength` is always `"required"`; `valueSet` is an inline list of codes, not a ValueSet URL |
| `constraint.key`, `.severity`, `.human`, `.expression` | element | FHIR invariant; `severity` is always `"error"` (every rule is a "shall"); `expression` is FHIRPath over the LoTE model, `null` when no schema can check it |
| `comment` | element | as in FHIR; used for derived rules (e.g. `ServiceHistory` forbidden because history isn't kept) |

**Added for this project**

| Field | Where | Purpose |
|---|---|---|
| `annex` | profile | Annex letter (D–I) |
| `lotetype` | profile | The LoTE type URI the profile applies to |
| `row` | element | The annex table row the element comes from (e.g. `Table D.1 LoTE sequence number`) |
| `citation` | element | Verbatim quote, page and line, found inside the element's own annex |
| `acceptAlso` | element | An extra accepted value next to a fixed value; used once, for the misspelt `WRPRCrovidersList` URI in Annex G |
| `constraint.checkable` | constraint | Whether code could check the rule: `{"status", "instrument", "reason", "note"}`, every field present, `null` where it does not apply. `status`: `yes` when code can decide the rule from the list alone, `no` otherwise. `instrument`: per binding, `{"xml": ..., "json": ...}`, each a key of the explicit model's `checkable_instruments` (`schematron`, `json-schema`, `code`, `signature-verifier`, `not-applicable`): what checks a `yes` rule, or the part of a `no` rule its `check` covers; `null` for a `no` rule without a check. `not-applicable` marks a rule that does not exist in that binding: the XML-only `ds:Signature` rules (`X-sig-ref-uri`, `-transforms`, `-c14n`) have `json: "not-applicable"`, as a JSON list is signed by encapsulation (6.8.0). `reason`: a key of `checkable_reasons` (e.g. `list-history`, `official-records`), why a `no` rule cannot be decided; `null` for `yes`. `note`: detail, or `null`. The frozen base and implicit models keep the earlier text form (`partly: needs the list history`). |
| `constraint.check` | constraint | The rule in a small structured form (`contains`, `min-items`) that the generator turns into JSON Schema and XPath; FHIR would rely on `expression` alone |
| `json`, `xml` | element | A rule of one binding only, as in the core model: `min` / `max` / `name` for JSON or XML, with `from` (`text` with a `quote` found in the annex, `wp4` or `project` with a `reason`). Used on `LoTE.Signature`: JSON from x.4 (signed by encapsulation, no Signature component), XML from H.4 for H (required) and a WP4 decision for D–G and I. Rule ids `<annex>-<component>-<xml|json>-<required|prohibited>` |
| `validation`, `validated_by` | element | `not-schema-based`, as on the core `Signature`: checked by the validator's signature layer |

### When editing

Check by hand that:

- every quote is found in its own annex (Annex C for registered URIs);
- every `path` resolves in the core model;
- every element only narrows the core (no lower `min`, no higher `max`, no prohibited mandatory component);
- every fixed LoTE type, status determination approach and scheme rules URI is registered in Annex C;
- every element agrees with the generated profile schema in [core/profiles/](../../reference/handwritten/profiles/) (`const`, `enum`, `required`, `not: {}`).
- every rule id (element ids and constraint keys) is unique within its annex.

### Findings while building them

- **F.3 and G.3 do not require** the certificates to certify the TEName. They ask only for, "where applicable, the information required to distinguish" access (registration) certificates from other certificates. The generated F and G profile schemas list "the certificates certify the TEName" in their `$comment`: that item is wrong and should change in the earlier `gen_profiles.py`.
- **Table G.1** fixes the status determination approach to the text's misspelt URI `WRPRCrovidersList`, which is also how Annex C registers it. The overlay records the text; the generated G profile schema also accepts the corrected spelling ([etsi_defects.md](../../../docs/etsi_defects.md) #13).
- **No history in D, E, F, G, I** is a derived rule: the annexes forbid `HistoricalInformationPeriod`, and clause 6.4.3 then forbids `ServiceHistory`. It is marked as derived in the element's `comment`.
