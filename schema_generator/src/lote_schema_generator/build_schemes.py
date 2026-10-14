"""Build the two scheme tracks of ETSI TS 119 602: explicit and implicit scheme information (clause 6.3.0, Table 1).

The core model (model/lote_model.json) holds what both kinds of list allow. Each track is a FHIR-style differential
on it, as the annex profiles are, and a generated snapshot: the full model of that track.

Outputs:
  model/schemes/explicit.json, implicit.json        differentials: what each track changes, quoted from the text
  explicit/model/lote_model_explicit.json                 snapshots: the core with the differential applied, read by the
  implicit/model/lote_model_implicit.json                 generators (gen_json.py, gen_xsd.py) and by the profiles D-I

Snapshot semantics: 'min' raises the occurrence; 'max: "0"' keeps the component with max 0, and the generators read the
snapshot through allowed(), so the track's schemas do not allow it at all. A changed component records the rule in
'scheme' (id, row, citation), so a validation report can cite Table 1 for a required and for a forbidden component.
Core constraints the track's structure already decides (R-Table1, R-SchemeInfoPlacement) move to 'superseded'.

Checks (the build fails otherwise):
  - every quote is found verbatim in the spec, exactly once (page and line computed);
  - every path resolves in the core model, through structures used only once (a change must not leak to other uses);
  - every element only narrows the core (no lower min, no prohibited mandatory component).
"""
import copy, json, os, sys

from . import spec_text as bm                              # spec index and quote normaliser
from .paths import MODEL, ROOT, SCHEMES_DIR, SNAPSHOT

DIFF_DIR = SCHEMES_DIR

LSI = "LoTE.ListAndSchemeInformation"
DIRECT = ["LoTEVersionIdentifier", "LoTESequenceNumber", "SchemeOperatorName", "ListIssueDateTime", "NextUpdate"]
EXPLICIT_ADDITIONAL = ["LoTEType", "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules",
                       "SchemeTerritory", "PolicyOrLegalNotice"]
IMPLICIT_FORBIDDEN = ["SchemeName", "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules",
                      "PolicyOrLegalNotice"]
Q_EXPLICIT = "In case the scheme information is explicit the LoTE shall contain this component."
Q_DIRECT = ("In case the LoTE does not contain this component, information about the list itself shall be provided within "
            "the list directly through the presence of the LoTEVersionIdentifier, the LoTESequenceNumber, the "
            "SchemeOperatorName, the ListIssueDateTime, and the NextUpdate elements.")
Q_ADDITIONAL = ("In case the scheme information is explicit this component shall contain, in addition, LoTEType, the "
                "SchemeInformationURI, the StatusDeterminationApproach, the SchemeTypeCommunityRules, the SchemeTerritory, "
                "and the PolicyOrLegalNotice elements.")


def el(prefix, path, row, quote, comment=None, **f):
    name = path.split(".")[-1]
    what = "prohibited" if f.get("max") == "0" else "required"
    e = {"id": f"{prefix}-{name}-{what}", "row": row, "path": path, **f, "_quote": quote}
    if comment:
        e["comment"] = comment
    return e


def elements(track):
    if track == "explicit":
        return ([el("EXP", LSI, "6.3.0 Explicit scheme information", Q_EXPLICIT, min=1)]
                + [el("EXP", f"LoTE.{n}", "6.3.0 List information placed directly in the list", Q_DIRECT, max="0",
                      comment="Derived: an explicit list contains ListAndSchemeInformation, and the direct placement is "
                              "only for a list without it.") for n in DIRECT]
                + [el("EXP", f"{LSI}.{n}", "6.3.0 Explicit scheme information (Semantics)", Q_ADDITIONAL, min=1)
                   for n in EXPLICIT_ADDITIONAL]
                + [el("EXP", f"{LSI}.{n}", f"Table 1 {n}", q, min=1,
                      comment="Table 1 only: the Semantics paragraph of 6.3.0 omits it (etsi_defects.md #19). Table 1 is "
                              "followed.")
                   for n, q in (("SchemeOperatorAddress", "SchemeOperatorAddress O M"), ("SchemeName", "SchemeName / M"))])
    return [el("IMP", f"{LSI}.{n}", f"Table 1 {n}", f"{n} / M", max="0",
               comment="'/' in the implicit column: shall not be present.") for n in IMPLICIT_FORBIDDEN]


def allowed(model):
    """The model without the components its track forbids (max 0): what the schemas and profiles are generated from."""
    m = copy.deepcopy(model)
    for s in m["structures"].values():
        s["components"] = [c for c in s["components"] if c.get("max") != 0]
    return m


TITLE = {"explicit": "Explicit scheme information: the LoTE describes its scheme itself (Table 1, explicit column)",
         "implicit": "Implicit scheme information: the scheme is known out of band (Table 1, implicit column)"}


def resolve(model, path, errors, where):
    """Return (structure name, component) for a path, checking that every structure on the way is used only once."""
    uses = {}
    for sn, s in model["structures"].items():
        for c in s["components"]:
            t = c.get("structure") or (c.get("items") or {}).get("structure")
            if t:
                uses[t] = uses.get(t, 0) + 1
    segs = path.split(".")
    struct, comp = model["root"], None
    for s in segs[1:]:
        comp = next((c for c in model["structures"][struct]["components"] if c["name"] == s), None)
        if comp is None:
            errors.append(f"{where}: {struct} has no component {s!r}"); return None, None
        if s != segs[-1]:
            struct = comp.get("structure") or (comp.get("items") or {}).get("structure")
            if uses.get(struct, 0) > 1:
                errors.append(f"{where}: structure {struct} is used more than once; a change would leak")
    return struct, comp


def superseded(snap):
    """Move the constraints the track's structure already decides out of 'constraint' into 'superseded', so the generated
    schemas of the track carry no dead rules: a check that names a component the track removed, or a co-occurrence whose
    required components are all mandatory in the track."""
    for sname, s in snap["structures"].items():
        names = {c["name"]: c for c in s["components"] if c.get("max") != 0}
        keep = []
        for c in s.get("constraint", []):
            ck = c.get("check") or {}
            named = ck.get("if_any_present", []) + ck.get("then_required", []) + ck.get("first", []) + ck.get("second", [])
            if any(n not in names for n in named):
                why = "names a component this track does not allow"
            elif ck.get("type") == "co-occurrence" and all(names[n]["min"] >= 1 for n in ck["then_required"]):
                why = "all required components are mandatory in this track"
            else:
                keep.append(c); continue
            s.setdefault("superseded", []).append({"key": c["key"], "reason": f"decided by the track's structure: {why}"})
        s["constraint"] = keep


def main():
    core = json.load(open(MODEL, encoding="utf-8"))
    text, pos_line, page_of_line = bm.load_spec()
    errors = []

    def cite(quote, where):
        q = bm.norm(quote)
        k = text.find(q)
        if k < 0 or text.find(q, k + 1) >= 0:
            errors.append(f"{where}: quote {'not found' if k < 0 else 'not unique'}: {quote!r}"); return None
        return {"quote": quote, "page": page_of_line[pos_line[k] - 1], "line": pos_line[k]}

    for track in ("explicit", "implicit"):
        els = elements(track)
        snap = copy.deepcopy(core)
        for e in els:
            where = f"{track} {e['id']}"
            e["citation"] = cite(e.pop("_quote"), where)
            struct, comp = resolve(core, e["path"], errors, where)
            if comp is None:
                continue
            if e.get("min", 0) < comp["min"]:
                errors.append(f"{where}: lowers min {comp['min']} -> {e['min']}")
            if e.get("max") == "0" and comp["min"] >= 1:
                errors.append(f"{where}: prohibits a mandatory component")
            s_struct, s_comp = resolve(snap, e["path"], errors, where)
            if e.get("max") == "0":
                s_comp["max"] = 0
            else:
                s_comp["min"] = e["min"]
            s_comp["scheme"] = {"id": e["id"], "row": e["row"], "citation": e["citation"]}
        superseded(snap)
        diff = {"id": f"lote-scheme-{track}", "title": TITLE[track], "derivation": "constraint",
                "baseDefinition": "model/lote_model.json", "differential": {"element": els}}
        snap["model"] = f"{core['model']} - {track} scheme information (snapshot)"
        snap["generated_by"] = f"lote_schema_generator/build_schemes.py: model/lote_model.json + model/schemes/{track}.json"
        snap["scheme"] = track
        if errors:
            continue
        os.makedirs(DIFF_DIR, exist_ok=True)
        with open(DIFF_DIR + f"{track}.json", "w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2, ensure_ascii=False); f.write("\n")
        os.makedirs(os.path.dirname(SNAPSHOT[track]), exist_ok=True)
        with open(SNAPSHOT[track], "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False); f.write("\n")
        n = sum(len(s["components"]) for s in allowed(snap)["structures"].values())
        print(f"{track}: {len(els)} differential elements; snapshot {os.path.relpath(SNAPSHOT[track], ROOT)} ({n} components)")
    if errors:
        print("\n".join(errors)); sys.exit(1)


if __name__ == "__main__":
    main()
