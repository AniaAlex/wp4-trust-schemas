"""Derive the two scheme tracks of ETSI TS 119 602 from the core model: explicit and implicit scheme information
(clause 6.3.0, Table 1).

Inputs (written by hand, next to this script):
  model/lote_model.json                  the core model: what both kinds of list allow
  model/schemes/explicit.json, implicit.json   FHIR-style differentials: what each track changes, quoted from the text
Outputs (derived, do not edit):
  ../explicit/model/lote_model_explicit.json   snapshots: the core with the differential applied, read by the
  ../implicit/model/lote_model_implicit.json   generators (gen_json, gen_xsd) and, for explicit, by the profiles D-I

Snapshot semantics: 'min' raises the occurrence; 'max: "0"' keeps the component with max 0, and the generators read the
snapshot through allowed(), so the track's schemas do not allow it at all. A changed component records the rule in
'scheme' (id, row, citation), so a validation report can cite Table 1 for a required and for a forbidden component.
Core constraints the track's structure already decides (R-Table1, R-SchemeInfoPlacement) move to 'superseded'.

Checks (nothing is written otherwise):
  - every path resolves in the core model, through structures used only once (a change must not leak to other uses);
  - every element only narrows the core (no lower min, no prohibited mandatory component);
  - every element has a citation.
Quotes are proofread by hand against docs/spec/ts_119602v010101p.txt (see model/README.md).

Frozen since 2026-10-15: the core model and the implicit track are frozen and the explicit track is edited by hand
(docs/project_decisions_vs_etsi.md #4). While the core model has "status": "frozen" the script refuses to run, so it
cannot overwrite the hand-edited explicit model. It is kept for unfreezing.

Run: python base/derive_tracks.py
"""
import copy, json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__)) + "/"
ROOT = os.path.dirname(BASE.rstrip("/")) + "/"
MODEL = BASE + "model/lote_model.json"
SCHEMES_DIR = BASE + "model/schemes/"
SNAPSHOT = {t: ROOT + f"{t}/model/lote_model_{t}.json" for t in ("explicit", "implicit")}


def resolve(model, path, errors, where):
    """Return the component at a path, checking that every structure on the way is used only once."""
    uses = {}
    for s in model["structures"].values():
        for c in s["components"]:
            t = c.get("structure") or (c.get("items") or {}).get("structure")
            if t:
                uses[t] = uses.get(t, 0) + 1
    segs = path.split(".")
    if segs[0] != model["root"]:
        errors.append(f"{where}: path does not start at the root {model['root']}"); return None
    struct, comp = model["root"], None
    for i, s in enumerate(segs[1:], 1):
        comp = next((c for c in model["structures"][struct]["components"] if c["name"] == s), None)
        if comp is None:
            errors.append(f"{where}: {struct} has no component {s!r}"); return None
        if i < len(segs) - 1:
            struct = comp.get("structure") or (comp.get("items") or {}).get("structure")
            if uses.get(struct, 0) > 1:
                errors.append(f"{where}: structure {struct} is used more than once; a change would leak")
    return comp


def superseded(snap):
    """Move the constraints the track's structure already decides out of 'constraint' into 'superseded', so the generated
    schemas of the track carry no dead rules: a check that names a component the track removed, or a co-occurrence whose
    required components are all mandatory in the track."""
    for s in snap["structures"].values():
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


def derive(core, track, errors):
    diff = json.load(open(SCHEMES_DIR + f"{track}.json", encoding="utf-8"))
    snap = copy.deepcopy(core)
    for e in diff["differential"]["element"]:
        where = f"{track} {e.get('id')}"
        if not e.get("citation"):
            errors.append(f"{where}: no citation")
        comp = resolve(core, e["path"], errors, where)
        if comp is None:
            continue
        if e.get("min", 0) < comp["min"]:
            errors.append(f"{where}: lowers min {comp['min']} -> {e['min']}")
        if e.get("max") == "0" and comp["min"] >= 1:
            errors.append(f"{where}: prohibits a mandatory component")
        s_comp = resolve(snap, e["path"], errors, where)
        if e.get("max") == "0":
            s_comp["max"] = 0
        else:
            s_comp["min"] = e["min"]
        s_comp["scheme"] = {"id": e["id"], "row": e["row"], "citation": e["citation"]}
    superseded(snap)
    snap["model"] = f"{core['model']} - {track} scheme information (snapshot)"
    snap["generated_by"] = f"base/derive_tracks.py: base/model/lote_model.json + base/model/schemes/{track}.json"
    snap["scheme"] = track
    return snap, len(diff["differential"]["element"])


def main():
    core = json.load(open(MODEL, encoding="utf-8"))
    if core.get("status") == "frozen":
        sys.exit("base/model/lote_model.json is frozen: the explicit model is edited by hand and must not be overwritten. "
                 "See its 'frozen' entry and docs/project_decisions_vs_etsi.md #4.")
    errors, out = [], {}
    for track in ("explicit", "implicit"):
        out[track] = derive(core, track, errors)
    if errors:
        print("\n".join(errors), file=sys.stderr); sys.exit(1)
    for track, (snap, n) in out.items():
        os.makedirs(os.path.dirname(SNAPSHOT[track]), exist_ok=True)
        with open(SNAPSHOT[track], "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False); f.write("\n")
        print(f"{track}: {n} differential elements -> {os.path.relpath(SNAPSHOT[track], ROOT)}")


if __name__ == "__main__":
    main()
