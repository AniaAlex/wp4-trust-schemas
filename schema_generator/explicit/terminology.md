# Terminology

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
| `json` / `xml` | a rule for one binding only (`min`, `max`, `name`), with `from` and a `citation`, `reason` or `note` | rare (`Signature`) | project |
| `validation`, `validated_by` | `not-schema-based`: checked by code (the signature layer), not by the schemas | rare (`Signature`) | project |
| `comment` | explanation, e.g. for a derived rule | optional | FHIR |

Each entry of `constraint`:

| Field | Meaning | Origin |
|---|---|---|
| `key` | rule id, reported on failure (e.g. `D-next-6m`) | FHIR `constraint.key` |
| `severity` | always `error`: every rule is a "shall" | FHIR `constraint.severity` |
| `human` | the rule in words, used in messages | FHIR `constraint.human` |
| `expression` | the rule in FHIRPath; `null` when no schema can check it | FHIR `constraint.expression` |
| `checkable` | `yes` / `partly` / `no`, with the reason | project |
| `check` | the rule in a structured form the generator translates to JSON Schema and XPath: `contains`, `min-items`, `months-after` | project |

FHIR's definitions: [ElementDefinition.constraint](https://hl7.org/fhir/R4/elementdefinition-definitions.html#ElementDefinition.constraint) (R4).
