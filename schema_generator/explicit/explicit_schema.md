# Explicit LoTE: structure

The tree of a scheme explicit List of Trusted Entities, as described by [model/lote_model_explicit.json](model/lote_model_explicit.json) (ETSI TS 119 602 V1.1.1, clause 6 with the explicit column of Table 1). Names are the text's names; the JSON and XML bindings may rename or wrap them (see the model's `json` / `xml` entries).

Legend: `1` required · `0..1` optional · `1..n` one or more · `0..n` any number · ★ required by the explicit track (Table 1), optional in the base model · `(type)` value type · `→ X` see structure X below.

```
LoTE  (the list)
├── LoTETag                          1      (uri)
├── ListAndSchemeInformation         1 ★    ── about the list and its scheme
│   ├── LoTEVersionIdentifier        1      (integer)
│   ├── LoTESequenceNumber           1      (positive-integer)
│   ├── LoTEType                     1 ★    (uri)
│   ├── SchemeOperatorName           1      (multilang-texts)
│   ├── SchemeOperatorAddress        1 ★
│   │   ├── PostalAddresses          1      list of → PostalAddress
│   │   └── ElectronicAddress        1      (mailto: + web URI)
│   ├── SchemeName                   1 ★    (multilang)
│   ├── SchemeInformationURI         1 ★    (multilang-uris)
│   ├── StatusDeterminationApproach  1 ★    (uri)
│   ├── SchemeTypeCommunityRules     1 ★    (multilang-uris)
│   ├── SchemeTerritory              1 ★    (country-code)
│   ├── PolicyOrLegalNotice          1 ★    choice: LoTEPolicy 1..n | LoTELegalNotice 1..n
│   ├── HistoricalInformationPeriod  0..1   (non-negative-integer)
│   ├── PointersToOtherLoTE          0..1   list of OtherLoTEPointer
│   │   ├── LoTELocation             1      (uri)
│   │   ├── ServiceDigitalIdentity   1..n   → ServiceDigitalIdentity
│   │   └── LoTEQualifiers           1      list of LoTEQualifier
│   │       └── LoTEType, SchemeOperatorName, SchemeTerritory, MimeType, [SchemeTypeCommunityRules]
│   ├── ListIssueDateTime            1      (utc-datetime)
│   ├── NextUpdate                   1      (utc-datetime)
│   ├── DistributionPoints           0..1   (uri-list)
│   └── SchemeExtensions             0..1   (extensions)
│
├── TrustedEntitiesList              0..1   list of TrustedEntity
│   └── TrustedEntity
│       ├── TrustedEntityInformation 1      ── who
│       │   ├── TEName               1      (multilang-texts)
│       │   ├── TETradeName          0..1   (multilang-texts)
│       │   ├── TEAddress            1
│       │   │   ├── TEPostalAddress      1  list of → PostalAddress
│       │   │   └── TEElectronicAddress  1  (mailto: + web URI)
│       │   ├── TEInformationURI     1      (multilang-uris)
│       │   └── TEInformationExtensions 0..1
│       │       └── ext: OtherAssociatedBodies → AssociatedBody
│       └── TrustedEntityServices    1      list of TrustedEntityService ── what they offer
│           ├── ServiceInformation   1      ── the current state
│           │   ├── ServiceTypeIdentifier       0..1  (uri)
│           │   ├── ServiceName                 1     (multilang-texts)
│           │   ├── ServiceDigitalIdentity      1     → ServiceDigitalIdentity
│           │   ├── ServiceStatus               0..1  (uri)
│           │   ├── StatusStartingTime          0..1  (utc-datetime)
│           │   ├── SchemeServiceDefinitionURI  0..1  (multilang-uris)
│           │   ├── ServiceSupplyPoints         0..1  (typed URIs)
│           │   ├── TEServiceDefinitionURI      0..1  (multilang-uris)
│           │   └── ServiceInformationExtensions 0..1
│           │       └── ext: ServiceUniqueIdentifier
│           └── ServiceHistory       0..1   list of ServiceHistoryInstance ── past states
│               ├── ServiceTypeIdentifier       0..1  (uri)
│               ├── ServiceName                 1     (multilang-texts)
│               ├── ServiceDigitalIdentity      1     → ServiceDigitalIdentity
│               ├── ServiceStatus               1     (uri)
│               ├── StatusStartingTime          1     (utc-datetime)
│               └── ServiceInformationExtensions 0..1
│
└── Signature                        0..1   (XML: ds:Signature; JSON: none, the list is signed by JAdES around it)
```

## Shared structures

```
PostalAddress
├── lang              1     (language-tag)
├── StreetAddress     1     (plain-text)
├── Locality          0..1  (plain-text)
├── StateOrProvince   0..1  (plain-text)
├── PostalCode        0..1  (plain-text)
└── Country           1     (country-code)

ServiceDigitalIdentity  (any-of: at least one)
└── X509Certificate (base64) | X509SubjectName | PublicKeyValue | X509SKI | OtherId    each 0..n

AssociatedBody  (extension OtherAssociatedBodies, in TEInformationExtensions)
├── AssociatedBodyName                  1     (multilang-texts)
├── AssociatedBodyTradeName             0..1  (multilang-texts)
├── AssociatedBodyAddress               0..1
│   ├── AssociatedBodyPostalAddress     1     list of → PostalAddress
│   └── AssociatedBodyElectronicAddress 1     (mailto: + web URI)
├── AssociatedBodyInformationURI        0..1  (multilang-uris)
├── AssociatedBodyTypeIdentifier        0..1  (uri)
└── AssociatedBodyInformationExtensions 0..1
```

## Not allowed in an explicit list

`LoTEVersionIdentifier`, `LoTESequenceNumber`, `SchemeOperatorName`, `ListIssueDateTime` and `NextUpdate` directly under `LoTE`. That placement is only for an implicit list without `ListAndSchemeInformation` (6.3.0, L912); in an explicit list they sit inside `ListAndSchemeInformation`. The model keeps them with `0..0` and a citation, so the validator can say why they are wrong.
