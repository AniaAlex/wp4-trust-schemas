# Project decisions vs ETSI TS 119 602

Where this project's schemas and tools deliberately differ from what ETSI TS 119 602 V1.1.1 (2025-11) or its Annex A bindings (ETSI Forge) prescribe, and why. Quotes are verbatim from [ts_119602v010101p.txt](spec/ts_119602v010101p.txt); page and line refer to that file.

## 1. XML profiles for annexes that allow only JSON

The project generates a JSON profile **and** an XML (Schematron) profile for each of the six EU annexes, in [explicit/generated/profiles/](../schema_generator/explicit/generated/profiles/). The annexes allow XML only for H:

| Annex | x.1 General requirements | Generated profiles |
|---|---|---|
| D, E, F, G, I | "shall comply with the scheme explicit **JSON** schema definition specified in Annex A" (e.g. D.1, p. 46, line 2838) | JSON **and** XML (e.g. `lote_profile_D_pid_providers.sch`) |
| H | "shall comply with **either** the scheme explicit XML schema definition … **or** the scheme explicit JSON schema definition" (p. 62, line 3646) | JSON and XML |

**Why the XML profiles exist anyway.** The generator treats every annex the same way, and the XML profiles check the *content* rules of the annex correctly: fixed URIs, required and prohibited elements, the Member State URIs, the 6-month `NextUpdate` limit, and the structure of an enveloped signature (H.4 2)–3), a WP4 rule for D–G and I, #2). Real lists of annexes D–G and I are published in XML (e.g. a WP4 PID providers list), and the XML profiles show their content errors.

**Consequence.** An XML list of annex D, E, F, G or I is not conforming by format, whatever its content: its annex requires JSON, signed with compact JAdES (x.4). The XML profiles of those annexes are content checks only.

**In the model.** Each profile's signature element (`LoTE.Signature`) records this as its XML binding with `"from": "wp4"` and the reason: a WP4 decision, not the text. The element's JSON binding comes from the text (x.4).

**Status: open.** [tools/lote_validate.py](../schema_validator/src/lote_schema_validator/validate.py) does not yet report the format, so an XML list with correct content is reported as "valid" against `--profile D`. Planned: a format finding per annex (e.g. `D-format`, citing D.1), recorded as a constraint in the profile overlays.

## 2. Signature placement in XML lists

Every list "shall be signed by means of an AdES digital signature at conformance level baseline B" (6.8.0, p. 38, line 2415), and "The AdES digital signature may either be present within the LoTE itself, … or the signature itself encapsulates the LoTE" (p. 38, line 2417). An XML list may therefore be **enveloped** (`ds:Signature` inside `ListOfTrustedEntities`, as its last element: the `Signature` component) or **enveloping** (the list inside a `ds:Signature`, in its `ds:Object`; the list itself then contains no signature element). A detached signature is not one of the two options.

| Case | Must the XML list contain `ds:Signature`? |
|---|---|
| **H** (Pub-EAA) in XML | **Yes.** "When an XML binding is used to issue the Pub-EAA providers list, the Signature component shall be present with a XAdES Baseline B signature" (H.4, p. 66, line 3858); "It shall be an enveloped digital signature." (line 3861), with the transforms enveloped-signature, then exclusive C14N |
| **D, E, F, G, I** in XML | The question does not arise: these lists must be JSON, signed with compact JAdES ("The PID providers list shall be signed by means of a compact JAdES Baseline B signature", D.4, p. 49, line 3016; the same in E.4–G.4 and I.4). An XML list of these annexes is non-conforming by format (entry 1), with or without a signature |
| Core, no profile | Either form: inside the list (enveloped) or around it (enveloping) |

**Status: the `Signature` component is optional (`0..1`) in the core and in both tracks; the H XML profile requires it** (rule `H-Signature-xml-required`, cited to H.4, p. 66, line 3858). In the profiles D, E, F, G and I it stays optional in XML, as in the core (a WP4 decision, entry 1). So:
- an H list in XML without `ds:Signature` fails its profile; the other annexes accept XML lists with or without it, for their content only;
- the H.4 details (enveloped signature, the two transforms, exclusive canonicalization) are not checked by the schemas; they belong to a signature validator;
- an enveloping XML list is validated only if the list is first taken out of the signature's `ds:Object`, which [tools/lote_validate.py](../schema_validator/src/lote_schema_validator/validate.py) does not do yet;
- whether a list is signed at all is not checked: an enveloping signature lies outside the list, so this needs the signature validator, not the schema.

**The structure of an enveloped XML signature: H.4 2)–3) in every profile.** H.4 is the only place where TS 119 602 says how an XML signature of a LoTE is built: "Its ds:SignedInfo element shall contain a ds:Reference element with the URI attribute set to an empty string (i.e. URI=""), so as to refer to the entire document" (2), p. 66, line 3863), with one `ds:Transforms` holding the enveloped-signature transform, then exclusive canonicalization (2) a)–b), line 3867), and `ds:CanonicalizationMethod` exclusive canonicalization (3), line 3875). Each profile checks these three points on a `ds:Signature` inside the list (Schematron; the XPath is in the overlay element's `xml.constraint`):

| Rule | Checks | H | D, E, F, G, I |
|---|---|---|---|
| `X-sig-ref-uri` | a `ds:Reference` with `URI=""` | the text (H.4 2)) | **WP4 rule** |
| `X-sig-transforms` | that reference: one `ds:Transforms`, enveloped-signature then exclusive C14N | the text (H.4 2) a)–b)) | **WP4 rule** |
| `X-sig-c14n` | `ds:CanonicalizationMethod` is exclusive C14N | the text (H.4 3)) | **WP4 rule** |

- **Why WP4 applies them to D–G and I.** These annexes allow only JSON and define no XML signature; XML lists of them are still validated for their content (#1). For such a list, H.4 is the closest the text comes to an XML signature profile, and its `URI=""` closes a known weakness: a reference by `Id` (`URI="#…"`) signs one element, which an attacker can move aside and replace with a forged one that a careless consumer reads instead (XML signature wrapping). `URI=""` signs the whole document, so nothing can be moved or added.
- **How a WP4 rule is marked.** The overlay constraint has `"from": "wp4"` and a `reason`; the Schematron message starts with "WP4 rule (project_decisions_vs_etsi.md #2)"; the validator's JSON finding has `"from": "wp4"` in its `source`. The citation is the H.4 sentence the rule comes from.
- **Only when signed inside the list.** The rules fire on `ds:Signature` inside the list; a list without one gets no finding from them (the signature stays optional for D–G and I, and `H-Signature-xml-required` reports its absence in H). An enveloping signature is not seen (see above).
- **Not checked:** the rest of XAdES Baseline B, the signing certificate, and whether the signature is valid; this is for the signature validator. No profile (`--no-profile`): the core text allows any reference, so none of these rules applies.

## 3. WP4 lists are explicit; the implicit track is not used in WP4

TS 119 602 allows two kinds of list: scheme information "may be provided either implicitly or explicitly" (6.3.0, p. 15, line 895). This project builds both as tracks ([explicit/](../schema_generator/explicit/), [implicit/](../schema_generator/implicit/); see [base/model/README.md](../schema_generator/base/model/README.md), Tracks).

WP4 mocks the EU community rules, so its lists behave like the real EU lists, and those are explicit without exception: every annex requires it ("The PID providers list shall comply with the scheme explicit JSON schema definition specified in Annex A", D.1, p. 46, line 2838; the same in E.1–I.1).

| WP4 list | Kind | Validate with |
|---|---|---|
| PID, wallet, WRPAC, WRPRC, Pub-EAA providers; registrars and registers | explicit, annex profile D–I | `tools/lote_validate.py <list> --profile D` … `--profile I` (implies `--explicit`) |
| List of Trusted Lists (`LoTLType/EUListOfTrustedLists`) | explicit: no annex covers it, but it mocks the EU LoTL, which fully describes its scheme | `tools/lote_validate.py <list> --explicit` |

**The implicit track** is provided for completeness of TS 119 602, for communities whose scheme is known out of band (closed federations, internal lists). It is not used in WP4.

**Consequence for the current WP4 LoTL.** The decoded LoTL (2026-10-06) carries `SchemeName`, which makes it explicit (Table 1: "/" for implicit lists), but lacks `SchemeOperatorAddress`, `SchemeInformationURI`, `StatusDeterminationApproach`, `SchemeTypeCommunityRules` and `PolicyOrLegalNotice`, as well as the mandatory `LoTETag` (clause 5; see etsi_defects.md #20). It should add them, not drop `SchemeName` to pass as implicit: an implicit LoTL would contradict the EU model WP4 mocks.

## 4. The base model and the implicit track are frozen; the explicit track is edited directly

Since 2026-10-15 the project works on the explicit track only (see #3: every WP4 list is explicit). To keep that work simple, the explicit model is the one file edited, and what serves only both kinds of list or implicit lists is frozen:

| File | Status |
|---|---|
| [base/model/lote_model.json](../schema_generator/base/model/lote_model.json) (both kinds of list) | frozen |
| [base/model/schemes/explicit.json](../schema_generator/base/model/schemes/explicit.json), [implicit.json](../schema_generator/base/model/schemes/implicit.json) (track differentials) | frozen |
| [implicit/model/lote_model_implicit.json](../schema_generator/implicit/model/lote_model_implicit.json) | frozen |
| [explicit/model/lote_model_explicit.json](../schema_generator/explicit/model/lote_model_explicit.json) and the profile overlays | active, edited by hand |

- **How it is marked:** each frozen file has `"status": "frozen"` and a `frozen` entry (since, reason, what is still allowed, when to unfreeze); the explicit model has `"status": "active"`.
- **How it is enforced:** [tests/test_frozen.py](../schema_generator/tests/test_frozen.py) pins the SHA-256 of every frozen file. [base/derive_tracks.py](../schema_generator/base/derive_tracks.py), which derived the track models from the base model, is out of the build and refuses to run while the base model is frozen, so it cannot overwrite the explicit model.
- **Still allowed:** correcting a misquoted or misplaced citation in a frozen file, with its hash updated in the same commit.
- **Still built:** the base and implicit schemas are regenerated and tested on every build, so a generator change cannot break them unnoticed; they only stop receiving model changes.
- **Not published:** `lote-schemas publish` copies only the generator's `explicit/` directory into the validator. The validator validates every list as explicit: there is no `--implicit` and no guessing of the track, so a list without the scheme information fails with the Table 1 rules instead of passing as implicit.
- **Consequence:** the explicit model will drift from the base model. Its `scheme` entries still record what Table 1 changes, but a later change in the explicit model is not reflected in the base model or the implicit track.
- **Unfreeze when:** ETSI publishes an implicit binding or an erratum to clause 6, or WP4 needs implicit lists. Then carry the explicit changes made since the freeze back into the base model (or the explicit differential), set the status back, and put `derive_tracks.py` back into the build.

## 5. An optional `Id` attribute on the XML root, as in Forge

The text defines no `Id` on the list. The Forge XSD allows one: `<xsd:attribute name="Id" type="xsd:ID" use="optional"/>` on `ListOfTrustedEntities`. Signing tools use it as the target of a XAdES reference (`<ds:Reference URI="#<Id>">`), as in the IDunion PID list (2026-10-16), whose root carries `Id="TrustedEntitiesList"`.

**Decision.** The explicit model has an optional `Id` attribute of type `xsd:ID` on the root, in the XML binding only (`"from": "forge-xsd"`). JSON has none: Forge JSON has no `Id`, and a JSON list is signed by encapsulation (compact JAdES).

**Why.** Compatibility with Forge and with lists signed by tools that set an `Id`; the text does not forbid one.

**Limits.**
- An `Id` does not make a reference by `Id` conforming. For an H list in XML, the reference must be `URI=""`: "Its ds:SignedInfo element shall contain a ds:Reference element with the URI attribute set to an empty string (i.e. URI=""), so as to refer to the entire document." (H.4 2), p. 66, line 3863). The profiles check it: `H-sig-ref-uri` in H (the text), and `D-sig-ref-uri` … `I-sig-ref-uri` in the other annexes (WP4 rule, #2). So in every profile an `Id` is accepted and signed with the rest of the document, but is not the signature's target; without a profile (`--no-profile`), a reference by `Id` stays allowed.
- Only the root has an `Id`. Forge also has none on other elements.

## Open decisions

### A. Digital identities in JSON: Forge objects or the text's strings; JWK and DID

`ServiceDigitalIdentity` "may contain" X509Certificate, X509SubjectName, PublicKeyValue, X509SKI and OtherId elements (6.6.3.0, p. 33–34). In JSON, the text and Forge disagree on two of them:

| Component | Text | Forge JSON | Project now |
|---|---|---|---|
| `X509Certificate` | "shall be a Base64 string" (6.6.3.1, p. 34, line 2166) | an object `pkiOb`: `{"val": <Base64>, "encoding": <URI>, "specRef": <string>}`, only `val` required | array of Base64 strings (the text) |
| `PublicKeyValue` | "left open and is syntax-specific" (6.6.3.3, p. 34, line 2197) | a JWK ([rfc7517.json](../schema_generator/reference/forge/1960201_json_schema/rfcs/rfc7517.json)) | open: any value |

**1. `X509Certificates`: `{"val": …}` objects or plain strings?** The text gives a Base64 string; Forge wraps it in an object, so a list built from the Forge schema (`[{"val": "MIIC…"}]`) fails the project's schema, and a list built from the text (`["MIIC…"]`) fails Forge. Options: keep the text's form; switch to Forge's form; or accept both (`oneOf`) until ETSI resolves it.

**2. `PublicKeyValues`: adopt Forge's JWK?** JWK is the natural form for keys in JSON, and is the key format of OpenID Federation. If adopted, Forge's JWK must be corrected, because it rejects valid keys ([errors.md](../schema_generator/reference/forge/errors.md)): RFC 7517 §4.3 defines `key_ops` as an array of unique strings, while Forge declares a single string. The corrected definition:

```json
"key_ops": {
  "type": "array",
  "items": { "type": "string", "enum": ["sign", "verify", "encrypt", "decrypt", "wrapKey", "unwrapKey", "deriveKey", "deriveBits"] },
  "uniqueItems": true
}
```

Forge's `kty` enum (`EC`, `RSA`, `oct`) also omits `OKP` (RFC 8037: Ed25519), which some wallet ecosystems use.

**3. Identities other than X.509.** Ecosystems that do not use PKI certificates identify an entity by a key or an identifier:

| Ecosystem | Identity | Where it fits in the text |
|---|---|---|
| OpenID Federation | JWK (or an entity identifier URL) | `PublicKeyValue` (JWK); `OtherId` (URL) |
| Decentralised identifiers | DID (`did:web:…`, `did:key:…`) | `OtherId`, whose "format is left open" (6.6.3.5, p. 35, line 2231) |

The text already allows both: the PKI rule "this component shall contain at least: one X509Certificate element or an X509SKI element" applies only "When using PKI public-key technology" (6.6.3.0, p. 34, line 2151). To decide: whether `OtherId` stays an open string, or takes a typed form that says which kind of identifier it is (e.g. a DID pattern, or an object with a type URI), so that a validator can check it.

