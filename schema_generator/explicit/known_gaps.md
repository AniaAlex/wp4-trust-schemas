# Known gaps: explicit track

Open issues in the explicit track (model, profiles, generators, validator) found while working on it, not fixed yet. Each entry says where it is, what can go wrong, and the proposed fix. Remove an entry when it is fixed; record lasting decisions in [docs/project_decisions_vs_etsi.md](../../docs/project_decisions_vs_etsi.md).

| # | Gap | Area | Risk |
|---|---|---|---|
| 1 | Occurrence values are not validated: a wrong type is silently ignored | generators | high: a rule disappears without an error |
| 2 | `Signature` still has `"json": {"max": "0"}` (a string) in the explicit model | model | low, but blocks gap 1 |
| 3 | Profiles support only `max: 0`, not `max: N` | profile generator | low today: no annex needs it |
| 4 | Unrecognized critical extensions are not rejected | validator | medium: clause 6.3.17 not enforced |
| 5 | `lote-schemas check` reads its requirements from the frozen base model | checker | medium: drifts as the explicit model changes |
| 6 | `ServiceDigitalIdentity` does not record that "at least one identifier" is an interpretation | model | low: traceability |
| 7 | `PolicyOrLegalNotice` cites a branch, not the "either … or" sentence | model | low: traceability |
| 8 | Two checkable constraints are not generated | generators | low |
| 9 | No signature validation | validator | known scope limit |
| 10 | Hand-written documents can drift from the model | docs | low |

## 1. Occurrence values are not validated

The generators compare `min` / `max` with exact values (`== 0`). Python never treats a number and a string as equal (`0 == "0"` is `False`) and raises no error, so a value of the wrong type makes the comparison false and the rule is skipped without notice. This happened once: `"max": 0` in [profiles/D_pid_providers.json](model/profiles/D_pid_providers.json) while the generator still looked for `"0"` would have dropped `D-HistoricalInformationPeriod-prohibited`.

**Fix.** Raise a `ValueError` when a model or overlay is read:

| Where | `min` | `max` |
|---|---|---|
| profile overlays | a number ≥ 0 | the number `0` only (gap 3) |
| model components | a number ≥ 0 | `0`, `1` or `"n"` (unbounded; FHIR writes `"*"`, which is why FHIR's `max` is a string) |
| model `json` / `xml` overrides | a number | a number |

Exclude `bool` explicitly (`True` counts as `1` in Python). The base and implicit models are frozen and still contain `"json": {"max": "0"}`: the override check applies to the explicit model only, or accepts `"0"` for the frozen files.

## 2. `Signature` `json.max` is a string

[model/lote_model_explicit.json](model/lote_model_explicit.json), `LoTE.Signature`: `"json": {"max": "0"}` (not part of the JSON binding, clause 6.8.0). The profile overlays now use the number `0`; this is the last string zero in the explicit track.

**Fix.** Change it to `0` and make the three readers accept both values, since the same code also reads the frozen base and implicit models, which keep `"0"`: [gen_json.py:194](../src/lote_schema_generator/gen_json.py#L194), [validate.py:479](../../schema_validator/src/lote_schema_validator/validate.py#L479), [check.py:233](../src/lote_schema_generator/check.py#L233) (`in (0, "0")`). Leave [check.py:269](../src/lote_schema_generator/check.py#L269) as it is: it reads only the frozen differentials. Check that the generated schemas do not change.

## 3. Profiles support only `max: 0`

[gen_profiles_from_model.py](../src/lote_schema_generator/gen_profiles_from_model.py) turns `max: 0` into a "prohibited" rule; any other `max` (an annex saying "at most one") is ignored. No annex needs it today.

**Fix.** Until needed: stop with an error (gap 1). When needed: JSON `maxItems: N`, Schematron `count(child) <= N`, and a check that `N` does not exceed the explicit model's own `max` (a profile may only narrow, clause 4.7).

## 4. Unrecognized critical extensions are not rejected

Clause 6.3.17 (p. 24, lines 1502–1503): "A system using LoTEs shall reject the LoTE if it encounters a critical extension it does not recognize, while a non-critical extension may be ignored if it is not recognized." The schemas check the shape of the extension lists and the content of the two defined extensions (`OtherAssociatedBodies`, `ServiceUniqueIdentifier`), and accept any other extension. Nothing rejects an unknown extension with `Critical: true`.

**Fix.** A rule in the validator with a configurable set of recognized extensions (the two above, plus any WP4 defines): an unknown critical extension is an error, an unknown non-critical one a warning. Record it in the model as a constraint on `LoTE` (e.g. `R-CriticalExtension`).

## 5. The checker reads the frozen base model

[check.py](../src/lote_schema_generator/check.py) takes its requirements from `base/model/lote_model.json` by default and, with `--scheme explicit`, the Table 1 changes from the frozen `base/model/schemes/explicit.json`. Since the explicit model is edited directly, a change there is checked against outdated requirements, and `test_check.py` may report it as a mismatch.

**Fix.** For `--scheme explicit`, read the requirements from the explicit model; its `scheme` entries already hold the Table 1 changes.

## 6. `ServiceDigitalIdentity`: interpretation not recorded

Clause 6.6.3.0 says the component "specifies one or multiple digital identifiers" (Description, p. 33, line 2119) but "may contain" each kind of identifier (Format, line 2130), which read alone allows an empty component. The model takes the Description: `"content": "any-of"` ([line 2836](model/lote_model_explicit.json#L2836)), at least one identifier. Its `note` and citation do not say that this is a choice between two readings. ETSI's Forge bindings read "may" literally and accept an empty identity; [forge/errors.md](../reference/forge/errors.md) records this for the XSD only, not for the JSON schema (no `minProperties`).

**Fix.** Extend the `note`, cite line 2130 next to line 2119, add the Forge JSON row to errors.md, and record the decision (draft: decision #5 in project_decisions_vs_etsi.md).

## 7. `PolicyOrLegalNotice` cites a branch

The structure's citation quotes "a sequence of LoTEPolicy elements which shall be multilingual pointers" (line 1344). The sentence that makes it a `choice` is "The PolicyOrLegalNotice component shall contain either:" (p. 22, line 1342).

**Fix.** Cite line 1342 on the structure; the branch quotes stay on the components.

## 8. Two checkable constraints are not generated

`R-NextUpdateAfterIssue` (6.3.15: `NextUpdate` after `ListIssueDateTime`) and `R-HistoryOrder` (6.4.4: service history in order) are checkable from the list alone but have no `check`, so the generated schemas only list them. Comparing two dates is not possible in JSON Schema; Schematron can.

**Fix.** Add a `check` type for date comparison (as the profiles' `months-after`) and generate it into Schematron and the validator's rule layer.

## 9. No signature validation

The validator checks only where a signature may or must sit (no `Signature` component in a JSON list; `ds:Signature` optional in XML, required in Annex H XML lists). It does not check the envelope, the JAdES / XAdES header, the signing certificate or the cryptographic signature, nor `R-SignerMatchesOperator` (6.8.0). See [base/generated/README.md](../base/generated/README.md), Model validator limitations.

## 10. Hand-written documents can drift

[explicit_schema.md](explicit_schema.md) and [terminology.md](terminology.md) are written by hand from the explicit model; a change in the model is not reflected automatically. The profile documentation (fields, semantics, "When editing") is in the frozen [base/model/README.md](../base/model/README.md), although the profiles are active.

**Fix.** Generate the tree in explicit_schema.md from the model during the build, or check it in a test; move the profile documentation to explicit/.
