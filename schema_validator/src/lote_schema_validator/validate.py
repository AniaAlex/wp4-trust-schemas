"""lote-validate: validate a LoTE (XML or JSON) against the generated schemas and report every failure with the
sentence of ETSI TS 119 602 it breaks: rule id, location in the list, clause or annex row, page, line and quote.

    lote-validate list.xml --profile D       # explicit track + Annex D (PID providers)
    lote-validate list.json                  # explicit track + the annex profile the list's LoTEType names
    lote-validate list.xml --profile D --json > report.json

    from lote_schema_validator import validate
    report = validate("list.json", profile="D")          # report.valid, report.track, report.findings

Schemas: the package data in schemas/explicit/ (the generator's explicit/ directory, published by `lote-schemas publish`),
or LOTE_SCHEMAS_DIR. Every list is validated as a scheme explicit list (clause 6.3.0, Table 1, explicit column): WP4
lists are explicit, and the implicit track is frozen and not published (docs/project_decisions_vs_etsi.md #3, #4). A
list without the scheme information therefore fails with the Table 1 rules (EXP-SchemeName-required, ...).

Profile: every list is checked against the profile its LoTEType names, which must be exactly one of the six annex types
fixed in Tables D.1-I.1, or the List of Trusted Lists type (http://uri.etsi.org/19602/LoTLType/EUListOfTrustedLists, a
WP4 value in the model's lote_types_without_profile: profile LoTL, the explicit track only, no annex covers it). Any other
LoTEType, or none, stops with "invalid profile" and the list of valid URIs (exit 2), whatever the flags. --profile and
--lotl name the profile expected; when the list declares another one, the declared one is used, with a warning.
--explicit is temporarily not in use.

Layers, in order:
  XML   the track's XSD (lote_core.xsd), its Schematron (lote_core.sch), profile Schematron (generated/profiles/*.sch)
  JSON  the track's JSON Schema, or the profile's (generated/profiles/*.json allOf the explicit track), then the profile rules JSON
        Schema cannot express (x-rules-layer entries with a 'check', e.g. the 6-month NextUpdate rule)
Rule ids and citations:
  profile rules     the overlay element of the rule id (schemas/explicit/model/profiles/*.json): D-LoTEType-fixed
  core rules        the model constraint (R-...) or, for the other core Schematron patterns, the model source of their
                    clause; a JSON if/then or either-or of a constraint carries the constraint's key
  schema errors     the error's location in the list is resolved through the explicit model (schemas/explicit/model/)
                    to a model place: a structure, or a component of one. The rule id is that place plus what is wrong,
                    and the citation is the place's source:
                      <Structure>-<Component>-required | -not-allowed | -occurrence | -value | -items
                      <Structure>-<Attribute>-not-allowed       an attribute the text does not define
                      LoTE-root                                 the root is not the LoTE root
                    A component the track requires or forbids (Table 1 / 6.3.0) uses the rule of its 'scheme' instead:
                    EXP-SchemeName-required, EXP-NextUpdate-prohibited (a forbidden component has max 0).
Signatures are not validated here (JAdES / XAdES, see the annexes' x.4).

Exit code: 0 if valid, 1 if any failure, 2 on usage errors.
"""
import argparse, glob, json, os, re, sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

SCHEMAS = os.environ.get("LOTE_SCHEMAS_DIR") or str(Path(__file__).resolve().parent / "schemas")
EXPLICIT = os.path.join(SCHEMAS, "explicit")             # the generator's explicit/ directory (models and schemas)
TRACKS = {"explicit": {"gen": os.path.join(EXPLICIT, "generated", "base"),
                       "model": os.path.join(EXPLICIT, "model", "lote_model_explicit.json")}}
PROFILES = os.path.join(EXPLICIT, "generated", "profiles")  # the profile schemas
OVERLAYS = os.path.join(EXPLICIT, "model", "profiles")      # the profile overlays (rule citations)
LOTETYPE = "LoTE.ListAndSchemeInformation.LoTEType"         # the overlay path whose fixedUri names the annex


class ProfileError(ValueError):
    """No annex profile can be chosen: the list's LoTEType is not an annex type, the LoTL type, and no --profile."""
SVRL = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
PREFIX = {"http://www.w3.org/2000/09/xmldsig#": "ds"}       # prefixes in reported locations; other namespaces are lote:
CORE_SCH_CLAUSE = {"LanguageTagCase": "6.1.4", "CountryCodeExclusions": "6.1.5", "ElectronicAddressContent": "6.3.5.2"}


@dataclass
class Finding:
    layer: str
    rule: str
    location: str
    message: str
    source: dict = field(default_factory=dict)          # ref (clause or annex row), page, line, quote


# ------------------------------------------------------------------ the model: where an error is, what it cites
@dataclass
class Node:
    """A place in a list, resolved through the model. kind: 'doc' (above the JSON root), 'struct' (an element or object
    of a structure), 'anyof' (the item wrapper of an any-of structure, e.g. DigitalId), 'list' (a list component holding
    items), 'wrapper' (the XML wrapper of a repeated structure), 'choice' (one entry of a JSON choice array) or 'leaf' (a
    value component, including the helper elements inside it: Name, URI, dateTime ...). comp is the component of
    owner through which the place was reached; name is the element or property name in the list."""
    kind: str
    struct: str = None
    comp: dict = None
    owner: str = None
    name: str = ""

    def label(self):
        """The model id of the place: the structure, or <structure>-<component>."""
        return self.struct if self.kind in ("struct", "anyof", "choice") else f"{self.owner}-{self.comp['name']}"


def xml_name(c):
    return re.sub(r"^\w+:", "", (c.get("xml") or {}).get("name") or c["name"])


def is_attribute(c):
    return (c.get("xml") or {}).get("form", "").startswith("attribute")


def json_names(c):
    j = c.get("json") or {}
    return {c["name"], j.get("name"), j.get("current_name")} - {None}


class Citations:
    def __init__(self, track):
        self.track = track
        self.model = json.load(open(TRACKS[track]["model"], encoding="utf-8"))
        self.S = self.model["structures"]
        self.root = self.model["root"]
        self.root_xml = (self.S[self.root].get("xml") or {}).get("name") or self.root
        self.forbidden = {(sn, c["name"]): c for sn, st in self.S.items()          # components the track forbids (max 0)
                          for c in st["components"] if c.get("max") == 0}
        for st in self.S.values():
            st["components"] = [c for c in st["components"] if c.get("max") != 0]
        self.rules = {c["key"]: c for s in self.S.values() for c in s.get("constraint", [])}
        self.by_clause = {}                               # clause -> first source with citations (model sources)

        def collect(o):
            if isinstance(o, dict):
                src = o.get("source")
                if isinstance(src, dict) and src.get("clause") and src.get("citations"):
                    self.by_clause.setdefault(src["clause"], src)
                for v in o.values():
                    collect(v)
            elif isinstance(o, list):
                for v in o:
                    collect(v)
        collect(self.model)
        self.profile_rules = {}                           # rule id -> (overlay element, constraint or None)
        for fn in glob.glob(os.path.join(OVERLAYS, "*.json")):
            for e in json.load(open(fn, encoding="utf-8"))["differential"]["element"]:
                self.profile_rules[e["id"]] = (e, None)
                for c in e.get("constraint", []) + (e.get("xml") or {}).get("constraint", []):
                    self.profile_rules[c["key"]] = (e, c)
                for what in ("required", "prohibited", "fixed", "values", "xml-required", "xml-prohibited",
                             "json-required", "json-prohibited"):
                    rid = f"{e['id'].split('-')[0]}-{component_name(e)}-{what}"
                    self.profile_rules.setdefault(rid, (e, None))

    @staticmethod
    def fmt(ref, cite):
        cite = cite or {}
        return {"ref": ref, "page": cite.get("page"), "line": cite.get("line"), "quote": cite.get("quote")}

    def profile(self, rule_id):
        e, c = self.profile_rules.get(rule_id, (None, None))
        if not e:
            return {}
        if c and c.get("citation"):                       # a constraint with its own sentence (e.g. H.4 2) for D-sig-ref-uri)
            src = self.fmt(c.get("row", e["row"]), c["citation"])
            return {**src, "from": "wp4"} if c.get("from") == "wp4" else src
        for bnd in ("xml", "json"):                       # a rule of one binding cites that binding's quote
            if f"-{bnd}-" in rule_id and (e.get(bnd) or {}).get("citation"):
                return self.fmt(e["row"], e[bnd]["citation"])
        return self.fmt(e["row"], e.get("citation"))

    def core_rule(self, rule_id):
        if rule_id in self.rules:
            r = self.rules[rule_id]
            cites = (r.get("source") or {}).get("citations") or [r.get("citation")]
            return self.fmt(f"Clause {r['clause']}", cites[0])
        clause = CORE_SCH_CLAUSE.get(rule_id)
        src = self.by_clause.get(clause)
        return self.fmt(f"Clause {clause}", src["citations"][0]) if src else {}

    # -------------------------------------------------------------- citations of model places
    def structure(self, sname):
        """Citation of a structure: its source, or its own citation."""
        st = self.S[sname]
        src = st.get("source") or {}
        if src.get("citations"):
            return self.fmt(f"Clause {src['clause']}", src["citations"][0])
        if st.get("citation"):
            return self.fmt(f"Clause {st['clause']}" if st.get("clause") else sname, st["citation"])
        return {}

    def component(self, owner, c, presence=False):
        """Citation of component c of structure owner. For an error about presence, a component the track made required
        cites the track rule (Table 1 / 6.3.0). A component without a citation cites its structure, or else its owner."""
        if presence and c.get("scheme"):
            return self.fmt(c["scheme"]["row"], c["scheme"]["citation"])
        src = c.get("source") or {}
        if src.get("citations"):
            best = next((x for x in src["citations"] if c["name"] in (x.get("quote") or "")), src["citations"][0])
            return self.fmt(f"Clause {src['clause']}", best)
        if c.get("citation"):
            return self.fmt(c["name"], c["citation"])
        return (self.structure(c["structure"]) if c.get("structure") else {}) or self.structure(owner)

    def place(self, node):
        if node.kind == "doc":
            return self.structure(self.root)
        return self.structure(node.struct) if node.kind in ("struct", "anyof", "choice") else self.component(node.owner, node.comp)

    def scheme(self, c):
        """The track rule on component c: its rule id and citation."""
        return c["scheme"]["id"], self.fmt(c["scheme"]["row"], c["scheme"]["citation"])

    def required(self, node, c, name):
        """Rule id and citation of a missing required component c of the structure at node."""
        if c is None:
            return f"{node.label()}-{name}-required", self.place(node)
        if c.get("scheme") and c["scheme"]["id"].endswith("-required"):
            return self.scheme(c)
        return f"{node.struct}-{c['name']}-required", self.component(node.struct, c, presence=True)

    def root_finding(self, layer, location, found):
        rid = f"{self.root}-root"
        if layer == "xsd":
            ns = (self.S[self.root].get("xml") or {}).get("namespace")
            why = f"The root element is {found}; the root element of a LoTE is '{self.root_xml}' in the namespace {ns}."
        else:
            why = f"{found}; a LoTE in JSON is an object with the single property '{self.root}'."
        return Finding(layer, rid, location, why, self.structure(self.root))

    # -------------------------------------------------------------- XML: element path -> model place
    def xml_child(self, node, name):
        if node.kind == "leaf":
            return node                                   # helper elements inside a value (Name, URI, dateTime ...)
        if node.kind == "list":
            it = node.comp["items"]
            if name != it["name"]:
                return None
            if it.get("structure"):
                return Node("struct", it["structure"], node.comp, node.owner, name)
            return Node("leaf", None, node.comp, node.owner, name)
        if node.kind == "wrapper":
            return Node("struct", node.comp["structure"], node.comp, node.owner, name) if name == node.comp["name"] else None
        st = self.S[node.struct]
        if node.kind == "struct" and st.get("content") == "any-of" and \
                name == (st.get("xml") or {}).get("item_wrapper", "Identifier"):
            return Node("anyof", node.struct, node.comp, node.owner, name)
        c = self.xml_component(node.struct, name)
        if c is None:
            return None
        if (c.get("xml") or {}).get("wrapper") == name:
            return Node("wrapper", None, c, node.struct, name)
        if c.get("items"):
            return Node("list", None, c, node.struct, name)
        if c.get("structure"):
            return Node("struct", c["structure"], c, node.struct, name)
        return Node("leaf", None, c, node.struct, name)

    def xml_component(self, sname, name):
        for c in self.S[sname]["components"]:
            if not is_attribute(c) and name in (xml_name(c), (c.get("xml") or {}).get("wrapper")):
                return c
        return None

    def xml_resolve(self, steps):
        """The model place of an element path (local names from the root), or None if the root is not the LoTE root.
        A path that leaves the model stops at the deepest place the model knows."""
        if not steps or steps[0] != self.root_xml:
            return None
        node = Node("struct", self.root, None, None, steps[0])
        for name in steps[1:]:
            nxt = self.xml_child(node, name)
            if nxt is None:
                break
            node = nxt
        return node

    # -------------------------------------------------------------- JSON: instance path -> model place
    def json_component(self, sname, key):
        return next((c for c in self.S[sname]["components"] if key in json_names(c)), None)

    def json_child(self, node, key):
        if node.kind == "leaf":
            return node                                   # inside a value (a multilingual entry, an extension ...)
        if node.kind == "doc":
            return Node("struct", self.root, None, None, key) if key == self.root else None
        if node.kind == "list":
            if not isinstance(key, int):
                return None
            target = (node.comp.get("items") or {}).get("structure") or node.comp.get("structure")
            return Node("struct", target, node.comp, node.owner, node.name) if target else node
        if node.kind == "choice":
            c = self.json_component(node.struct, key) if isinstance(key, str) else None
            return Node("leaf", None, c, node.struct, key) if c else None
        if isinstance(key, int):                          # a choice structure is an array of one-component objects
            return Node("choice", node.struct, node.comp, node.owner, node.name) \
                if self.S[node.struct].get("content") == "choice" else None
        c = self.json_component(node.struct, key)
        if c is None:
            return None
        if c.get("items") or c.get("max") == "n" or c.get("value") == "extension-list":
            return Node("list", None, c, node.struct, key)
        if c.get("structure"):
            return Node("struct", c["structure"], c, node.struct, key)
        return Node("leaf", None, c, node.struct, key)

    def json_resolve(self, path):
        node = Node("doc", name="(document)")
        for key in path:
            nxt = self.json_child(node, key)
            if nxt is None:
                break
            node = nxt
        return node


def component_name(e):
    return [s for s in e["path"].split(".") if s not in ("uriValue", "value")][-1]


def local(tag):
    return re.sub(r"^.*[}:]", "", tag or "")


# ------------------------------------------------------------------ XML
def xsd_finding(C, e):
    """An XSD error as a finding: the model place of its element path gives the rule id (model id + what is wrong)
    and the citation."""
    reason = e.reason or str(e.message)
    loc = e.path or "/"
    steps = [local(s) for s in re.sub(r"\[\d+\]", "", e.path or "").split("/") if s]
    node = C.xml_resolve(steps)
    if node is None or re.search(r"is not an element of the schema", reason):
        tag = getattr(getattr(e, "obj", None), "tag", None) or (steps[0] if steps else "?")
        ns = re.match(r"\{([^}]*)\}", tag)
        found = f"'{local(tag)}' in the namespace {ns.group(1)}" if ns else f"'{local(tag)}' in no namespace"
        return C.root_finding("xsd", loc, found)
    m = re.search(r"Tag (.*?) expected", reason)
    expected = [local(x) for x in re.findall(r"'([^']+)'", m.group(1))] if m else []
    unexpected = re.search(r"Unexpected child with tag '([^']+)'", reason)
    incomplete = re.search(r"The content of element '[^']+' is not complete", reason)
    attr_not_allowed = re.match(r"'([^']+)' attribute not allowed", reason)
    attr_missing = re.search(r"missing required attribute '([^']+)'", reason)
    attr_value = re.match(r"attribute ([\w:]+)=", reason)
    in_struct = node.kind in ("struct", "anyof")

    if unexpected and in_struct:
        x = local(unexpected.group(1))
        fb = C.forbidden.get((node.struct, x))
        if fb:                                                         # the track forbids it here (max 0)
            rid, src = C.scheme(fb)
            return Finding("xsd", rid, loc, f"'{x}' is not allowed in {node.name} in a scheme {C.track} list.", src)
        known = C.xml_component(node.struct, x)
        if expected:
            want = C.xml_component(node.struct, expected[0])
            rid, src = C.required(node, want, expected[0])
            why = (f"'{expected[0]}' is missing or out of order in {node.name}: it is expected before '{x}'." if known
                   else f"'{x}' is not an element of {node.name}; '{expected[0]}' is expected here.")
            return Finding("xsd", rid, loc, why, src)
        if known:
            why = (f"'{x}' is a second identifier in {node.name}: each {node.name} holds exactly one identifier."
                   if node.kind == "anyof" else f"'{x}' is out of order or occurs more often than allowed in {node.name}.")
            return Finding("xsd", f"{node.struct}-{known['name']}-occurrence", loc, why, C.component(node.struct, known))
        return Finding("xsd", f"{node.struct}-{x}-not-allowed", loc, f"'{x}' is not an element of {node.name}.", C.place(node))
    if unexpected and node.kind in ("list", "wrapper"):
        item = node.comp["items"]["name"] if node.kind == "list" else node.comp["name"]
        return Finding("xsd", f"{node.label()}-items", loc,
                       f"'{local(unexpected.group(1))}' is not an item of {node.name}; each item is '{item}'.", C.place(node))
    if incomplete and expected and in_struct:
        want = C.xml_component(node.struct, expected[0])
        rid, src = C.required(node, want, expected[0])
        return Finding("xsd", rid, loc, f"'{expected[0]}' is missing in {node.name}.", src)
    if attr_not_allowed:
        a = local(attr_not_allowed.group(1))
        return Finding("xsd", f"{node.label()}-{a}-not-allowed", loc, f"'{a}' is not an attribute of {node.name} in TS 119 602.",
                       C.place(node))
    if (attr_missing or attr_value) and in_struct:
        a = local((attr_missing or attr_value).group(1))
        c = next((c for c in C.S[node.struct]["components"] if is_attribute(c) and a in (c["name"], c["xml"]["form"].split()[-1])), None)
        if attr_missing:
            rid, src = C.required(node, c, a)
            return Finding("xsd", rid, loc, f"The attribute '{a}' of {node.name} is missing.", src)
        return Finding("xsd", f"{node.struct}-{c['name'] if c else a}-value", loc, f"{node.name}: {reason}",
                       C.component(node.struct, c) if c else C.place(node))
    where = node.name if steps[-1] == node.name else f"{node.name}/{steps[-1]}"   # a helper element inside the value
    return Finding("xsd", f"{node.label()}-value", loc, f"{where}: {reason}", C.place(node))


def looks_like_lote(root, C):
    """A root element that is not the LoTE root, but holds the LoTE root's components in the LoTE namespace."""
    ns = (C.S[C.root].get("xml") or {}).get("namespace")
    names = {xml_name(c) for c in C.S[C.root]["components"] if not is_attribute(c)}
    return any(isinstance(ch.tag, str) and ch.tag.startswith(f"{{{ns}}}") and local(ch.tag) in names for ch in root)


def validate_xml(path, annex, C, gen):
    """Findings for an XML list, and whether the root was corrected in memory: when the root element is not the LoTE
    root but its content is a LoTE, the wrong root is reported and the rest of the list is checked as if the root were
    right (only the root's name is changed, in memory; locations are reported against the file)."""
    import xmlschema
    from lxml import etree, isoschematron
    out = []
    xsd = xmlschema.XMLSchema(os.path.join(gen, "lote_core.xsd"))
    doc = etree.parse(path, etree.XMLParser(resolve_entities=False, no_network=True))
    root = doc.getroot()
    ns = (C.S[C.root].get("xml") or {}).get("namespace")
    lote_root = f"{{{ns}}}{C.root_xml}"
    corrected = root.tag != lote_root and looks_like_lote(root, C)
    if corrected:
        out.extend(xsd_finding(C, e) for e in xsd.iter_errors(path))      # the wrong root, as the file has it
        as_written = (f"{root.prefix}:" if root.prefix else "") + local(root.tag)
        root.tag = lote_root
        checked = [xsd_finding(C, e) for e in xsd.iter_errors(doc)]
    else:
        checked = [xsd_finding(C, e) for e in xsd.iter_errors(path)]
    schs = [("core-schematron", os.path.join(gen, "lote_core.sch"))]
    if annex:
        schs.append((f"profile-{annex}", glob.glob(os.path.join(PROFILES, f"lote_profile_{annex}_*.sch"))[0]))
    for layer, fn in schs:
        sch = isoschematron.Schematron(etree.parse(fn), store_report=True)
        sch.validate(doc)
        pattern = None
        for node in sch.validation_report.getroot():
            if node.tag == f"{{{SVRL['svrl']}}}active-pattern":
                pattern = node.get("id")
            elif node.tag == f"{{{SVRL['svrl']}}}failed-assert":
                text = " ".join(node.xpath("string(svrl:text)", namespaces=SVRL).split())
                rule_id = node.get("id") or pattern or "-"
                if layer.startswith("profile"):
                    src = C.profile(rule_id)
                    text = re.sub(r"^\[[^\]]+\]\s*", "", text).split(". " + src.get("ref", "\0"))[0]
                else:
                    src = C.core_rule(rule_id)
                loc = re.sub(r"\*\[local-name\(\)='(\w+)' and namespace-uri\(\)='([^']*)'\]",
                             lambda m: f"{PREFIX.get(m[2], 'lote')}:{m[1]}", node.get("location") or "")
                checked.append(Finding(layer, rule_id, loc, text, src))
    if corrected:
        for f in checked:
            f.location = re.sub(rf"^/(?:\w+:)?{C.root_xml}(?=/|\[|$)", f"/{as_written}", f.location)
    return out + checked, corrected


# ------------------------------------------------------------------ JSON
def months_after(value, base, months):
    """Same semantics as the Schematron check: compare year*12+month, then the rest of the date-time."""
    mon = lambda s: int(s[0:4]) * 12 + int(s[5:7])
    rest = lambda s: s[8:].replace("T", "").replace(":", "").replace("Z", "")
    return mon(value) < mon(base) + months or (mon(value) == mon(base) + months and rest(value) <= rest(base))


def get_path(doc, path):
    """Values at a model path such as LoTE.ListAndSchemeInformation (lists are flattened)."""
    nodes = [doc]
    for seg in path.split("."):
        nxt = []
        for n in nodes:
            v = n.get(seg) if isinstance(n, dict) else None
            nxt.extend(v if isinstance(v, list) else [v] if v is not None else [])
        nodes = nxt
    return nodes


def core_constraint_schemas(core):
    """id() of every subschema that expresses a core constraint (the 'then' of an if/then, an either-or 'oneOf'),
    mapped to the constraint key named in its description."""
    out = {}

    def mark(o, key):
        if isinstance(o, dict):
            out[id(o)] = key
            for v in o.values():
                mark(v, key)
        elif isinstance(o, list):
            for v in o:
                mark(v, key)
    for d in core.get("$defs", {}).values():
        k = re.match(r"(R-[\w-]+)", (d.get("if") or {}).get("description", ""))
        if k and d.get("then"):
            mark(d["then"], k.group(1))
        k = re.search(r"\b(R-[\w-]+) \(clause", d.get("description", ""))
        if k and d.get("oneOf"):
            out[id(d)] = k.group(1)
            for br in d["oneOf"]:
                mark(br, k.group(1))
    return out


def json_findings(C, e, loc):
    """A JSON Schema error as findings: the model place of its instance path gives the rule id and the citation."""
    node = C.json_resolve(list(e.absolute_path))
    missing = re.match(r"'([^']+)' is a required property", e.message) if e.validator == "required" else None
    if node.kind == "doc":
        if e.validator in ("required", "additionalProperties", "type"):
            return [C.root_finding("json-schema", loc, e.message)]
    if missing and node.kind == "struct":
        name = missing.group(1)
        rid, src = C.required(node, C.json_component(node.struct, name), name)
        return [Finding("json-schema", rid, loc, f"'{name}' is missing in {node.name}.", src)]
    if e.validator == "additionalProperties" and node.kind in ("struct", "choice"):
        out = []
        for n in re.findall(r"'([^']+)'", e.message.split("(", 1)[-1]):
            fb = next((c for (s, _), c in C.forbidden.items() if s == node.struct and n in json_names(c)), None)
            c = C.json_component(node.struct, n)
            if fb:                                        # the track forbids it here (max 0)
                rid, src = C.scheme(fb)
                out.append(Finding("json-schema", rid, loc, f"'{n}' is not allowed in {node.name} in a scheme {C.track} list.", src))
            elif c and (c.get("json") or {}).get("max") == "0":          # not part of the JSON binding (e.g. Signature)
                j = c["json"]
                src = C.fmt(f"Clause {(c.get('source') or {}).get('clause')}", j.get("citation")) if j.get("citation") \
                    else C.component(node.struct, c)
                out.append(Finding("json-schema", f"{node.struct}-{c['name']}-not-in-json", loc,
                                   f"'{n}' is not part of the JSON binding.", src))
            else:
                out.append(Finding("json-schema", f"{node.struct}-{n}-not-allowed", loc,
                                   f"'{n}' is not a property of {node.name}.", C.place(node)))
        return out
    what = "items" if node.kind == "list" and e.validator in ("minItems", "type", "contains") else "value"
    return [Finding("json-schema", f"{node.label()}-{what}", loc, f"{node.name}: {e.message[:300]}", C.place(node))]


def validate_json(path, annex, C, gen):
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    out = []
    doc = json.load(open(path, encoding="utf-8"))
    core_fn = os.path.join(gen, "lote_core.schema.json")
    core = json.load(open(core_fn, encoding="utf-8"))
    reg = Registry().with_resource("file://" + core_fn, Resource.from_contents(core))
    if annex:
        fn = glob.glob(os.path.join(PROFILES, f"lote_profile_{annex}_*.json"))[0]
        schema = {**json.load(open(fn, encoding="utf-8")), "$id": "file://" + fn}
    else:
        schema = {**core, "$id": "file://" + core_fn}
    v = Draft202012Validator(schema, registry=reg, format_checker=FormatChecker())
    constraint_of = core_constraint_schemas(core)
    for e in v.iter_errors(doc):
        loc = "/" + "/".join(str(p) for p in e.absolute_path)
        rule_id = e.schema.get("$anchor") if isinstance(e.schema, dict) else None
        if rule_id:
            out.append(Finding(f"profile-{annex}", rule_id, loc, e.schema.get("title") and
                               e.schema["description"].split(". " + C.profile(rule_id).get("ref", "\0"))[0] or e.message,
                               C.profile(rule_id)))
            continue
        key = constraint_of.get(id(e.schema))
        if key:                                           # a core constraint (if/then, either-or)
            out.append(Finding("json-schema", key, loc, e.message[:300], C.core_rule(key)))
            continue
        out.extend(json_findings(C, e, loc))
    if annex:                                            # rules JSON Schema cannot express
        for r in schema.get("x-rules-layer", []):
            ck = r.get("check") or {}
            if ck.get("type") != "months-after":
                continue
            e, _ = C.profile_rules[r["id"]]
            for node in get_path(doc, e["path"]):
                val, base = node.get(ck["component"]), node.get(ck["base"])
                if isinstance(val, str) and isinstance(base, str) and not months_after(val, base, ck["months"]):
                    out.append(Finding("rules", r["id"], "/" + e["path"].replace(".", "/") + "/" + ck["component"],
                                       f"{r['human']} ({ck['base']} {base}, {ck['component']} {val})", C.profile(r["id"])))
    return out


# ------------------------------------------------------------------ profile: which annex the list declares
def annex_types():
    """LoTEType URI -> annex letter, from the fixed LoTEType of each overlay (Tables D.1-I.1)."""
    out = {}
    for fn in sorted(glob.glob(os.path.join(OVERLAYS, "*.json"))):
        for e in json.load(open(fn, encoding="utf-8"))["differential"]["element"]:
            if e.get("path") == LOTETYPE and e.get("fixedUri"):
                out[e["fixedUri"]] = e["id"].split("-")[0]
    return out


def types_without_profile():
    """LoTEType URI -> entry, for lists checked against the explicit track only (the model's lote_types_without_profile:
    today the WP4 List of Trusted Lists)."""
    model = json.load(open(TRACKS["explicit"]["model"], encoding="utf-8"))
    return {t["uri"]: t for t in model.get("lote_types_without_profile", [])}


def declared_lote_type(path, is_xml):
    """The list's LoTEType, or None. XML is matched by local name, so a list with a wrong root or namespace still
    declares its annex; a list that cannot be read declares none (the validation reports why)."""
    try:
        if is_xml:
            from lxml import etree
            root = etree.parse(path, etree.XMLParser(resolve_entities=False, no_network=True)).getroot()
            v = root.xpath("string(*[local-name()='ListAndSchemeInformation']/*[local-name()='LoTEType'])")
        else:
            v = next(iter(get_path(json.load(open(path, encoding="utf-8")), LOTETYPE)), None)
    except Exception:
        return None
    return v.strip() if isinstance(v, str) and v.strip() else None


# ------------------------------------------------------------------ report
def text_report(r):
    lines = [f"{r.path}: {r.track} track ({r.track_reason}), "
             + (f"profile {r.profile} ({r.profile_reason})" if r.profile else f"no profile ({r.profile_reason})")
             + " - " + (f"{len(r.findings)} failure(s)" if r.findings else "valid")]
    lines += [f"WARNING: {w}" for w in r.warnings]
    if r.root_corrected:
        lines.append("The root element is not the LoTE root (see LoTE-root); the rest of the list was checked as if it "
                     "were, so the findings below cover the whole list.")
    findings = r.findings
    counts = {}
    for f in findings:
        counts.setdefault((f.layer, f.rule, f.source.get("ref")), [0, f.source])[0] += 1
    if counts:
        lines.append("\nSummary (layer, rule, failures, spec):")
        for (layer, rule, _), (n, s) in counts.items():
            lines.append(f"  {layer:16} {rule:42} {n:3}  {s.get('ref') or ''}" + (f", p. {s['page']}" if s.get("page") else ""))
    for f in findings:
        s = f.source
        lines.append(f"\nERROR: [{f.layer}] {f.rule}\n  at   {f.location}\n  why  {f.message}")
        if s.get("quote"):
            lines.append(f"  spec {s['ref']}, p. {s['page']}, line {s['line']}: \"{s['quote']}\"")
        elif s.get("ref"):
            lines.append(f"  spec {s['ref']}")
    lines.append("\nNot checked here: the signature (JAdES / XAdES), and rules-layer items no program can check.")
    return "\n".join(lines)


@dataclass
class Report:
    """The result of validating one list."""
    path: str
    track: str                                            # always "explicit"
    track_reason: str                                     # why: the flag, the profile, or the default
    profile: str = None                                   # annex letter applied, "LoTL", or None
    findings: list = field(default_factory=list)          # [Finding]
    root_corrected: bool = False                          # wrong root: the rest was checked as if the root were right
    profile_reason: str = ""                              # why: --profile, the list's LoTEType, or why none
    declared_profile: str = None                          # what the list's LoTEType names: annex letter, "LoTL", or None
    warnings: list = field(default_factory=list)          # [str], e.g. --profile differs from the declared annex

    @property
    def valid(self):
        return not self.findings

    def to_dict(self):
        return {"track": self.track, "track_reason": self.track_reason, "profile": self.profile,
                "profile_reason": self.profile_reason, "declared_profile": self.declared_profile,
                "warnings": self.warnings, "root_corrected": self.root_corrected,
                "findings": [asdict(f) for f in self.findings]}


def validate(path, profile=None, track=None):
    """Validate the list at path as a scheme explicit list against the profile its LoTEType names: an annex D-I, or "LoTL"
    (the List of Trusted Lists: explicit track only, a WP4 type). profile: an annex letter or "LoTL", overridden (with a
    warning) when the list declares another one; None; or False for the explicit track only (tests of the core rules).
    Raises ProfileError ("invalid profile", with the valid LoTEType URIs) when the LoTEType is missing or not exactly one
    of them, whatever profile is given.
    track: "explicit" or None (the same: the explicit track is the only one published, docs/project_decisions_vs_etsi.md
    #4)."""
    path = str(path)
    if track not in (None, "explicit"):
        raise ValueError(f"track {track!r} is not supported: only the explicit track is published (the implicit track is "
                         "frozen, docs/project_decisions_vs_etsi.md #4)")
    with open(path, "rb") as fh:
        is_xml = fh.read(512).lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<")
    lote_type = declared_lote_type(path, is_xml)
    lotl = {t["profile"]: t for t in types_without_profile().values()}["LoTL"]
    declared = annex_types().get(lote_type) or ("LoTL" if lote_type == lotl["uri"] else None)
    what = lambda p: f"Annex {p}" if p != "LoTL" else f"the {lotl['name']}, which no annex covers"
    flag = "--lotl" if profile == "LoTL" else f"--profile {profile}"
    warnings = []
    if profile is False:                                  # Python only (tests of the core rules): the track alone
        profile, profile_why = None, "profile=False: the explicit track only"
    elif declared:                                        # the list's own LoTEType decides; a differing flag is overridden
        if profile and profile != declared:
            warnings.append(f"{flag} ignored: the list declares LoTEType {lote_type}, {what(declared)}; checked against "
                            f"profile {declared}.")
        profile, profile_why = declared, f"from its LoTEType {lote_type}"
    else:                                                 # missing, misspelt or unknown: no profile, whatever the flags
        known = {**{u: a for u, a in annex_types().items()}, lotl["uri"]: "LoTL"}
        raise ProfileError("invalid profile: " + (f"the list's LoTEType is \"{lote_type}\"" if lote_type else
                                                  "the list has no LoTEType")
                           + ". The profiles must be:\n" + "\n".join(f"  {a:5} {u}" for u, a in
                                                                      sorted(known.items(), key=lambda x: x[1])))
    annex = profile if profile and profile != "LoTL" else None
    tr = "explicit"
    why = (f"profile {annex}: D.1-I.1 require a scheme explicit list" if annex else
           "profile LoTL: a WP4 list, explicit like the EU LoTL (project_decisions_vs_etsi.md #3)" if profile == "LoTL" else
           "--explicit" if track == "explicit" else "default: only the explicit track is published")
    C = Citations(tr)
    gen = TRACKS[tr]["gen"]
    findings, corrected = validate_xml(path, annex, C, gen) if is_xml else (validate_json(path, annex, C, gen), False)
    return Report(path, tr, why, profile, findings, corrected, profile_why, declared, warnings)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lote-validate", description=__doc__.splitlines()[0])
    ap.add_argument("list", help="the LoTE to validate (.xml or .json)")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--profile", choices=list("DEFGHI"),
                       help="the annex profile expected; the list's LoTEType decides (a differing one is used, with a "
                            "warning)")
    which.add_argument("--lotl", action="store_true",
                       help="expect a List of Trusted Lists (profile LoTL: explicit track, no annex; WP4); the list's "
                            "LoTEType decides, as for --profile")
    ap.add_argument("--explicit", action="store_true",
                    help="temporarily not in use: only the explicit track is used")
    ap.add_argument("--json", action="store_true", help="print the findings as JSON")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.list):
        ap.error(f"no such file: {a.list}")
    try:
        r = validate(a.list, "LoTL" if a.lotl else a.profile, "explicit" if a.explicit else None)
    except ProfileError as e:
        ap.error(str(e))
    if a.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(text_report(r))
    return 1 if r.findings else 0


if __name__ == "__main__":
    sys.exit(main())
