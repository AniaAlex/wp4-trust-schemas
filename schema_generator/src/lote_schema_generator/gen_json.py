"""Generate the core LoTE JSON Schema (draft 2020-12) from the abstract model base/model/lote_model.json.

The model says WHAT the text requires (components, occurrence, value types, rules); this script holds HOW the JSON binding
expresses it (the binding conventions below). Nothing component-specific is written here.

    python gen_json.py                  # base/generated/lote_core.schema.json, names as the current core schema
    python gen_json.py --names text     # use the text's names where a decision is pending

JSON binding conventions:
  - the document is {"<root>": {...}}; every structure is an object in $defs, closed (additionalProperties: false);
  - a component is a property named after the component, or its 'json.name' override; min >= 1 -> listed in 'required';
  - max 'n' or 'items' -> an array (minItems: at least 1); 'items' with a structure -> array of that structure;
  - content 'choice' -> oneOf of arrays of single-component objects (the Forge form of PolicyOrLegalNotice);
  - content 'any-of' -> object with minProperties: 1;
  - value types -> one $defs entry each (below); multilingual sequences require an 'en' entry (has-entry check, R-English);
  - extension lists -> arrays of open objects, with 'Critical' required where the component says criticality 'required',
    and the known extensions of the model as optional properties;
  - constraints: co-occurrence and required-if checks -> if/then, either-or -> oneOf, has-entry -> contains; constraints without a check
    (rules-layer) -> listed in the root $comment.
"""
import argparse, json, os

from .model import CODE_ONLY, allowed
from .paths import BASE_GEN, MODEL, ROOT, SNAPSHOT, TRACK_GEN

OUT = BASE_GEN + "lote_core.schema.json"
# --scheme: the base (both kinds of list) or one track, read from its snapshot (explicit|implicit/model/)
SCHEMES = {"base": (MODEL, OUT),
           "explicit": (SNAPSHOT["explicit"], TRACK_GEN["explicit"] + "lote_core.schema.json"),
           "implicit": (SNAPSHOT["implicit"], TRACK_GEN["implicit"] + "lote_core.schema.json")}

# Value type -> ($defs name, JSON Schema). Patterns are the binding's rendering of the value-type descriptions.
# BMP ranges as regex escapes; characters above U+FFFF as literal characters (portable across regex dialects).
PLAIN_TEXT = "^(?!\\uFEFF)[^\\u0000-\\u001F\\u007F-\\u009F\\uE000-\\uF8FF\U000E0000-\U000E007F\U000F0000-\U0010FFFF]+$"


def constraints(model, check_type=None):
    """(structure, constraint) pairs of the model, in structure order; only those with the given check type if one is given."""
    return [(n, c) for n, s in model["structures"].items() for c in s.get("constraint", [])
            if check_type is None or (c.get("check") or {}).get("type") == check_type]


def has_entry(model):
    """The has-entry check (R-English): the entry every multilingual sequence must contain, as a JSON 'contains' schema."""
    (_, c), = constraints(model, "has-entry")
    ck = c["check"]
    return ck, {"properties": {ck["field"]: {"const": ck["match"]["equals"]}}}


def value_defs(model):
    vt = model["value_types"]
    d = {
        "integer": ("Integer", {"type": "integer"}),
        "positive-integer": ("PositiveInteger", {"type": "integer", "minimum": 1}),
        "non-negative-integer": ("NonNegativeInteger", {"type": "integer", "minimum": 0}),
        "uri": ("URI", {"type": "string", "format": "uri", "minLength": 1}),
        "uri-list": ("URIList", {"type": "array", "items": {"$ref": "#/$defs/URI"}, "minItems": 1}),
        "utc-datetime": ("DateTime", {"type": "string", "format": "date-time",
                                      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"}),
        "plain-text": ("PlainText", {"type": "string", "minLength": 1, "pattern": PLAIN_TEXT}),
        "language-tag": ("LanguageTag", {"type": "string", "pattern": "^[a-z]{2,3}(-[A-Za-z0-9]{1,8})*$"}),
        "multilang-text": ("MultiLangString", {"type": "object", "properties": {"lang": {"$ref": "#/$defs/LanguageTag"},
                                                                                 "value": {"$ref": "#/$defs/PlainText"}},
                                               "required": ["lang", "value"], "additionalProperties": False}),
        "multilang-uri": ("MultiLangURI", {"type": "object", "properties": {"lang": {"$ref": "#/$defs/LanguageTag"},
                                                                             "uriValue": {"$ref": "#/$defs/URI"}},
                                           "required": ["lang", "uriValue"], "additionalProperties": False}),
        "multilang-texts": ("MultiLangStrings", {"type": "array", "items": {"$ref": "#/$defs/MultiLangString"},
                                                 "minItems": 1}),
        "multilang-uris": ("MultiLangURIs", {"type": "array", "items": {"$ref": "#/$defs/MultiLangURI"},
                                             "minItems": 1}),
        "scheme-name": ("SchemeNameStrings", {"type": "array", "items": {"allOf": [
            {"$ref": "#/$defs/MultiLangString"}, {"properties": {"value": {"pattern": "^[A-Z]{2,}:.+$"}}}]},
            "minItems": 1}),
        "electronic-address": ("ElectronicAddress", {"type": "array", "items": {"$ref": "#/$defs/MultiLangURI"}, "minItems": 2,
                                                     "allOf": [{"contains": {"properties": {"uriValue": {"pattern": "^mailto:"}}}},
                                                               {"contains": {"properties": {"uriValue": {"pattern": "^https?://"}}}}]}),
        "country-code": ("CountryCode", {"type": "string", "pattern": "^[A-Z]{2,}$", "not": {"enum": ["GB", "GR"]}}),
        "country-code-a": ("CountryCodeA", {"enum": vt["country-code-a"]["codes"]}),
        "mime-type": ("MimeType", {"type": "string", "pattern": "^[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+(\\s*;.*)?$"}),
        "base64": ("Base64", {"type": "string", "contentEncoding": "base64",
                              "pattern": "^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$"}),
        "string": ("NonEmptyString", {"type": "string", "minLength": 1}),
        "typed-uri": ("TypedURI", {"type": "object", "properties": {"ServiceType": {"$ref": "#/$defs/URI"},
                                                                     "uriValue": {"$ref": "#/$defs/URI"}},
                                   "required": ["uriValue"], "additionalProperties": False}),
        "open": ("Open", {}),
        "signature": ("Signature", {}),
        "extension-list": ("Extension", {"type": "object", "properties": {"Critical": {"type": "boolean"}}}),
    }
    ck, en = has_entry(model)
    for t in ck["in"]["value_types"]:                       # the has-entry check on the multilingual value types
        schema = d[t][1]
        if "allOf" in schema:
            schema["allOf"].append({"contains": en})
        else:
            schema["contains"] = en
    missing = set(vt) - set(d)
    if missing:
        raise SystemExit(f"no JSON rendering for value types: {sorted(missing)}")
    out = {}
    for t, (name, schema) in d.items():
        out[name] = {"description": vt[t]["description"] + cite(vt[t]["source"]), **schema}
    return {t: name for t, (name, _) in d.items()}, out


def cite(source):
    if not source:
        return ""
    c = source["citations"][0]
    return f" Clause {source['clause']}, p. {c['page']}: \"{c['quote']}\""


def component_citation(m):
    if m.get("source"):
        return cite(m["source"]).strip()
    c = m.get("citation")
    return f"p. {c['page']}: \"{c['quote']}\"" if c else ""


# ------------------------------------------------------------------ generation
class Gen:
    def __init__(self, model, names, source="base/model/lote_model.json"):
        self.m, self.names, self.source = model, names, source
        self.vname, self.defs = value_defs(model)
        self.has_entry, self.en = has_entry(model)

    def json_name(self, m):
        j = m.get("json") or {}
        if self.names == "current" and j.get("current_name"):
            return j["current_name"]
        return j.get("name", m["name"])

    def ref_value(self, t):
        return {"$ref": f"#/$defs/{self.vname[t]}"}

    def item_schema(self, items):
        if items.get("structure"):
            s = {"$ref": f"#/$defs/{items['structure']}"}
        else:
            s = self.ref_value(items["value"])
        return s

    def extension_list(self, m):
        item = [{"$ref": "#/$defs/Extension"}]
        if m.get("criticality") == "required":
            item.append({"required": ["Critical"]})
        known = {n: e for n, e in self.m["extensions"].items() if e["in"] == m["name"]}
        if known:
            item.append({"properties": {n: (self.extension_schema(e)) for n, e in known.items()}})
        return {"type": "array", "items": {"allOf": item}, "minItems": 1}

    def extension_schema(self, e):
        if e.get("items"):
            return {"type": "array", "items": self.item_schema(e["items"]), "minItems": e["items"]["min"]}
        return self.ref_value(e["value"])

    def component_schema(self, m):
        if m.get("items"):
            s = {"type": "array", "items": self.item_schema(m["items"]), "minItems": max(1, m["items"]["min"])}
            if m["items"].get("structure") in self.has_entry["in"]["lists_of"]:
                s["contains"] = self.en                              # has-entry on lists of multilingual structures
        elif m.get("value") == "extension-list":
            s = self.extension_list(m)
        elif m.get("max") == "n":
            inner = {"$ref": f"#/$defs/{m['structure']}"} if m.get("structure") else self.ref_value(m["value"])
            s = {"type": "array", "items": inner, "minItems": 1}
        elif m.get("structure"):
            s = {"$ref": f"#/$defs/{m['structure']}"}
        else:
            s = self.ref_value(m["value"])
        if (m.get("json") or {}).get("nullable"):
            s = {"oneOf": [s, {"type": "null"}]}
        desc = component_citation(m)
        notes = [m.get("note"), (m.get("json") or {}).get("reason")]
        desc = " ".join(x for x in [desc] + notes if x)
        return {"description": desc, **s} if desc else s

    def structure(self, name, s):
        components = s["components"]
        desc = (component_citation(s) or "") + (" " + s["note"] if s.get("note") else "")
        if s["content"] == "choice":
            branches = []
            for m in components:
                obj = {"type": "object", "properties": {self.json_name(m): self.ref_value(m["value"])},
                       "required": [self.json_name(m)], "additionalProperties": False}
                br = {"type": "array", "items": obj, "minItems": 1}
                if name in self.has_entry["in"]["choices"] and m.get("value", "").startswith("multilang"):
                    br["contains"] = {"properties": {self.json_name(m): self.en}}
                branches.append(br)
            return {"description": desc.strip(), "oneOf": branches}
        props, req = {}, []
        for m in components:
            if (m.get("json") or {}).get("max") == "0":          # not part of the JSON binding (e.g. Signature: encapsulation)
                continue
            jn = self.json_name(m)
            props[jn] = self.component_schema(m)
            jmin = (m.get("json") or {}).get("min", m["min"])
            if jmin >= 1:
                req.append(jn)
        out = {"description": desc.strip(), "type": "object", "properties": props}
        if req:
            out["required"] = req
        if s["content"] == "any-of":
            out["minProperties"] = 1
        out["additionalProperties"] = False
        return out

    def path_to(self, start, target):
        """Breadth-first search for the chain of JSON steps from structure start to structure target."""
        from collections import deque
        q, seen = deque([(start, [])]), {start}
        while q:
            cur, steps = q.popleft()
            if cur == target:
                return steps
            for m in self.m["structures"][cur]["components"]:
                nxt = (m.get("items") or {}).get("structure") or m.get("structure")
                if nxt and nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, steps + [(self.json_name(m), bool(m.get("items") or m.get("max") == "n"))]))
        return None

    def nest(self, steps, leaf):
        for name, is_array in reversed(steps):
            leaf = {"properties": {name: ({"items": leaf} if is_array else leaf)}}
        return leaf

    def apply_constraints(self, defs):
        """Translate the constraints' checks: co-occurrence -> if/then on the structure; required-if -> if/then on the root
        (the condition may lie anywhere in the list); either-or -> oneOf of the two placements; has-entry -> 'contains',
        applied with the value types above."""
        for sname, c in constraints(self.m, "co-occurrence"):
            ck = c["check"]
            defs[sname]["if"] = {"description": f"{c['key']} (clause {c['clause']}): explicit scheme information",
                                 "anyOf": [{"required": [x]} for x in ck["if_any_present"]]}
            defs[sname]["then"] = {"required": ck["then_required"]}
        for sname, c in constraints(self.m, "required-if"):
            ck, root = c["check"], self.m["root"]
            cond = {"minimum": ck["if"]["min"]}
            for name in reversed(ck["if"]["path"].split(".")[1:]):
                cond = {"properties": {name: cond}, "required": [name]}
            then = self.nest(self.path_to(root, sname), {"required": [ck["component"]]})
            defs[root]["if"] = {"description": f"{c['key']} (clause {c['clause']}): {c['human']}", **cond}
            defs[root]["then"] = then
        for sname, c in constraints(self.m, "either-or"):
            ck, d = c["check"], defs[sname]
            branch = lambda req, absent: {"required": req, "not": {"anyOf": [{"required": [x]} for x in absent]}}
            d["description"] = (d.get("description", "") + f" {c['key']} (clause {c['clause']}): {c['human']}").strip()
            d["oneOf"] = [branch(ck["first"], ck["second"]), branch(ck["second"], ck["first"])]

    def build(self):
        defs = {}
        for name, s in self.m["structures"].items():
            defs[name] = self.structure(name, s)
        for n, e in self.m["extensions"].items():
            defs[n] = {"description": cite(e["source"]).strip(), **self.extension_schema(e)}
        self.apply_constraints(defs)
        defs.update(self.defs)
        business = [f"{c['clause']} {c['human']}" + (" (checked by the validator's code)" if c.get("check") else "")
                    for _, c in constraints(self.m) if not c.get("check") or c["check"]["type"] in CODE_ONLY]
        root = self.m["root"]
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "ETSI TS 119 602 V1.1.1 - List of Trusted Entities (LoTE), JSON binding (generated)",
            "description": f"Generated by lote_schema_generator/gen_json.py from {self.source} (names: {self.names}). "
                           "Do not edit; change the model or the generator.",
            "$comment": "Requirements JSON Schema cannot express, to be enforced by a business-rules layer: " + " ".join(business),
            "type": "object",
            "properties": {root: {"$ref": f"#/$defs/{root}"}},
            "required": [root],
            "additionalProperties": False,
            "$defs": defs,
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", choices=["current", "text"], default="current",
                    help="where a naming decision is pending: keep the current core schema's name, or use the text's name")
    ap.add_argument("--scheme", choices=list(SCHEMES), default="base",
                    help="base: both kinds of list (Table 1 as a rule); explicit / implicit: one track (Table 1 column as structure)")
    ap.add_argument("--out", help="output file (default: per --scheme)")
    a = ap.parse_args()
    model_path, a.out = SCHEMES[a.scheme][0], a.out or SCHEMES[a.scheme][1]
    model = allowed(json.load(open(model_path, encoding="utf-8")))
    schema = Gen(model, a.names, os.path.relpath(model_path, ROOT)).build()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=True); f.write("\n")  # ASCII only: no invisible characters in the file (PlainText's ranges)
    print(f"wrote {a.out}: {len(schema['$defs'])} definitions")


if __name__ == "__main__":
    main()
