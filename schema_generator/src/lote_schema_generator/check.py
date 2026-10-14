#!/usr/bin/env python3
"""lote_check: check a LoTE schema (XSD or JSON Schema) against the requirements of ETSI TS 119 602.

The requirements come from the model (model/lote_model.json, or --model): every component with its text names and
verified quote (lote_schema_generator/sources.py), its expected name and occurrence per binding, and what is not bound.

    python tools/lote_check.py forge/1960201_xml_schema/*.xsd
    python tools/lote_check.py forge/1960201_json_schema/*.json --show-ok
    python tools/lote_check.py core/1960201_json_schema_text_based.json --json > report.json

What it checks (structure only):
  - every component of the text exists, under the right parent, with the expected name;
  - required vs optional;
  - name spelling (case), and which variant is used where the text itself gives two names;
  - schema files that do not load, and JSON $refs that do not resolve;
  - names the schema defines that the text does not know.
Rules spanning several elements (Table 1, dates, "one entry must be English") and value formats are listed as not
checked: they need instance tests.

Exit code: 0 if no MISMATCH / MISSING / BROKEN finding, 1 otherwise, 2 on usage errors.
"""
import argparse, json, os, sys
from dataclasses import dataclass, field

from .paths import MODEL, ROOT, SCHEMES_DIR  # noqa: F401
DEFAULT_MODEL = MODEL
SEVERITY = ["BROKEN", "MISMATCH", "MISSING", "VARIANT", "EXTRA", "OK"]
FAILING = {"BROKEN", "MISMATCH", "MISSING"}
# Structural helper names that are not text components (wrappers, value fields, attributes).
HELPERS = {"lang", "value", "uriValue", "ServiceType", "Critical", "Name", "URI", "DigitalId", "dateTime", "Extension",
           "type", "Id", "PostalAddress", "OtherLoTEPointer", "LoTEQualifier", "AssociatedBody", "TrustedEntityService",
           "TrustedEntityInformation", "TrustedEntityServices", "LoTEPolicy", "ServiceSupplyPoint", "KeyValue",
           "AssociatedBodyPostalAddress", "AssociatedBodyElectronicAddress", "LoTEType", "SchemeOperatorName",
           "SchemeTerritory", "SchemeTypeCommunityRules"}


@dataclass
class Node:
    """One element / attribute (XML) or property / array item (JSON) found in the schema."""
    name: str
    chain: tuple            # names of the enclosing elements / properties / definitions, outermost first
    min: int
    file: str
    kind: str = "element"   # element | attribute | property | item | definition
    broken: str = ""        # set when the node's own type cannot be resolved
    choice: bool = False    # member of an xsd:choice / oneOf branch: required/optional is not comparable

    @property
    def where(self):
        parts = [p for i, p in enumerate(self.chain + (self.name,)) if i == 0 or p != (self.chain + (self.name,))[i - 1]]
        return f"{os.path.basename(self.file)}: " + "/".join(parts)


@dataclass
class Inventory:
    binding: str
    nodes: list = field(default_factory=list)
    failed: dict = field(default_factory=dict)      # file -> load error
    raw: dict = field(default_factory=dict)         # file -> text, to locate names in files that failed to load


# ------------------------------------------------------------------ XML
def inventory_xml(files):
    import xmlschema
    inv = Inventory("xml")
    for f in files:
        inv.raw[f] = open(f, encoding="utf-8").read()
        try:
            schema = xmlschema.XMLSchema(f)
        except Exception as e:                               # noqa: BLE001 - report any load failure
            inv.failed[f] = str(e).splitlines()[0]
            continue
        for el in schema.elements.values():
            _walk_xml(el, (), 1, f, inv, set())
    return inv


def _walk_xml(el, chain, eff_min, f, inv, seen_types, in_choice=False):
    inv.nodes.append(Node(el.local_name, chain, eff_min, f, "element", choice=in_choice))
    t = el.type
    if t is None or len(chain) > 25 or (t.name and t.name in seen_types):
        return
    if el.target_namespace and "uri.etsi.org/019602" not in el.target_namespace:
        return                                               # do not descend into XMLDSig etc.
    here = chain + (el.local_name,)
    for a in getattr(t, "attributes", {}).values():
        if a.local_name:
            inv.nodes.append(Node(a.local_name, here, 1 if a.use == "required" else 0, f, "attribute"))
    if t.is_complex() and not t.has_simple_content() and t.content is not None:
        _walk_group(t.content, here, 1, f, inv, seen_types | ({t.name} if t.name else set()))


def _walk_group(g, chain, group_min, f, inv, seen_types):
    choice = g.model == "choice" and len(list(g)) > 1
    gmin = group_min * (1 if g.min_occurs else 0)
    for it in g:
        if hasattr(it, "model"):                             # nested group
            _walk_group(it, chain, 0 if choice else gmin, f, inv, seen_types)
        elif getattr(it, "local_name", None):                # element (xsd:any has no name)
            m = 0 if choice else gmin * (1 if it.min_occurs else 0)
            _walk_xml(it, chain, m, f, inv, seen_types, choice)


# ------------------------------------------------------------------ JSON
def inventory_json(files):
    inv = Inventory("json")
    docs = {}
    for f in files:
        inv.raw[f] = open(f, encoding="utf-8").read()
        try:
            docs[os.path.abspath(f)] = json.loads(inv.raw[f])
        except Exception as e:                               # noqa: BLE001
            inv.failed[f] = f"invalid JSON: {e}"
    for f, doc in list(docs.items()):
        w = _JsonWalker(docs, inv)
        if isinstance(doc.get("properties"), dict):
            w.walk(doc, (), f, None)
        for key in ("definitions", "$defs"):
            for name, sub in (doc.get(key) or {}).items():
                inv.nodes.append(Node(name, (), 0, f, "definition"))
                w.walk(sub, (name,), f, None)
    return inv


class _JsonWalker:
    def __init__(self, docs, inv):
        self.docs, self.inv = docs, inv

    def resolve(self, ref, f):
        path, _, frag = ref.partition("#")
        target = os.path.abspath(os.path.join(os.path.dirname(f), path)) if path else f
        if target not in self.docs:
            if not os.path.exists(target):
                return None, None, None
            self.docs[target] = json.load(open(target, encoding="utf-8"))
        node = self.docs[target]
        for part in [p for p in frag.split("/") if p]:
            if not isinstance(node, dict) or part not in node:
                return None, None, None
            node = node[part]
        return node, target, frag.split("/")[-1] if frag else os.path.basename(target)

    def walk(self, s, chain, f, owner, depth=0, trail=()):
        if not isinstance(s, dict) or depth > 40:
            return
        if "$ref" in s:
            sub, tf, name = self.resolve(s["$ref"], f)
            if sub is None:
                if owner is not None:
                    owner.broken = owner.broken or f"$ref {s['$ref']!r} does not resolve"
                return
            target = (tf, s["$ref"].partition("#")[2])
            if target in trail:                              # recursion guard on the reference target
                return
            self.walk(sub, chain + (name,), tf, owner, depth + 1, trail + (target,))
        req = set(s.get("required", []))
        for p, ps in (s.get("properties") or {}).items():
            n = Node(p, chain, 1 if p in req else 0, f, "property")
            self.inv.nodes.append(n)
            self.walk(ps, chain + (p,), f, n, depth + 1, trail)
        items = s.get("items")
        if isinstance(items, dict):
            if "$ref" in items:                              # array of a named definition: record the item too
                _, _, name = self.resolve(items["$ref"], f)
                if name:
                    self.inv.nodes.append(Node(name, chain, 1 if s.get("minItems", 0) >= 1 else 0, f, "item"))
            self.walk(items, chain, f, owner, depth + 1, trail)
        for key in ("allOf", "anyOf", "oneOf"):
            for sub in s.get(key, []) or []:
                self.walk(sub, chain, f, owner, depth + 1, trail)
        if isinstance(s.get("then"), dict):
            self.walk(s["then"], chain, f, owner, depth + 1, trail)


# ------------------------------------------------------------------ comparison
def expected_min(card):
    if not card or card in ("-", "choice") or card.startswith("choice"):
        return None
    return 1 if card.startswith("1") else 0 if card.startswith("0") else None


def expectation(rec, binding):
    """Name and min occurrence the text calls for in this binding (the core target, which follows the text)."""
    if binding == "xml":
        cx = rec["core_xml"]
        return (cx["name"] or "").split(":")[-1], expected_min(cx["cardinality"])
    cj = rec["core_json"]
    card = cj["cardinality"] if cj["status"] == "implemented" else rec["core_xml"]["cardinality"]
    return cj["target_name"], expected_min(card)


def requirements_from_model(model_path=DEFAULT_MODEL):
    """The requirements in the form check() reads, derived from the model: one record per text component (its source in
    sources.py), with the expected name and occurrence per binding, and the text's data types and rules as records that
    are listed as not checked. A component used in several places is checked at its home: the first place outside the
    root, where the direct placement of an implicit list (6.3.0) only copies it."""
    m = json.load(open(model_path, encoding="utf-8"))
    places = {}                                          # source id -> [(parent structure, component, item of)]
    for sn, st in m["structures"].items():
        for c in st["components"]:
            sid = (c.get("source") or {}).get("id")
            if sid:
                places.setdefault(sid, []).append((sn, c, None))
            item = (c.get("items") or {}).get("structure")
            isrc = (m["structures"].get(item, {}).get("source") or {}).get("id") if item else None
            if isrc:
                places.setdefault(isrc, []).append((c["name"], {**c["items"], "name": c["items"]["name"], "min": 1}, c))
    for en, e in m["extensions"].items():
        places.setdefault((e.get("source") or {}).get("id"), []).append((e["in"], {"name": en, "min": 0, **e}, "extension"))
    reqs = []
    for sid, src in SOURCE_INFO(m).items():
        root = m["structures"][m["root"]]
        if sid == (root.get("source") or {}).get("id"):    # the list itself
            reqs.append({"id": sid, "clause": src["clause"], "title": src["title"], "kind": "component",
                         "text": {"names": src["text_names"], "citations": src["citations"], "parent": None},
                         "core_xml": {"name": (root.get("xml") or {}).get("name", m["root"]), "cardinality": "1"},
                         "core_json": {"target_name": m["root"], "cardinality": "1", "status": "implemented"}})
            continue
        if src["kind"] != "component" or sid not in places:
            reqs.append({"id": sid, "clause": src["clause"], "title": src["title"], "kind": src["kind"],
                         "text": {"names": src["text_names"], "citations": src["citations"], "parent": None}})
            continue
        home = [p for p in places[sid] if p[0] != m["root"]] or places[sid]
        parent, c, via = home[0]
        x, j = c.get("xml") or {}, c.get("json") or {}
        content = m["structures"].get(parent, {}).get("content")
        card = lambda mn, b: "choice" if content == "choice" or (content == "any-of" and b == "xml") else ("1" if mn >= 1 else "0..1")
        reqs.append({"id": sid, "clause": src["clause"], "title": src["title"], "kind": "component",
                     "text": {"names": src["text_names"], "citations": src["citations"],
                              "parent": parent, "extension": via == "extension"},
                     "core_xml": {"name": x.get("name") or x.get("wrapper") or c["name"], "cardinality": card(c["min"], "xml")},
                     "core_json": {"target_name": j.get("name", c["name"]), "cardinality": card(j.get("min", c["min"]), "json"),
                                   "status": "not-bound" if j.get("max") == "0" else "implemented"}})
    return reqs


def SOURCE_INFO(m):
    """Every source the model cites (sources.py, as the model resolved it), with its title and kind."""
    from .sources import SOURCES
    out = {}

    def walk(o):
        if isinstance(o, dict):
            src = o.get("source")
            if isinstance(src, dict) and src.get("id") in SOURCES and src["id"] not in out:
                out[src["id"]] = {**src, "title": SOURCES[src["id"]]["title"], "kind": SOURCES[src["id"]]["kind"]}
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(m)
    return out


def scheme_overrides(track):
    """Table 1 column of a track (model/schemes/<track>.json): {(parent, name): 'required' | 'forbidden'}."""
    if not track:
        return {}
    diff = json.load(open(SCHEMES_DIR + f"{track}.json", encoding="utf-8"))
    out = {}
    for e in diff["differential"]["element"]:
        segs = e["path"].split(".")
        out[(segs[-2], segs[-1])] = "forbidden" if e.get("max") == "0" else "required"
    return out


def check(inv, reqs, scheme=None):
    comps = [r for r in reqs if r["kind"] == "component"]
    bname = {r["id"].split("/", 1)[1]: expectation(r, inv.binding)[0] for r in comps}
    known = HELPERS | {n for r in comps for n in r["text"]["names"]} | set(bname.values())
    findings, misspelt = [], set()

    def under(node, parent):
        return parent is None and node.chain == () or parent is not None and parent in node.chain

    scheme = scheme or {}
    for r in comps:
        exp, emin = expectation(r, inv.binding)
        parent_text = r["text"]["parent"]
        rule = scheme.get((parent_text, r["text"]["names"][0]))
        if rule == "required":
            emin = 1
        parent = bname.get(parent_text, parent_text) if parent_text else None
        anywhere = r["text"].get("extension")
        cands = [n for n in inv.nodes if (anywhere or under(n, parent)) and (anywhere or n.kind != "definition")]
        exact = [n for n in cands if n.name == exp]
        f = {"id": r["id"], "clause": r["clause"], "title": r["title"], "expected": exp, "parent": parent,
             "citation": r["text"]["citations"][0], "text_names": r["text"]["names"]}
        direct = [n for n in exact if n.chain and n.chain[-1] == parent]    # a forbidden component: only as a direct child
        if inv.binding == "json" and r["core_json"]["status"] == "not-bound":
            rule = "forbidden"                                # not part of the JSON binding: expected absent
        if rule == "forbidden":
            f.update(status="MISMATCH" if direct else "OK", where=direct[0].where if direct else "",
                     detail=("present, but not allowed here" if direct else "absent, as required (forbidden in this track or not part of this binding)"))
        elif not exact and any(v == "forbidden" and k[1] == parent_text for k, v in scheme.items()):
            f.update(status="OK", where="", detail=f"absent: its parent {parent_text} is forbidden in this track (Table 1)")
        elif exact:
            n = min(exact, key=lambda n: len(n.chain))
            f["where"] = n.where
            prefix = n.chain + (n.name,)
            inner = [d for d in inv.nodes if d.broken and d.file == n.file and d.chain[:len(prefix)] == prefix]
            if n.broken or inner:
                f.update(status="BROKEN", detail=n.broken or f"{inner[0].name}: {inner[0].broken}")
            elif emin is not None and not n.choice and not (anywhere and n.chain == ()) and n.min != emin:
                # (a global extension element has no occurrence of its own: its extension list decides)
                f.update(status="MISMATCH", detail=f"text: {'required' if emin else 'optional'}; "
                                                   f"schema: {'required' if n.min else 'optional'}")
            else:
                f.update(status="OK", detail="")
            others = [v for v in r["text"]["names"] if v != r["text"]["names"][0]]
            if others:
                f["conflict"] = f"text also uses {', '.join(others)}"
        else:
            ci = [n for n in cands if n.name.lower() == exp.lower()]
            var = [n for n in cands for v in r["text"]["names"] if n.name == v and v != exp]
            dead = [fl for fl, txt in inv.raw.items() if fl in inv.failed and f'"{exp}"' in txt]
            if ci:
                f.update(status="MISMATCH", where=ci[0].where, detail=f"spelled {ci[0].name!r}; text: {exp!r}")
                misspelt.add(ci[0].name)
            elif var:
                f.update(status="VARIANT", where=var[0].where,
                         detail=f"uses the text's alternative name {var[0].name!r} instead of {exp!r}",
                         conflict=f"text uses {' OR '.join(r['text']['names'])}")
            elif dead:
                f.update(status="BROKEN", where=os.path.basename(dead[0]),
                         detail=f"defined in a file that does not load: {inv.failed[dead[0]][:140]}")
            else:
                sib = sorted({n.name for n in inv.nodes if parent and n.chain and n.chain[-1] == parent})
                f.update(status="MISSING", where="",
                         detail=f"not defined under {parent or 'the root'}" + (f"; found there: {', '.join(sib)}" if sib else ""))
        findings.append(f)

    comp_parents = set(bname.values()) | {bname.get(r["text"]["parent"], r["text"]["parent"]) for r in comps}
    seen = set()
    for n in inv.nodes:
        if n.kind in ("item", "definition"):
            continue
        if n.chain and n.chain[-1] in comp_parents and n.name not in known | misspelt and (n.chain[-1], n.name) not in seen:
            seen.add((n.chain[-1], n.name))
            findings.append({"id": "-", "clause": "-", "title": n.name, "status": "EXTRA", "where": n.where,
                             "detail": f"{n.kind} {n.name!r} under {n.chain[-1]} is not a component of the text",
                             "citation": None, "text_names": []})
    for fl, err in inv.failed.items():
        findings.append({"id": "-", "clause": "-", "title": os.path.basename(fl), "status": "BROKEN", "where": os.path.basename(fl),
                         "detail": f"schema file does not load: {err[:200]}", "citation": None, "text_names": []})
    not_checked = [r["id"] for r in reqs if r["kind"] != "component"]
    return findings, not_checked


# ------------------------------------------------------------------ report
def text_report(files, binding, findings, not_checked, show_ok):
    out = [f"LoTE schema check: {binding.upper()} | " + ", ".join(os.path.basename(f) for f in files),
           "Requirements: ETSI TS 119 602 V1.1.1 (2025-11), from the model (model/lote_model.json)", ""]
    for sev in SEVERITY:
        items = [f for f in findings if f["status"] == sev]
        if not items or (sev == "OK" and not show_ok):
            continue
        out.append(f"== {sev} ({len(items)})")
        for f in items:
            c = f["citation"]
            head = f"{sev:<8} {f['clause']} {f['title']}" + (f"  (p. {c['page']}, L{c['line']})" if c else "")
            out.append(head)
            if f.get("detail"):
                out.append(f"         {f['detail']}")
            if f.get("where"):
                out.append(f"         schema: {f['where']}")
            if c and sev != "OK":
                out.append(f"         text:   \"{c['quote']}\"")
        out.append("")
    conflicts = [f for f in findings if f.get("conflict")]
    if conflicts:
        out.append(f"== TEXT CONFLICTS ({len(conflicts)}): the text names these components in more than one way")
        for f in conflicts:
            used = f["where"].split("/")[-1] if f.get("where") else "none"
            out.append(f"         {f['clause']} {' OR '.join(f['text_names'])}: schema uses {used}")
        out.append("")
    counts = {s: sum(f["status"] == s for f in findings) for s in SEVERITY}
    out.append("Summary: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v))
    out.append(f"Not checked here ({len(not_checked)} rules/data types, need instance tests): " + ", ".join(not_checked))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a LoTE XSD or JSON Schema against ETSI TS 119 602 requirements.")
    ap.add_argument("schemas", nargs="+", help="schema files: all .xsd or all .json (core plus its extension files)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="the model the requirements come from (default: %(default)s)")
    ap.add_argument("--json", action="store_true", help="print findings as JSON instead of text")
    ap.add_argument("--show-ok", action="store_true", help="also list components that match")
    ap.add_argument("--scheme", choices=["explicit", "implicit"],
                    help="check a track's schema: apply its Table 1 column (model/schemes/<track>.json)")
    a = ap.parse_args(argv)
    exts = {os.path.splitext(f)[1].lower() for f in a.schemas}
    if exts not in ({".xsd"}, {".json"}):
        ap.error("give either only .xsd files or only .json files")
    for f in a.schemas:
        if not os.path.isfile(f):
            ap.error(f"no such file: {f}")
    reqs = requirements_from_model(a.model)
    inv = inventory_xml(a.schemas) if exts == {".xsd"} else inventory_json(a.schemas)
    findings, not_checked = check(inv, reqs, scheme_overrides(a.scheme))
    if a.json:
        print(json.dumps({"binding": inv.binding, "files": a.schemas, "findings": findings, "not_checked": not_checked},
                         indent=2, ensure_ascii=False))
    else:
        print(text_report(a.schemas, inv.binding, findings, not_checked, a.show_ok))
    return 1 if any(f["status"] in FAILING for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
