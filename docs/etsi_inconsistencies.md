# Inconsistencies in ETSI TS 119 602 V1.1.1 (2025-11)

Places where two parts of ETSI TS 119 602 V1.1.1 do not fit together, so that a requirement can be read in more than one way and an implementation has to choose. Plain errors (wrong cross-references, typos, missing content) are in [etsi_defects.md](etsi_defects.md); the choices this project made are in [project_decisions_vs_etsi.md](project_decisions_vs_etsi.md).

- **Source text:** [ts_119602v010101p.pdf](spec/ts_119602v010101p.pdf). Pages are those of the PDF; quotes are verbatim.

| # | Topic | Clauses | Impact on implementations | Project decision |
|---|---|---|---|---|
| 1 | One "value" of a multilingual `TEName` | 6.5.1, 6.1.4 vs 6.6.3.0, Table H.3 | **Medium:** whether a certificate's organizationName may match any language version of the TE name | [#6](project_decisions_vs_etsi.md#6-a-certificates-organizationname-matches-at-least-one-tename-value) |

---

### 1. One "value" of a multilingual `TEName`

**The text says `TEName` has several values.** Clause 6.5.1 (p. 27):

> "The TEName component shall be a sequence of multilingual character strings (see clause 6.1.4)."

and clause 6.1.4 (p. 14):

> "Each multilingual character string shall consist of two parts: a tag, conformant to IETF RFC 5646 [11] and in lower case, that identifies the language in which the string is expressed, and the text in that language. The same content may be represented in multiple languages by a sequence of multilingual character strings."

Every list has at least an English value ("Lists of trusted entities shall be issued supporting at least the UK English language", 6.1.4, p. 14), and may have more; a name not in the Latin alphabet is given twice, in the native script and transliterated (p. 15).

**The certificate rules compare against one value.** Clause 6.6.3.0 (p. 34), a recommendation for every list:

> "The value of that organizationName attribute should strictly match the 'TE Name' value (clause 6.4.1)."

and Table H.3, Service digital identity (p. 65), a requirement for Annex H lists:

> "The organizationName attribute present in the subject name shall strictly match the value of the TEName component."

A certificate subject usually has one organizationName, in one language. Which of the `TEName` values it must match is not said:

1. any one of them;
2. the English one, the only language every list must have;
3. the one in the provider's own language.

**Example.** A Belgian provider lists `TEName` as `en: Provider BE` and `fr: Fournisseur BE`; its certificate has `O=Fournisseur BE`. Reading 1 accepts the list, reading 2 rejects it, reading 3 depends on what the provider's own language is, which the list does not state.

**Suggested clarification.** "… shall strictly match one of the values of the TEName component", with "strictly" defined (identical character strings, no case or whitespace normalisation).

**Also in this sentence:** 6.6.3.0 refers to "clause 6.4.1" for TE name, which is clause 6.5.1 ([etsi_defects.md #3](etsi_defects.md#3-te-name-referred-to-as-clause-641-instead-of-651)).
