# Known gaps: schema_validator

What `lote-validate` does not process, and why. Gaps in the explicit model, the profiles and the generators are listed in [../schema_generator/explicit/known_gaps.md](../schema_generator/explicit/known_gaps.md).

| # | Gap | Risk |
|---|---|---|
| 1 | Implicit lists are not supported | none for WP4; an implicit list from elsewhere is reported as invalid |
| 2 | The base model (both kinds of list) is not used | none for WP4 |
| 3 | Unrecognized critical extensions are not rejected | medium: clause 6.3.17 not enforced |
| 4 | Signatures are not validated | known scope limit |

## 1. Implicit lists are not supported

TS 119 602 allows lists with implicit scheme information (clause 6.3.0, Table 1, implicit column): the scheme is known out of band, the list may leave out `ListAndSchemeInformation` and place the five list elements directly under `LoTE`, and `SchemeName`, `SchemeInformationURI`, `StatusDeterminationApproach`, `SchemeTypeCommunityRules` and `PolicyOrLegalNotice` are not allowed.

The validator validates **every list as explicit**: there is no `--implicit` option and the track is not inferred from the content. An implicit list therefore fails with the explicit track's Table 1 rules, e.g. `EXP-ListAndSchemeInformation-required`, `EXP-NextUpdate-prohibited` (list elements placed directly in the list) or `EXP-SchemeName-required`, each with its citation.

**Why.** WP4 lists are explicit (every annex D–I requires it, D.1–I.1), and the implicit track is frozen and not published ([project_decisions_vs_etsi.md](../docs/project_decisions_vs_etsi.md) #3, #4). Inferring the track let an incomplete WP4 list pass as implicit.

**To support it again.** The generator still builds and tests the implicit track (`schema_generator/implicit/`). Publish it next to `explicit/`, add it back to `TRACKS` in [validate.py](src/lote_schema_validator/validate.py), and add an explicit `--implicit` option (not inference).

## 2. The base model is not used

The generator's base model (`schema_generator/base/`) describes both kinds of list at once, with Table 1 as rules (`R-Table1`, `R-SchemeInfoPlacement`) instead of structure. The validator neither ships nor reads it: it validates against the explicit track only. The base model is frozen.

## 3. Unrecognized critical extensions are not rejected

Clause 6.3.17 (p. 24, lines 1502–1503): "A system using LoTEs shall reject the LoTE if it encounters a critical extension it does not recognize, while a non-critical extension may be ignored if it is not recognized." The schemas check the shape of the extension lists and the content of the two extensions the text defines (`OtherAssociatedBodies`, `ServiceUniqueIdentifier`), and accept any other extension. Nothing rejects an unknown extension with `Critical: true`.

**Fix.** A rule in the validator with a configurable set of recognized extensions: an unknown critical extension is an error, an unknown non-critical one a warning (see the generator's known gaps, #4).

## 4. Signatures are not validated

Only where a signature may or must sit is checked: no `Signature` component in a JSON list (6.8.0), `ds:Signature` optional in XML, required in an Annex H list in XML (H.4). The envelope (compact JWS around a JSON list, `ds:Signature` in or around an XML list), the JAdES / XAdES header, the signing certificate, the cryptographic signature and `R-SignerMatchesOperator` (6.8.0) are not checked.
