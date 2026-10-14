# Defects in ETSI TS 119 602 V1.1.1 (2025-11)

These defects in the text of ETSI TS 119 602 V1.1.1 were found while deriving JSON Schemas from it. Each entry gives the location, the exact text, the problem and a suggested correction.

- **Source text:** [ts_119602v010101p.txt](../schema_generator/spec/ts_119602v010101p.txt), extracted from [ts_119602v010101p.pdf](../schema_generator/spec/ts_119602v010101p.pdf). Links like `L796` open the line.
- **Found during:** the audit of the base schema (defects 1–12), the audit of the profile schemas (defects 13–16), the review of the Forge bindings (defects 17–18) and the review of implicit and explicit scheme information (defect 19).

| # | Category | Location | Impact on implementations |
|---|---|---|---|
| 1 | Wrong cross-reference | 6.1.2, 6.3.3 | Low: readers look in the wrong annex |
| 2 | Wrong cross-reference | 6.1.4 | Low: readers look in the wrong annex |
| 3 | Wrong cross-reference | 6.6.3.0 | Low |
| 4 | Undefined placement | 6.3.0, Annex A | **Medium:** where the list information goes in an implicit list without `ListAndSchemeInformation` |
| 5 | Contradiction | 6.6.0 vs 6.6.3.0 | **Medium:** what a PKI-based service identity must contain |
| 6 | Inconsistent name | 6.3.0 / Table 1 vs 6.3.13 | **Medium:** property name in bindings |
| 7 | Inconsistent name | 6.6.0 vs 6.6.7 | **Medium:** property name in bindings |
| 8 | Inconsistent name | 6.6.0 vs 6.6.8 | **High:** lists using one name are rejected by schemas using the other |
| 9 | Inconsistent name, typos | 6.5.5.1.1, 6.5.5.1.4, 6.5.5.1.5 | **Medium:** property names in bindings |
| 10 | Missing content | 6.6.3.4 | **High:** the X509SKI format and meaning are undefined |
| 11 | Garbled wording | 6.3.7 | Low |
| 12 | Undefined value | 6.3.15 | **Medium:** a closed list can't use a registered "expired" status |
| 13 | Typo in a registered URI | Table G.1, Annex C.2.2 | **High:** exact URI matching fails |
| 14 | Inconsistent placement | Table H.2 | **Medium:** where validators look for the country URI |
| 15 | Missing quotation mark | Table F.3 | Low |
| 16 | Wrong description | Tables G.3, H.3 | Low |
| 17 | Undefined term, missing binding | 3.1, 4.6, 6.3.0, Annex A, D.1–I.1 | **Medium:** "scheme explicit" is a requirement in every profile but never defined; implicit lists have no binding |
| 18 | Contradiction | 6.6.3.1 vs Annex A and D.1–I.1 | **High:** every profile list breaks either the text or the mandated JSON schema |
| 19 | Contradiction | 6.3.0 Semantics vs Table 1 | **Medium:** whether an explicit list must contain `SchemeOperatorAddress` and `SchemeName` |
| 20 | Missing value, missing binding | 6.2, clause 5 vs Annex A.1 | **Medium:** the mandatory LoTE tag has no registered value, and the mandated JSON schema has no place for it |

---

## Clauses 5–6 (core data model)

### 1. Registered URIs referred to as Annex H instead of Annex C

**Location.** 6.1.2 ([L796](../schema_generator/spec/ts_119602v010101p.txt#L796), [L802](../schema_generator/spec/ts_119602v010101p.txt#L802)) and 6.3.3 ([L1071](../schema_generator/spec/ts_119602v010101p.txt#L1071)).

> "These common names are linked to their declaration in Annex H, which formally states all specific URIs used in the present document…"
>
> "Information on URI registration can be found in Annex H."
>
> "A list of registered LoTE type is provided in Annex H."

**Problem.** The registered URIs are in Annex C ("Registered Uniform Resource Identifiers"). Annex H is the profile for Pub-EAA providers.

**Suggested correction.** Replace "Annex H" with "Annex C" in all three places.

### 2. Multilingual rules referred to as Annex G instead of Annex B

**Location.** 6.1.4 ([L820](../schema_generator/spec/ts_119602v010101p.txt#L820), [L851](../schema_generator/spec/ts_119602v010101p.txt#L851)).

> "…using the 'en' language code as specified in IETF RFC 5646 [11] and Annex G."
>
> "Further detailed requirements regarding multilingual implementation are specified in normative Annex G."

**Problem.** The multilingual rules are in Annex B ("Implementation requirements for multilingual support"). Annex G is the profile for WRPRC providers.

**Suggested correction.** Replace "Annex G" with "Annex B" in both places.

### 3. TE name referred to as clause 6.4.1 instead of 6.5.1

**Location.** 6.6.3.0 ([L2157](../schema_generator/spec/ts_119602v010101p.txt#L2157)).

> "The value of that organizationName attribute should strictly match the 'TE Name' value (clause 6.4.1)."

**Problem.** Clause 6.4.1 is "Trusted entity". TE name is defined in clause 6.5.1.

**Suggested correction.** "(clause 6.5.1)".

### 4. Implicit scheme information without the component: where do the elements go?

**Location.** 6.3.0 ([L901](../schema_generator/spec/ts_119602v010101p.txt#L901), [L912](../schema_generator/spec/ts_119602v010101p.txt#L912) vs [L970](../schema_generator/spec/ts_119602v010101p.txt#L970)).

> "In case the scheme information is implicit, the LoTE need not contain this component."
>
> "In case the LoTE does not contain this component, information about the list itself shall be provided within the list directly through the presence of the LoTEVersionIdentifier, the LoTESequenceNumber, the SchemeOperatorName, the ListIssueDateTime, and the NextUpdate elements."

versus the Semantics paragraph of the same clause:

> "In case the scheme information is implicit, this component shall contain at least the LoTEVersionIdentifier, the LoTESequenceNumber, the SchemeOperatorName, the ListIssueDateTime, and the NextUpdate elements."

**Reading.** The three sentences are consistent: an implicit list need not contain `ListAndSchemeInformation` (L901); without it, the five elements are provided "within the list directly" (L912); with it, the component contains at least those five (L970, which states the content of the component when present, not that it must be present). An earlier version of this entry read L970 as a contradiction; this project now follows the reading above (see [docs/model/README.md](../schema_generator/model/README.md), Tracks).

**Problem.** "Within the list directly" has no defined place:
- The data model in clause 5 lists the components of a LoTE and has no slot for these elements outside `ListAndSchemeInformation`.
- Annex A provides bindings only for scheme-explicit lists (defect 17), where the component is always present. No binding shows the implicit form without it.
- Implementations therefore have to invent a placement, and two independent implementations will not agree. This project places the five elements under the root, in the component's position (XML: children of `ListOfTrustedEntities`; JSON: keys of `"LoTE"`).

**Suggested correction.** State in clause 5 / 6.3.0 where the five elements go when the component is absent (e.g. as direct children of the LoTE, in the position of `ListAndSchemeInformation`), and show it in an implicit binding in Annex A. Alternatively, require the component in implicit lists too and delete L901 and L912.

### 5. PKI-based service identity: certificate only, or certificate or SKI?

**Location.** 6.6.0 ([L2076](../schema_generator/spec/ts_119602v010101p.txt#L2076)) vs 6.6.3.0 ([L2151](../schema_generator/spec/ts_119602v010101p.txt#L2151)).

> "When the listed service relies on PKI technology, the ServiceDigitalIdentity component shall contain at least one X509Certificate element."
>
> "When using PKI public-key technology, this component shall contain at least: one X509Certificate element or an X509SKI element."

**Problem.** The same situation has two different requirements. An identity containing only an X509SKI satisfies 6.6.3.0 but violates 6.6.0.

**Suggested correction.** Align both clauses. Given 6.7, which uses X509SKI for history instances, the 6.6.3.0 wording ("X509Certificate or X509SKI") seems intended. Otherwise, state explicitly that the stricter rule of 6.6.0 applies to current service information.

### 6. `PointerToOtherLoTE` vs `PointersToOtherLoTE`

**Location.** 6.3.0 ([L964](../schema_generator/spec/ts_119602v010101p.txt#L964)) and Table 1 ([L1004](../schema_generator/spec/ts_119602v010101p.txt#L1004)) vs 6.3.13 ([L1380](../schema_generator/spec/ts_119602v010101p.txt#L1380)).

> "The PointerToOtherLoTE component (see clause 6.3.13)."
>
> "The PointersToOtherLoTE component references any relevant list of trusted entities…"

**Problem.** Two names for the same component. Bindings have to pick one.

**Suggested correction.** Use `PointersToOtherLoTE`, the name in the defining clause, in 6.3.0 and Table 1.

### 7. `ServiceSupplyPoint` vs `ServiceSupplyPoints`

**Location.** 6.6.0 ([L2046](../schema_generator/spec/ts_119602v010101p.txt#L2046)) vs 6.6.7 ([L2298](../schema_generator/spec/ts_119602v010101p.txt#L2298)).

> "The ServiceSupplyPoint component (see clause 6.6.7)."
>
> "The ServiceSupplyPoints component specifies one or more URIs…"

**Problem.** Two names for the same component. Table I.3 also uses the singular ("The ServiceSupplyPoint component shall contain the URI…", [L4046](../schema_generator/spec/ts_119602v010101p.txt#L4046)).

**Suggested correction.** Use `ServiceSupplyPoints` throughout, including in Table I.3.

### 8. `ServiceDefinitionURI` vs `TEServiceDefinitionURI`

**Location.** 6.6.0 ([L2048](../schema_generator/spec/ts_119602v010101p.txt#L2048)) vs 6.6.8 ([L2317](../schema_generator/spec/ts_119602v010101p.txt#L2317), [L2322](../schema_generator/spec/ts_119602v010101p.txt#L2322)).

> "The ServiceDefinitionURI component (see clause 6.6.8)."
>
> "The TEServiceDefinitionURI component specifies the URI(s) where relying parties can obtain service-specific information provided by the TE."

**Problem.** Two names for the same component. This has already caused a real incompatibility: an XML list in circulation uses `TEServiceDefinitionURI`, while the ETSI Forge JSON binding uses `ServiceDefinitionURI`.

**Suggested correction.** Choose one name. `TEServiceDefinitionURI` distinguishes it clearly from `SchemeServiceDefinitionURI` (6.6.6). Use it in 6.6.0 and in the bindings.

### 9. Associated body component names

**Location.** 6.5.5.1.1 ([L1846](../schema_generator/spec/ts_119602v010101p.txt#L1846)) vs 6.5.5.1.5 ([L1968](../schema_generator/spec/ts_119602v010101p.txt#L1968)), and 6.5.5.1.4 ([L1909](../schema_generator/spec/ts_119602v010101p.txt#L1909)–[L1918](../schema_generator/spec/ts_119602v010101p.txt#L1918)).

> "The AssociatedBodyInformationURI element (see clause 6.5.5.1.5)."
>
> "The AssociatedBodyInformation component specifies the URI(s) where users (e.g. relying parties) can obtain information specific to that body."
>
> "The AssosciatedBodyAddress component specifies the address of the body identified through the AssocitedBodyName component (clause 6.5.1)…"

**Problem.**
- The information URI component has two names.
- Clause 6.5.5.1.4 misspells `AssociatedBodyAddress`, `AssociatedBodyPostalAddress`, `AssociatedBodyElectronicAddress` and `AssociatedBodyName`. The same misspellings recur in 6.5.5.1.4.1 and 6.5.5.1.4.2.
- It also refers to "(clause 6.5.1)" for the associated body name, which is defined in 6.5.5.1.2.

**Suggested correction.** Use `AssociatedBodyInformationURI` in 6.5.5.1.5, correct the spellings in 6.5.5.1.4.x, and refer to clause 6.5.5.1.2.

### 10. Subject key identifier clause is a copy of the public key clause

**Location.** 6.6.3.4 ([L2210](../schema_generator/spec/ts_119602v010101p.txt#L2210)–[L2222](../schema_generator/spec/ts_119602v010101p.txt#L2222)).

> "6.6.3.4 Subject key identifier … Format: The format of the PublicKeyValue component is left open and is syntax-specific. Semantics: The value of the PublicKeyValue component shall be the same public key as the one present within any X509Certificate element listed in the parent ServiceDigitalIdentity component, if any."

**Problem.**
- The Format and Semantics paragraphs repeat 6.6.3.3 (PublicKeyValue) word for word.
- The X509SKI component's format and meaning are therefore never defined, although 6.6.3.0, 6.7 and Table H.3 rely on it.
- The clause also names the component `SubjectKeyIdentifier`, while 6.6.3.0 lists it as `X509SKI`.

**Suggested correction.** Define the X509SKI component, e.g. "The X509SKI component shall be a Base64 string. Its value shall be the value of the subjectKeyIdentifier extension of the X.509 certificate(s) that were or are applicable for the service." Use one component name.

### 11. Garbled sentence in the scheme information URI clause

**Location.** 6.3.7 ([L1235](../schema_generator/spec/ts_119602v010101p.txt#L1235)).

> "This component may contain be zero or more URIs leading to archived versions of the list."

**Suggested correction.** "This component may contain zero or more URIs leading to archived versions of the list."

### 12. "Expired" status required but never defined

**Location.** 6.3.15 ([L1462](../schema_generator/spec/ts_119602v010101p.txt#L1462)–[L1463](../schema_generator/spec/ts_119602v010101p.txt#L1463)).

> "If a scheme ceases operations or halts publication of its LoTE, a final version shall be published with all services' status shown as "expired" (see Service current status) and this field set null."

**Problem.**
- Clause 6.6.4 defines no status values; it leaves them to profiles.
- None of the profiles defines an "expired" status. Five of them (D, E, F, G, I) forbid `ServiceStatus` altogether.
- So a closed list can't meet this requirement in those profiles, and in the others there is no registered URI to use.

**Suggested correction.** Register a generic "expired" status URI in Annex C and state how profiles without `ServiceStatus` close a list. For example: allow `ServiceStatus` in the final list only, or remove all entities.

## Annexes D–I (profiles)

### 13. Typo in the WRPRC status determination approach URI

**Location.** Table G.1 ([L3480](../schema_generator/spec/ts_119602v010101p.txt#L3480)) and Annex C.2.2 ([L2763](../schema_generator/spec/ts_119602v010101p.txt#L2763)).

> "The value of the StatusDeterminationApproach component shall be "http://uri.etsi.org/19602/WRPRCrovidersList/StatusDetn/EU"."

**Problem.** "WRPRCrovidersList" is missing the "P" of "Providers". Every other URI follows the `…ProvidersList` pattern, including the WRPRC scheme rules URI in the same table ([L3482](../schema_generator/spec/ts_119602v010101p.txt#L3482)): `http://uri.etsi.org/19602/WRPRCProvidersList/schemerules/EU`. Because the typo appears in both places, implementers will split between the two spellings, and exact string matching will fail.

**Suggested correction.** `http://uri.etsi.org/19602/WRPRCProvidersList/StatusDetn/EU` in both Table G.1 and Annex C.2.2.

### 14. Country URI placed under TE address in Annex H only

**Location.** Table H.2, TE address row ([L3749](../schema_generator/spec/ts_119602v010101p.txt#L3749)–[L3757](../schema_generator/spec/ts_119602v010101p.txt#L3757)).

> "The TEAddress component shall contain: a) the postal address of the Pub-EAA provider; and b) the contact email and contact phone number … c) the URI "http://uri.etsi.org/19602/ListOfTrustedEntities/PubEAAProvider/CC" …"

**Problem.**
- In Annexes D, E, F, G and I the equivalent URI is item c) of the **TE information URI** row, e.g. D.2 [L2942](../schema_generator/spec/ts_119602v010101p.txt#L2942).
- In H it sits under TE address, where the electronic address is meant for e-mail, web-site and phone contacts (clause 6.3.5.2).
- Real Pub-EAA lists already put it under TE information URI, following the other annexes.

**Suggested correction.** Move item c) to the TE information URI row of Table H.2, as in the other annexes.

### 15. Missing closing quotation mark in a WRPAC service type

**Location.** Table F.3 ([L3372](../schema_generator/spec/ts_119602v010101p.txt#L3372)).

> "a) "http://uri.etsi.org/19602/SvcType/WRPAC/Issuance to indicate that the service is service under which wallet relying parties access certificates are issued;"

**Suggested correction.** `"http://uri.etsi.org/19602/SvcType/WRPAC/Issuance" to indicate…`

### 16. Service type descriptions copied from the WRPAC profile

**Location.** Table G.3 ([L3573](../schema_generator/spec/ts_119602v010101p.txt#L3573), [L3576](../schema_generator/spec/ts_119602v010101p.txt#L3576)–[L3577](../schema_generator/spec/ts_119602v010101p.txt#L3577)) and Table H.3 ([L3788](../schema_generator/spec/ts_119602v010101p.txt#L3788)–[L3790](../schema_generator/spec/ts_119602v010101p.txt#L3790)).

> G.3: "…"http://uri.etsi.org/19602/SvcType/WRPRC/Issuance" to indicate that the service is service under which wallet relying parties access certificates are issued; b) "http://uri.etsi.org/19602/SvcType/WRPRC/Revocation" to indicate that the service is a service providing validity status information on wallet relying party access certificates."
>
> H.3: "b) "http://uri.etsi.org/19602/SvcType/PubEAA/Revocation" to indicate that the service is a service providing validity status information on wallet relying party access certificates."

**Problem.** The URIs are correct, but the descriptions say "access certificates". In Annex G they should say *registration* certificates. In Annex H they should say *electronic attestations of attributes*.

**Suggested correction.**
- G.3: "…under which wallet relying party registration certificates are issued" and "…validity status information on wallet relying party registration certificates".
- H.3: "…validity status information on electronic attestations of attributes".

## Terms and bindings

### 17. "Scheme explicit" is required but never defined, and implicit lists have no binding

**Location.** Clause 3.1 ([L451](../schema_generator/spec/ts_119602v010101p.txt#L451)), clause 4.6 ([L556](../schema_generator/spec/ts_119602v010101p.txt#L556)–[L557](../schema_generator/spec/ts_119602v010101p.txt#L557)), clause 6.3.0 ([L895](../schema_generator/spec/ts_119602v010101p.txt#L895)–[L903](../schema_generator/spec/ts_119602v010101p.txt#L903), Table 1 [L988](../schema_generator/spec/ts_119602v010101p.txt#L988)), Annex A ([L2444](../schema_generator/spec/ts_119602v010101p.txt#L2444), [L2455](../schema_generator/spec/ts_119602v010101p.txt#L2455)–[L2456](../schema_generator/spec/ts_119602v010101p.txt#L2456)) and D.1 ([L2838](../schema_generator/spec/ts_119602v010101p.txt#L2838)), with the same sentence in E.1–I.1.

> 6.3.0: "Information about the scheme within which the LoTE is issued may be provided either implicitly or explicitly."
>
> 4.6: "EXAMPLE: Different bindings can be defined, for instance, for an implicit scheme information compared to an explicit scheme information."
>
> A.1: "A JSON binding for a scheme-explicit LoTE is provided in the following repository"
>
> D.1: "The PID providers list shall comply with the scheme explicit JSON schema definition specified in Annex A of the present document."

**Problem.**
- **The term is never defined.** Clause 3.1 lists no definition of implicit or explicit scheme information, or of a "scheme-explicit LoTE". The meaning has to be inferred from 6.3.0 and Table 1, and 6.3.0 itself contradicts itself on whether an implicit list may omit `ListAndSchemeInformation` (defect 4). Yet "scheme explicit" is a normative requirement in every profile annex (D.1–I.1).
- **A list does not say which kind it is.** There is no element that declares the mode. A validator can only infer it from content: a list is explicit as soon as it contains one of the elements Table 1 forbids for implicit lists (`SchemeName`, `SchemeInformationURI`, `StatusDeterminationApproach`, `SchemeTypeCommunityRules`, `PolicyOrLegalNotice`). The text never states this rule.
- **Implicit lists have no binding.** Clause 4.6 anticipates separate bindings for implicit and explicit scheme information, and clause 6.3 allows both, but Annex A only provides bindings "for a scheme-explicit LoTE". An implicit LoTE cannot be validated against any ETSI schema.
- **The bindings do not enforce the term they are named after.** The Forge XML schema always requires three explicit-only elements but never requires `SchemeTypeCommunityRules`, `SchemeTerritory` or `PolicyOrLegalNotice`. The Forge JSON schema requires only the five elements common to both modes. Neither implements Table 1.

**Suggested correction.**
- Add to clause 3.1:
  - *explicit scheme information*: scheme information provided within the LoTE, through all elements marked "M" in the explicit column of Table 1;
  - *implicit scheme information*: scheme information known to all parties by means outside the LoTE, which then contains only the elements marked "M" in the implicit column of Table 1;
  - *scheme-explicit LoTE*: a LoTE with explicit scheme information.
- State in 6.3.0 that the presence of any element marked "/" for implicit scheme information makes the scheme information explicit.
- Either provide bindings for implicit scheme information, or state in Annex A and clause 4.6 that only scheme-explicit bindings are defined.
- Make the Annex A schemas enforce Table 1 for explicit lists.

### 18. The profiles require the Annex A JSON schema, which contradicts the text

**Location.** Clause 6.6.3.1 ([L2166](../schema_generator/spec/ts_119602v010101p.txt#L2166)), Annex A.1 ([L2444](../schema_generator/spec/ts_119602v010101p.txt#L2444)–[L2449](../schema_generator/spec/ts_119602v010101p.txt#L2449)) and D.1 ([L2838](../schema_generator/spec/ts_119602v010101p.txt#L2838)), with the same sentence in E.1 ([L3041](../schema_generator/spec/ts_119602v010101p.txt#L3041)), F.1 ([L3246](../schema_generator/spec/ts_119602v010101p.txt#L3246)), G.1 ([L3445](../schema_generator/spec/ts_119602v010101p.txt#L3445)), H.1 ([L3646](../schema_generator/spec/ts_119602v010101p.txt#L3646)) and I.1 ([L3902](../schema_generator/spec/ts_119602v010101p.txt#L3902)).

> 6.6.3.1: "The X509Certificate component shall be a Base64 string."
>
> D.1: "The PID providers list shall comply with the scheme explicit JSON schema definition specified in Annex A of the present document."
>
> A.1: "In the event that any part of the module and/or schemas within this electronic attachment are in conflict with the text of the present document, the present document shall prevail as the authoritative source."

**Problem.**
- The Annex A JSON schema (`1960201_json_schema.json` on ETSI Forge) does not accept a certificate as a Base64 string. It requires an object `{"val": "<base64>", "encoding"?, "specRef"?}` (definition `pkiOb`, copied from the JAdES schema). The Annex A XML schema uses a plain `base64Binary`, as the text does.
- So a JSON profile list cannot satisfy both requirements. With `"X509Certificates": ["MII…"]` it follows 6.6.3.1 but fails the schema that D.1–I.1 make mandatory; with `[{"val": "MII…"}]` it passes the schema but breaks 6.6.3.1. Lists that are valid against the text-based profile schemas of this project are all rejected by the Annex A JSON schema, for this reason only.
- The prevalence rule of A.1 resolves the conflict in favour of the text, but implementers who validate against the published schema will see correct lists rejected and are likely to "fix" them into the wrong form.
- The same mechanism applies to other places where the Annex A JSON schema contradicts the text (see [forge/errors.md](../schema_generator/reference/forge/errors.md)): a closed list with `NextUpdate` null (6.3.15), a multilingual `LoTELegalNotice` (6.3.11) and regional `SchemeTerritory` codes such as `ASIA` (6.1.5 b) are also rejected.

**Suggested correction.**
- Change the Annex A JSON schema so that `X509Certificates` items are Base64 strings, as in the text and the XML binding.
- Until then, state in D.1–I.1 that lists shall comply with the Annex A schema "except where it conflicts with the text", or point implementers explicitly to the A.1 prevalence rule.

### 19. Explicit scheme information: the text lists six additional elements, Table 1 eight

**Location.** 6.3.0, Semantics ([L981](../schema_generator/spec/ts_119602v010101p.txt#L981)–[L983](../schema_generator/spec/ts_119602v010101p.txt#L983)) vs Table 1 ([L988](../schema_generator/spec/ts_119602v010101p.txt#L988)–[L1010](../schema_generator/spec/ts_119602v010101p.txt#L1010), rows [L996](../schema_generator/spec/ts_119602v010101p.txt#L996) and [L997](../schema_generator/spec/ts_119602v010101p.txt#L997)). Related to defects 4 and 17.

> Semantics: "In case the scheme information is explicit this component shall contain, in addition, LoTEType, the SchemeInformationURI, the StatusDeterminationApproach, the SchemeTypeCommunityRules, the SchemeTerritory, and the PolicyOrLegalNotice elements."

versus Table 1, which the next sentence says "summarizes the above requirements":

> | Element | Implicit scheme information | Explicit scheme information |
> |---|---|---|
> | SchemeOperatorAddress | O | M |
> | SchemeName | / | M |

**Problem.**
- The Semantics paragraph makes **six** elements mandatory for explicit scheme information, in addition to the five that both kinds require. Table 1 marks **eight** as M in the explicit column: the same six plus `SchemeOperatorAddress` and `SchemeName`.
- Table 1 is introduced as a summary of the text ("Table 1 summarizes the above requirements…", [L985](../schema_generator/spec/ts_119602v010101p.txt#L985)), yet it adds two requirements the text does not state. Nothing else in the text requires them either: the Format paragraph lists both among the optional sub-components ([L948](../schema_generator/spec/ts_119602v010101p.txt#L948), [L950](../schema_generator/spec/ts_119602v010101p.txt#L950)), and clauses 6.3.5 and 6.3.6 describe their content but not when they must be present.
- So an explicit list without `SchemeOperatorAddress` or `SchemeName` is valid by the text and invalid by Table 1. The two readings give different validators: one requires 6 additional elements, the other 8.
- `SchemeName` makes the gap sharper. Table 1 forbids it in implicit lists ("/"), so its mere presence makes a list explicit (see defect 17), but by the text an explicit list does not have to contain it.

**What this project does.** The model and the generated schemas follow Table 1: rule `R-Table1` requires all eight elements once any explicit-only element is present, and every profile (D–I) requires all eight under "scheme explicit". The text alone would require six.

**Suggested correction.** Align the Semantics paragraph with Table 1: "In case the scheme information is explicit this component shall contain, in addition, LoTEType, the SchemeOperatorAddress, the SchemeName, the SchemeInformationURI, the StatusDeterminationApproach, the SchemeTypeCommunityRules, the SchemeTerritory, and the PolicyOrLegalNotice elements." If six elements were intended instead, change the explicit column of Table 1 for `SchemeOperatorAddress` and `SchemeName` to "O".

### 20. The mandatory LoTE tag has no value, and the JSON binding no place for it

**Location.** Clause 5 ([L580](../schema_generator/spec/ts_119602v010101p.txt#L580), [L585](../schema_generator/spec/ts_119602v010101p.txt#L585)), clause 6.2 ([L874](../schema_generator/spec/ts_119602v010101p.txt#L874)–[L882](../schema_generator/spec/ts_119602v010101p.txt#L882)), Annex C, Annex A.1 ([L2444](../schema_generator/spec/ts_119602v010101p.txt#L2444)–[L2449](../schema_generator/spec/ts_119602v010101p.txt#L2449)) and D.1–I.1.

> Clause 5: "There shall be only one occurrence of the first two and last components (i.e. 1., 2. and 6.)." — component 1: "A list of trusted entities tag (Tag): This tag facilitates the identification of the list of trusted entities during electronic searches. The contents of the tag are specified in clause 6.2."
>
> 6.2: "The LoTETag component shall be a character string which indicates that the data structure is a LoTE. This shall be the character representation of the LoTE Tag URI."

**Problem.**
- **No value.** The tag is mandatory and shall be "the LoTE Tag URI", but no such URI is registered: not in Annex C, not anywhere in the text. Implementations cannot know which value to write, and validators cannot check it. The predecessor TS 119 612 registers one (`http://uri.etsi.org/19612/TSLTag`).
- **No place in JSON.** The Annex A JSON schema (`1960201_json_schema.json` on ETSI Forge) has no tag property, and `additionalProperties: false` on the root and on `LoTE` forbids adding one. So a JSON list cannot carry the mandatory tag and still pass the schema that D.1–I.1 make mandatory. The Annex A XML schema does carry it, as the attribute `LOTETag` (spelled differently from the text's `LoTETag`).
- Real lists show the result: an XML PID providers list carries `LOTETag=""` (empty), and the WP4 List of Trusted Lists in JSON carries no tag.

**What this project does.** The tag is required in both bindings, with any URI as its value: the text prevails over the Annex A schemas (A.1).

**Suggested correction.**
- Register the LoTE Tag URI in Annex C, e.g. `http://uri.etsi.org/19602/LoTETag`, and state it in 6.2.
- Add a `LoTETag` property to the Annex A JSON schema, and use the text's spelling `LoTETag` in the XML schema.

