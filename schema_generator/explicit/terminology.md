# Terminology

## Structures, components and value types

The model ([model/lote_model_explicit.json](model/lote_model_explicit.json)) is built from three things. The tree they form, unfolded, is drawn in [explicit_schema.md](explicit_schema.md); this section explains how the file encodes it.

| Term | What it is | In the file | Count |
|---|---|---|---|
| **structure** | an element that has parts: a box | a key under `"structures"`: `"SchemeOperatorAddress": { … }` | 16 |
| **component** | a named part of a structure: a slot, with how often it occurs (`min` / `max`) | an entry in a structure's `"components"` list: `{"name": "SchemeOperatorAddress", …}` | 78 |
| **value type** | the shape of a single value (a date, a URI, a code): a leaf | a key under `"value_types"`: `"country-code": { … }` | 23 |

The text calls all of these "components"; the model separates *where* an element sits (component) from *what* it contains (structure or value type).

### What a component holds

A component holds exactly one of three things:

| The component says | It holds | Count |
|---|---|---|
| `"value": "<value type>"` | a single value | 60 |
| `"structure": "<structure>"` | one box of that structure | 10 |
| `"items": {"structure": "<structure>", "min": 1, "max": "n"}` | a non-empty list of boxes of that structure | 8 |

### Example: SchemeOperatorAddress

The same name appears twice, in two roles:

```json
"ListAndSchemeInformation": {                               ← structure (line 1084)
  "components": [
    { "name": "SchemeOperatorAddress", "min": 1, "max": 1,  ← component: the slot (line 1198), required (★)
      "structure": "SchemeOperatorAddress" }                ← reference to the structure below
  ]
},
"SchemeOperatorAddress": {                                  ← structure: what the slot contains (line 1588)
  "clause": "6.3.5.0", "content": "sequence",
  "components": [
    { "name": "PostalAddresses", "min": 1, "max": 1,
      "items": { "structure": "PostalAddress", "min": 1, "max": "n" } },   ← a list of PostalAddress boxes
    { "name": "ElectronicAddress", "min": 1, "max": 1,
      "value": "electronic-address" }                                       ← a single value
  ]
},
"PostalAddress": {                                          ← structure, shared with TEAddress and AssociatedBodyAddress
  "components": [ { "name": "Country", "value": "country-code-a" }, … ]    ← ends in value types
}
```

| The name appears as … | It is … |
|---|---|
| `"name": "X"` inside a `components` list | the **component** X (where it sits, how often) |
| `"structure": "X"` or `"items": {"structure": "X"}` inside a component | a **reference** to the structure X |
| a key directly under `"structures"`: `"X": { … }` | the **structure** X (what it contains) |

A component and its structure often share a name (`SchemeOperatorAddress`, `ListAndSchemeInformation`, `TEAddress`: 10 cases). A list component is usually named in the plural (`PostalAddresses` → `PostalAddress`, `TrustedEntitiesList` → `TrustedEntity`). Some components use a shared structure under another name (`TEPostalAddress`, `AssociatedBodyPostalAddress` → `PostalAddress`).

### Rules

- **Defined once, referenced by name.** The file is flat: every structure sits directly under `"structures"` and is never written inside another one. The tree emerges from the references, starting at `"root": "LoTE"`.
- **A referenced structure must exist.** A misspelt name stops the build.
- **Sharing is allowed.** `PostalAddress` and `ServiceDigitalIdentity` are used by three components each.
- **No loops.** No structure contains itself, directly or through others; every chain ends in value types. Why this makes the model a directed acyclic graph, not a tree: [README, Concepts](../../README.md#concepts).
- **Two exceptions.** `LoTE` is a structure but no component: it is the root. `AssociatedBody` is held by no component: it is reached through the `OtherAssociatedBodies` extension.

**Why flat.** A shared structure is changed in one place; each structure matches one clause of the text, which refers to definitions the same way ("formatted as specified in clause 6.6.3", 6.3.13 b); and each structure becomes one `$defs` entry in JSON Schema and one `complexType` in XSD.

## Content modes: how a structure combines its components

Every structure in [model/lote_model_explicit.json](model/lote_model_explicit.json) has a `content` mode that says which of its components must or may appear together. There are three modes. Their names are taken from the schema languages: `sequence` and `choice` from XML Schema (XSD), `any-of` from JSON Schema (`anyOf`). The model uses them to describe the text without committing to either syntax.

### Side by side

For two components A and B:

| Mode | Meaning | Source term | Valid | Invalid | Example in the model |
|---|---|---|---|---|---|
| `sequence` | all components, each as often as its own `min` / `max` allows | XSD `xsd:sequence` | with A `1`, B `0..1`: A · A+B | B alone · nothing | `PostalAddress` (6.3.5.1) |
| `choice` | exactly one of the components | XSD `xsd:choice` (JSON Schema `oneOf`) | A · B | A+B · nothing | `PolicyOrLegalNotice` (6.3.11) |
| `any-of` | at least one of the components, in any combination | JSON Schema `anyOf` (XSD has no equivalent) | A · B · A+B | nothing | `ServiceDigitalIdentity` (6.6.3) |

Most structures are a `sequence`; `choice` and `any-of` are used once each.

### As logic operations

| `content` | Logic | Reads as | For components A, B |
|---|---|---|---|
| `sequence` | AND (conjunction) | A **and** B | both, as their own `min` / `max` allow |
| `choice` | XOR (exclusive or) | **either** A **or** B, not both | exactly one |
| `any-of` | OR (inclusive or) | A **or** B **or** both | at least one |

The text uses the same words: "shall contain **either** … **or** …" (6.3.11, `choice`), "**one or multiple** digital identifiers" (6.6.3.0, `any-of`). The match is not exact in three points:

- `sequence` is AND over each component's own `min` / `max`: an optional component (`0..1`) may be absent, so only the required ones are forced. A `sequence` also fixes the element order in XML, which logic does not have.
- `choice` means "exactly one", also with more than two options; a chained XOR (A ⊕ B ⊕ C) would also accept all three. The model's only `choice` has two options.
- Logic says only present or absent; each component adds how many (`1..n`, `0..n`) on top.

### `sequence`: PostalAddress

Every component appears as its own occurrence allows: the required ones always, the optional ones if present.

```
PostalAddress  (sequence)
├── lang              1      language of this address
├── StreetAddress     1      must be there
├── Locality          0..1   may be there
├── StateOrProvince   0..1
├── PostalCode        0..1
└── Country           1      must be there
```

| Binding | Generated as |
|---|---|
| XSD | `<xsd:sequence>` of the elements, in this order; optional ones with `minOccurs="0"`; `lang` as the `xml:lang` attribute |
| JSON | an object with the components as properties; the required ones in `"required": ["lang", "StreetAddress", "Country"]` |

### `choice`: PolicyOrLegalNotice

The list states either its policy or its legal notice, never both and never neither (clause 6.3.11).

```
PolicyOrLegalNotice  (choice)
├── LoTEPolicy        1..n   either: multilingual URIs of the policy
└── LoTELegalNotice   1..n   or: multilingual legal notice texts
```

| Binding | Generated as |
|---|---|
| XSD | `<xsd:choice>` with `LoTEPolicy` and `LoTELegalNotice`, each `maxOccurs="unbounded"` |
| JSON | `oneOf` two arrays: an array of `{"LoTEPolicy": …}` items, or an array of `{"LoTELegalNotice": …}` items (the Forge form); each needs an English entry |

### `any-of`: ServiceDigitalIdentity

A service is identified by at least one identifier; any of them, and several together, are allowed (clause 6.6.3).

```
ServiceDigitalIdentity  (any-of)
├── X509Certificate   0..n   base64
├── X509SubjectName   0..n
├── PublicKeyValue    0..n
├── X509SKI           0..n
└── OtherId           0..n
```

A certificate alone is valid; a certificate with its subject name is valid; no identifier at all is not.

| Binding | Generated as |
|---|---|
| XSD | XSD has no any-of: a `<xsd:sequence>` of one or more `DigitalId` elements, each a `<xsd:choice>` of one identifier |
| JSON | an object with one array per identifier (`X509Certificates`, `X509SubjectNames`, …), each `minItems: 1`, and `minProperties: 1` for "at least one" |

The generated schemas are in [generated/base/](generated/base/): `lote_core.xsd` and `lote_core.schema.json`.

## Profile elements: how a profile narrows the explicit model

A profile overlay ([model/profiles/](model/profiles/), Annexes D–I) does not define structures or value types. Each element of its `differential` points to an existing component of the explicit model by `path` (e.g. `LoTE.ListAndSchemeInformation.LoTEType`), inherits that component's type, and adds one restriction. A profile may only narrow the model, never widen it (clause 4.7).

| Field | Narrowing |
|---|---|
| `min: 1` | required |
| `max: 0` | prohibited |
| `fixedUri` / `fixedString` / `fixedInteger` | one exact value |
| `binding` | one of a set of values |
| `constraint` | a condition (FHIRPath) |
| `json` / `xml` | a rule for one binding only |

### What is not written is inherited

A profile is a **differential**: each element carries only the fields its annex changes. A field that is missing keeps the value the component has in the explicit model. In particular, an element without `min` or `max` keeps the component's occurrence from the model.

| Element | Has `min`? | Why |
|---|---|---|
| `D-LoTEType-fixed` (path `…ListAndSchemeInformation.LoTEType`) | no | `LoTEType` is already `1..1` in the explicit model; Annex D changes only its value (`fixedUri`) |
| `D-PointersToOtherLoTE-required` (path `…ListAndSchemeInformation.PointersToOtherLoTE`) | `min: 1` | the component is `0..1` in the explicit model; Table D.1 makes it required |

FHIR calls the two views **differential** (only what the profile changes, as in our overlays) and **snapshot** (every element with its full definition after the change). The overlays are not written as snapshots: the generator combines the explicit model and the overlay, and the generated profile schema is the snapshot.

### Fields of a profile overlay

The profile as a whole ([model/profiles/D_pid_providers.json](model/profiles/D_pid_providers.json) as example):

| Field | Meaning | Example (Annex D) | Origin |
|---|---|---|---|
| `id` | identifier of the profile | `lote-profile-D` | FHIR |
| `title` | human-readable name | `ETSI TS 119 602 V1.1.1 Annex D - PID providers list` | FHIR |
| `derivation` | always `constraint`: the profile only narrows its base | `constraint` | FHIR |
| `baseDefinition` | the model the profile narrows | `explicit/model/lote_model_explicit.json` | FHIR (a file path here, not a canonical URL) |
| `baseCitation` | the annex sentence that requires an explicit list | quote, page, line of D.1 | project |
| `annex` | annex letter | `D` | project |
| `lotetype` | the LoTE type URI the profile applies to | `http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList` | project |
| `differential.element` | the list of elements, one per annex table row | 24 in Annex D | FHIR |

Each element of `differential.element`:

| Field | Meaning | Required? | Origin |
|---|---|---|---|
| `id` | id of the element's first rule, unique per annex; failures are reported under it | always | FHIR (not path-based here) |
| `row` | the annex table row it comes from | always | project |
| `path` | the component it narrows, as a path in the explicit model | always | FHIR |
| `citation` | `quote`, `page`, `line` of the sentence, found inside the element's own annex | always | project |
| `min` | `1`: the component becomes required | only if changed | FHIR |
| `max` | `0`: the component becomes prohibited | only if changed | FHIR (FHIR writes `"0"` as a string) |
| `fixedUri` / `fixedString` / `fixedInteger` | the component must have exactly this value | only if fixed | FHIR `fixed[x]` |
| `acceptAlso` | an extra accepted value next to the fixed one (Annex G's misspelt `WRPRCrovidersList` URI) | rare | project |
| `binding` | `strength: "required"` and a `valueSet` (inline list of values): the value must be one of them | only if restricted | FHIR (inline list, not a ValueSet URL) |
| `constraint` | conditions on the component (see below) | only if any | FHIR |
| `json` / `xml` | a rule for one binding only (`min`, `max`, `name`), with `from` and a `citation`, `reason` or `note`; `xml` may hold a `constraint` list: rules on the XML element itself, each with an `xpath` (the H.4 signature checks) | rare (`Signature`) | project |
| `validation`, `validated_by` | `not-schema-based`: checked by code (the signature layer), not by the schemas | rare (`Signature`) | project |
| `comment` | explanation, e.g. for a derived rule | optional | FHIR |

Each entry of `constraint`:

| Field | Meaning | Origin |
|---|---|---|
| `key` | rule id, reported on failure (e.g. `D-next-6m`) | FHIR `constraint.key` |
| `severity` | always `error`: every rule is a "shall" | FHIR `constraint.severity` |
| `human` | the rule in words, used in messages | FHIR `constraint.human` |
| `expression` | the rule in FHIRPath; `null` when no schema can check it | FHIR `constraint.expression` |
| `checkable` | `{status, instrument, reason, note}`, `null` where not applicable: `status` yes when code can decide the rule from the list alone; `instrument` per binding `{xml, json}` from `checkable_instruments` (what checks it; `not-applicable` where the rule does not exist in the binding); `reason` from `checkable_reasons` (why not) | project |
| `check` | the rule in a structured form the generator translates to JSON Schema and XPath: `contains`, `min-items`, `months-after` | project |
| `xpath` | the rule as an XPath 1.0 test from the constrained element; only in an `xml.constraint` (XML only) | FHIR R4 `constraint.xpath` |
| `row`, `citation` | the constraint's own annex row and sentence, when it is not the element's (e.g. `D-sig-ref-uri` cites H.4) | project |
| `from`, `reason` | `text`, or `wp4` with the reason: a WP4 rule, not the annex's (its message starts with "WP4 rule") | project |

FHIR's definitions: [ElementDefinition.constraint](https://hl7.org/fhir/R4/elementdefinition-definitions.html#ElementDefinition.constraint) (R4).
