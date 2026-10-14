"""Generate the six LoTE profile schemas (Annexes D-I) from the core model and the profile overlays.

Inputs : explicit/model/lote_model_explicit.json (the explicit track; every annex requires a scheme explicit list) and
         model/profiles/*.json (FHIR-style differentials).
Outputs: explicit/generated/profiles/lote_profile_<X>_<name>.json  - JSON Schema: allOf the explicit core + the overlay
         explicit/generated/profiles/lote_profile_<X>_<name>.sch   - ISO Schematron, used with the explicit lote_core.xsd + .sch

    python gen_profiles_from_model.py                 # names as the current core schema
    python gen_profiles_from_model.py --names text    # the text's names where a decision is pending

Translation of a differential element (path -> binding location):
  min 1                      JSON: name in the parent's 'required'          XML: assert the child exists
  max "0"                    JSON: 'not': {}                                 XML: assert the child is absent
  fixed[x] (+ acceptAlso)    JSON: 'const' (or 'enum')                       XML: assert the value
  binding (required)         JSON: 'enum'                                    XML: assert the value is one of the set
  constraint with 'check'    JSON: 'contains' / 'minItems'                   XML: XPath assertion
  check 'months-after'       JSON: listed in $comment (no comparison)        XML: XPath 1.0 date comparison
  constraint without check   listed as a rules-layer requirement (JSON $comment and x-rules-layer, Schematron comment)

Every rule carries its id and the citation of its overlay element, so a validation report can name the rule and the
sentence of the annex it enforces:
  JSON       each rule is its own allOf entry: {"$anchor": id, "title": id, "description": text + citation, <rule>}
  Schematron <sch:pattern id="p-id"> / <sch:assert id="id">, and the message starts with [id] and ends with the citation.
Rule ids: '<annex>-<component>-<required|prohibited|fixed|values>' for structural rules, '<annex>-<component>-<xml|json>-
<required|prohibited>' for a rule of one binding (an element's 'xml' / 'json'), the constraint key for invariants
(the same ids as build_profiles.rule_ids; the overlay element's 'id' is its first rule).
"""
import argparse, json, os, re
from xml.sax.saxutils import escape, quoteattr

from .build_schemes import allowed
from .paths import PROFILES_DIR, PROFILES_GEN, ROOT, SNAPSHOT  # noqa: F401

MODEL = SNAPSHOT["explicit"]                                 # the profiles narrow the explicit track (x.1)
OVERLAYS = PROFILES_DIR
OUT = PROFILES_GEN
NS = "http://uri.etsi.org/019602/v1#"


class Steps:
    """Resolve a model path into binding steps (JSON key / XML name per segment)."""

    def __init__(self, model, names):
        self.m, self.names = model, names
        self.ext_prefix = {"OtherAssociatedBodies": "tie", "ServiceUniqueIdentifier": "sie"}

    def jname(self, comp):
        j = comp.get("json") or {}
        if self.names == "current" and j.get("current_name"):
            return j["current_name"]
        return j.get("name", comp["name"])

    def component(self, struct, name):
        return next(x for x in self.m["structures"][struct]["components"] if x["name"] == name)

    def resolve(self, path):
        segs = path.split(".")
        root = self.m["structures"][self.m["root"]]
        steps = [{"kind": "root", "json": segs[0], "xml": (root.get("xml") or {}).get("name", segs[0]), "struct": self.m["root"]}]
        struct, comp, pending = self.m["root"], None, None
        for s in segs[1:]:
            if pending is not None:
                steps.append({"kind": "item", "xml": s, "struct": pending.get("structure")})
                struct, pending, comp = pending.get("structure"), None, None
                continue
            if comp is not None and s in ("uriValue", "value"):
                steps.append({"kind": "field", "json": s, "xml": "URI" if s == "uriValue" else "Name"})
                continue
            if comp is not None and comp.get("value") == "extension-list":
                steps.append({"kind": "ext", "json": s, "xml": f"{self.ext_prefix[s]}:{s}", "list": steps[-1]})
                continue
            comp = self.component(struct, s)
            x = comp.get("xml") or {}
            sx = self.m["structures"][struct].get("xml") or {}
            xml = x.get("name", s)
            if x.get("form") == "attribute":
                xml = "@" + s
            elif x.get("wrapper"):
                xml = f"{x['wrapper']}/lote:{s}"
            elif sx.get("item_wrapper"):                      # identifiers inside DigitalId
                xml = f"{sx['item_wrapper']}/lote:{s}"
            steps.append({"kind": "component", "json": self.jname(comp), "xml": xml, "comp": comp, "struct": struct})
            struct, pending = comp.get("structure"), comp.get("items")
        return steps


# ------------------------------------------------------------------ match specs
def rx(s):
    return re.escape(s).replace("\\:", ":").replace("\\/", "/")


SCH_ONLY = ("months-after",)                                 # check types JSON Schema cannot express
def component_name(e):
    return [s for s in e["path"].split(".") if s not in ("uriValue", "value")][-1]


def rid(e, what):
    """Id of a structural rule of element e (see build_profiles.rule_ids)."""
    return f"{e['id'].split('-')[0]}-{component_name(e)}-{what}"


def what_text(e, what):
    """The rule in words, for reports: 'LoTEType is required', 'LoTEType must be "http://..."', ..."""
    n = component_name(e)
    if what == "fixed":
        vals = [next(e[k] for k in ("fixedUri", "fixedInteger", "fixedString") if k in e)] + e.get("acceptAlso", [])
        return f"{n} must be " + " or ".join(f'"{v}"' for v in vals)
    return {"required": f"{n} is required", "prohibited": f"{n} must not be present",
            "values": f"{n} must be one of the allowed values"}[what]


def citation(e):
    c = e.get("citation") or {}
    return f"{e['row']} (p. {c.get('page')}, line {c.get('line')}): \"{c.get('quote')}\""


def months_after(m, b, n):
    """XPath 1.0: date-time m (YYYY-MM-DDThh:mm:ssZ), when present, is at most n months after b. Months are compared as
    year*12 + month; in the same month the rest (day and time) decides, so 31 Aug + 6 months allows up to the end of Feb."""
    mon = lambda x: f"(number(substring({x}, 1, 4)) * 12 + number(substring({x}, 6, 2)))"
    rest = lambda x: f"number(translate(substring({x}, 9), 'T:Z', ''))"
    return (f"not({m}) or {mon(m)} < {mon(b)} + {n} or "
            f"({mon(m)} = {mon(b)} + {n} and {rest(m)} <= {rest(b)})")


def match_json(spec):
    if "equals" in spec:
        return {"const": spec["equals"]}
    if "startsWith" in spec:
        neg = "".join(f"(?!{rx(n)})" for n in spec.get("notStartsWith", []))
        return {"pattern": "^" + neg + "(?:" + "|".join(rx(x) for x in spec["startsWith"]) + ")"}
    return {"pattern": "^" + rx(spec["prefix"]) + "(" + "|".join(spec["codes"]) + ")" + (".+" if spec["rest"] else "") + "$"}


def match_xpath(spec, n):
    if "equals" in spec:
        return f"{n} = '{spec['equals']}'"
    if "startsWith" in spec:
        pos = " or ".join(f"starts-with({n}, '{x}')" for x in spec["startsWith"])
        neg = "".join(f" and not(starts-with({n}, '{x}'))" for x in spec.get("notStartsWith", []))
        return f"({pos}){neg}"
    p, codes = spec["prefix"], " " + " ".join(spec["codes"]) + " "
    rest = f"substring-after({n}, '{p}')"
    if spec["rest"]:
        return f"starts-with({n}, '{p}') and contains('{codes}', concat(' ', substring({rest}, 1, 2), ' ')) and string-length({rest}) > 2"
    return f"starts-with({n}, '{p}') and contains('{codes}', concat(' ', {rest}, ' '))"


# ------------------------------------------------------------------ JSON
class JsonProfile:
    def __init__(self, steps_resolver):
        self.R = steps_resolver
        self.root = {}

    def node(self, steps):
        """Return (parent object node, json name, node) for the last step, creating the nesting."""
        node, parent, name = self.root, None, None
        for st in steps:
            if st["kind"] == "root":
                parent, name = self.root, st["json"]
                node = self.root.setdefault("properties", {}).setdefault(st["json"], {})
            elif st["kind"] == "component":
                parent, name = node, st["json"]
                node = node.setdefault("properties", {}).setdefault(st["json"], {})
            elif st["kind"] == "item":
                node = node.setdefault("items", {})
            elif st["kind"] == "field":
                node = node.setdefault("items", {}).setdefault("properties", {}).setdefault(st["json"], {})
            elif st["kind"] == "ext":
                parent, name = node, st["json"]                 # node = the extension list
        return parent, name, node

    @staticmethod
    def rule(target, rule_id, text, e, body):
        """Add one rule to target as its own allOf entry, annotated with its id and citation."""
        target.setdefault("allOf", []).append(
            {"$anchor": rule_id, "title": rule_id, "description": f"{text}. {citation(e)}", **body})

    def apply(self, e):
        steps = self.R.resolve(e["path"])
        parent, name, node = self.node(steps)
        last = steps[-1]
        if e.get("min", 0) >= 1:
            r = rid(e, "required")
            if last["kind"] == "ext":                             # list component required + an entry carrying the extension
                lst_parent, lst_name, _ = self.node(steps[:-1])
                self.rule(lst_parent, r, what_text(e, "required"), e, {"required": [lst_name]})
                node.setdefault("allOf", []).append({"contains": {"required": [name]}})
            elif last["kind"] != "field":
                self.rule(parent, r, what_text(e, "required"), e, {"required": [name]})
        if e.get("max") == "0":
            self.rule(node, rid(e, "prohibited"), what_text(e, "prohibited"), e, {"not": {}})
        for fk in ("fixedUri", "fixedInteger", "fixedString"):
            if fk in e:
                vals = [e[fk]] + e.get("acceptAlso", [])
                self.rule(node, rid(e, "fixed"), what_text(e, "fixed"), e,
                          {"enum": vals} if len(vals) > 1 else {"const": e[fk]})
        if "binding" in e:
            self.rule(node, rid(e, "values"), what_text(e, "values"), e, {"enum": e["binding"]["valueSet"]})
        jb = e.get("json") or {}                              # rules of the JSON binding only, citing the binding's quote
        eb = {**e, "citation": jb.get("citation") or e.get("citation")}
        if jb.get("max") == "0":
            self.rule(node, rid(e, "json-prohibited"), f"{name} is not part of the JSON binding", eb, {"not": {}})
        if jb.get("min", 0) >= 1:
            self.rule(parent, rid(e, "json-required"), f"{name} is required in JSON", eb, {"required": [name]})
        for c in e.get("constraint", []):
            ck = c.get("check")
            if not ck or ck["type"] in SCH_ONLY:
                continue
            if ck["component"] == ".":
                target = node
            else:
                struct = last.get("struct") if last["kind"] == "root" else (last.get("comp") or {}).get("structure") or last.get("struct")
                comp = self.R.component(struct, ck["component"])
                target = node.setdefault("properties", {}).setdefault(self.R.jname(comp), {})
            if ck["type"] == "min-items":
                self.rule(target, c["key"], c["human"], e, {"minItems": ck["min"]})
                continue
            inner = {"properties": {ck["field"]: match_json(ck["match"])}, "required": [ck["field"]]}
            for n in reversed(ck.get("nested", [])):
                inner = {"properties": {n: {"contains": inner}}, "required": [n]}
            self.rule(target, c["key"], c["human"], e, {"contains": inner})


# ------------------------------------------------------------------ Schematron
class SchProfile:
    def __init__(self, steps_resolver):
        self.R = steps_resolver
        self.rules = []                                          # (id, context, test, message)

    def xpath(self, steps):
        parts = []
        for st in steps:
            parts.append(st["xml"] if st["xml"].startswith(("@", "tie:", "sie:")) else ("lote:" + st["xml"] if not st["xml"].startswith("ds:") else st["xml"]))
        return "/" + "/".join(parts)

    def add(self, rule_id, ctx, test, text, e):
        self.rules.append((rule_id, ctx, test, f"[{rule_id}] {text}. {citation(e)}"))

    def structural(self, e, what, ctx, test):
        self.add(rid(e, what), ctx, test, what_text(e, what), e)

    def apply(self, e):
        steps = self.R.resolve(e["path"])
        last = steps[-1]
        if last["kind"] == "ext":
            list_steps = steps[:-1]
            ctx = self.xpath(list_steps[:-1])
            rel = self.xpath(list_steps[-1:])[1:] + f"/lote:Extension/{last['xml']}"
        else:
            ctx = self.xpath(steps[:-1]) if len(steps) > 1 else "/"
            rel = self.xpath(steps[-1:])[1:]
        if e.get("min", 0) >= 1 and last["kind"] != "field":
            self.structural(e, "required", ctx, rel)
        if e.get("max") == "0":
            self.structural(e, "prohibited", ctx, f"not({rel})")
        full = self.xpath(steps) if last["kind"] != "ext" else f"{ctx}/{rel}"
        for fk in ("fixedUri", "fixedInteger", "fixedString"):
            if fk in e:
                vals = [e[fk]] + e.get("acceptAlso", [])
                self.structural(e, "fixed", full, " or ".join(f". = '{v}'" for v in vals))
        if "binding" in e:
            self.structural(e, "values", full, " or ".join(f". = '{v}'" for v in e["binding"]["valueSet"]))
        xb = e.get("xml") or {}                               # rules of the XML binding only, citing the binding's quote
        eb = {**e, "citation": xb.get("citation") or e.get("citation")}
        if xb.get("min", 0) >= 1:
            self.add(rid(e, "xml-required"), ctx, rel, f"{component_name(e)} is required in XML", eb)
        if xb.get("max") == "0":
            self.add(rid(e, "xml-prohibited"), ctx, f"not({rel})", f"{component_name(e)} is not part of the XML binding", eb)
        for c in e.get("constraint", []):
            ck = c.get("check")
            if not ck:
                continue
            here = self.xpath(steps)
            add = lambda test: self.add(c["key"], here, test, c["human"], e)
            if ck["type"] == "months-after":
                struct = (last.get("comp") or {}).get("structure") or last.get("struct")
                add(months_after(self.dt(struct, ck["component"]), self.dt(struct, ck["base"]), ck["months"]))
                continue
            if ck["component"] == ".":
                items = [f"lote:{(last['comp'].get('items') or {}).get('name')}"]
                base = "/".join(items)
            else:
                struct = (last.get("comp") or {}).get("structure") or last.get("struct")
                comp = self.R.component(struct, ck["component"])
                inner_item = "lote:Name" if comp.get("value", "") in ("multilang-texts", "scheme-name") else \
                    "lote:URI" if comp.get("value", "") in ("multilang-uris", "electronic-address") else \
                    f"lote:{(comp.get('items') or {}).get('name')}"
                base = f"lote:{(comp.get('xml') or {}).get('name', comp['name'])}/{inner_item}"
            if ck["type"] == "min-items":
                add(f"count({base}) >= {ck['min']}")
                continue
            field = "." if ck["field"] in ("uriValue", "value") else f"lote:{ck['field']}"
            cond = match_xpath(ck["match"], field)
            for n in reversed(ck.get("nested", [])):
                # nested list n of the current item structure: its items are the model's item name
                cond_item = self.nested_item(last, n)
                cond = f"lote:{n}/lote:{cond_item}[{cond}]"
            add(f"{base}[{cond}]")

    def dt(self, struct, name):
        """XPath of a date-time component; NextUpdate holds its value in an optional dateTime child."""
        comp = self.R.component(struct, name)
        return f"lote:{name}" + ("/lote:dateTime" if "dateTime child" in (comp.get("xml") or {}).get("form", "") else "")

    def nested_item(self, last, n):
        struct = (last["comp"].get("items") or {}).get("structure")
        return (self.R.component(struct, n).get("items") or {}).get("name")

    def text(self, title, business):
        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               f"<!-- {escape(title)} (generated by lote_schema_generator/gen_profiles_from_model.py). Use together with lote_core.xsd and lote_core.sch.",
               "     Rules-layer requirements (not checkable by a schema):"]
        out += [f"       - {escape(b)}" for b in business] + ["-->",
                '<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">',
                f'  <sch:ns prefix="lote" uri="{NS}"/>',
                '  <sch:ns prefix="tie" uri="http://uri.etsi.org/019602/v1/TrustedEntityExtensions"/>',
                '  <sch:ns prefix="sie" uri="http://uri.etsi.org/019602/v1/ServiceInformationExtensions"/>',
                '  <sch:ns prefix="ds" uri="http://www.w3.org/2000/09/xmldsig#"/>']
        # one pattern per assertion: a node matching several contexts would otherwise only fire the first rule
        for rule_id, ctx, test, msg in self.rules:
            out += [f'  <sch:pattern id="p-{rule_id}">', f'    <sch:rule context={quoteattr(ctx)}>',
                    f'      <sch:assert id="{rule_id}" test={quoteattr(test)}>{escape(msg)}</sch:assert>',
                    "    </sch:rule>", "  </sch:pattern>"]
        return "\n".join(out + ["</sch:schema>", ""])


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--names", choices=["current", "text"], default="current")
    a = ap.parse_args()
    model = allowed(json.load(open(MODEL, encoding="utf-8")))
    R = Steps(model, a.names)
    os.makedirs(OUT, exist_ok=True)
    for fn in sorted(os.listdir(OVERLAYS)):
        ov = json.load(open(OVERLAYS + fn, encoding="utf-8"))
        letter = ov["annex"]
        base = f"lote_profile_{fn[:-5]}"
        js, sch = JsonProfile(R), SchProfile(R)
        business, json_only = [], []                          # json_only: checked by Schematron, not by JSON Schema
        rules_layer = []                                       # the same, structured: what a rules checker reads
        for e in ov["differential"]["element"]:
            js.apply(e)
            sch.apply(e)
            for c in e.get("constraint", []):
                item = f"{c['key']}: {c['human']} [checkable: {c['checkable']}] {citation(e)}"
                if not c.get("check"):
                    business.append(item)
                elif c["check"]["type"] in SCH_ONLY:
                    json_only.append(item)
                else:
                    continue
                rules_layer.append({"id": c["key"], "human": c["human"], "checkable": c["checkable"],
                                    **({"check": c["check"]} if c.get("check") else {}),
                                    "row": e["row"], "citation": e.get("citation")})
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"{ov['title']} (LoTE profile, JSON binding, generated)",
            "description": f"Generated by lote_schema_generator/gen_profiles_from_model.py from model/profiles/{fn} "
                           f"(names: {a.names}). A scheme-explicit LoTE (explicit track) that also meets Annex {letter}.",
            "$comment": "Not expressible in JSON Schema, to be enforced by a business-rules layer (see x-rules-layer): "
                        + " | ".join(json_only + business),
            "x-rules-layer": rules_layer,
            "allOf": [{"$ref": "../lote_core.schema.json"}] + js.root.get("allOf", []),
            "properties": js.root["properties"],
        }
        with open(OUT + base + ".json", "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False); f.write("\n")
        with open(OUT + base + ".sch", "w", encoding="utf-8") as f:
            f.write(sch.text(ov["title"], business))
        print(f"Annex {letter}: {base}.json, {base}.sch ({len(sch.rules)} assertions, {len(business)} rules-layer items)")


if __name__ == "__main__":
    main()
