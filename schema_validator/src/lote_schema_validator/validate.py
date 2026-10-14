"""lote-validate: validate a LoTE (XML or JSON) against the generated schemas and report every failure with the
sentence of ETSI TS 119 602 it breaks: rule id, location in the list, clause or annex row, page, line and quote.

    lote-validate list.xml --profile D       # explicit track + Annex D (PID providers)
    lote-validate list.json --explicit       # explicit track (Table 1, explicit column)
    lote-validate list.json --implicit       # implicit track (Table 1, implicit column)
    lote-validate list.json                  # track inferred from the content
    lote-validate list.xml --profile D --json > report.json

    from lote_schema_validator import validate
    report = validate("list.json", profile="D")          # report.valid, report.track, report.findings

Schemas: the package data in schemas/ (published by the generator: `lote-schemas publish`), or LOTE_SCHEMAS_DIR.
Tracks (clause 6.3.0, Table 1): schemas/explicit/ or schemas/implicit/. Without --explicit or --implicit the track is
inferred: a list is explicit as soon as it contains an element Table 1 forbids for implicit lists (SchemeName,
SchemeInformationURI, StatusDeterminationApproach, SchemeTypeCommunityRules, PolicyOrLegalNotice). --profile implies
--explicit: every annex requires a scheme explicit list (D.1-I.1).

Layers, in order:
  XML   the track's XSD (lote_core.xsd), its Schematron (lote_core.sch), profile Schematron (profiles/*.sch)
  JSON  the track's JSON Schema, or the profile's (profiles/*.json allOf the explicit track), then the profile rules JSON
        Schema cannot express (x-rules-layer entries with a 'check', e.g. the 6-month NextUpdate rule)
Where a citation comes from:
  profile rules     the overlay element of the rule id (schemas/model/profiles/*.json)
  core rules        the model constraint (R-...) or, for the other core Schematron patterns, the model source of their clause
  track rules       an element the track requires or forbids: Table 1 / clause 6.3.0 (schemas/model/schemes/<track>.json)
  schema errors     the model component the error is about (the track's snapshot, schemas/<track>/model/)
Signatures are not validated here (JAdES / XAdES, see the annexes' x.4).

Exit code: 0 if valid, 1 if any failure, 2 on usage errors.
"""
import argparse, glob, json, os, re, sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

SCHEMAS = os.environ.get("LOTE_SCHEMAS_DIR") or str(Path(__file__).resolve().parent / "schemas")
TRACKS = {t: {"gen": os.path.join(SCHEMAS, t, "generated"), "model": os.path.join(SCHEMAS, t, "model", f"lote_model_{t}.json"),
              "diff": os.path.join(SCHEMAS, "model", "schemes", f"{t}.json")} for t in ("explicit", "implicit")}
EXPLICIT_MARKERS = ["SchemeName", "SchemeInformationURI", "StatusDeterminationApproach", "SchemeTypeCommunityRules",
                    "PolicyOrLegalNotice"]                # "/" in Table 1's implicit column
OVERLAYS = os.path.join(SCHEMAS, "model", "profiles")
SVRL = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
CORE_SCH_CLAUSE = {"LanguageTagCase": "6.1.4", "CountryCodeExclusions": "6.1.5", "ElectronicAddressContent": "6.3.5.2"}


@dataclass
class Finding:
    layer: str
    rule: str
    location: str
    message: str
    source: dict = field(default_factory=dict)          # ref (clause or annex row), page, line, quote


# ------------------------------------------------------------------ citations
class Citations:
    def __init__(self, track):
        self.model = json.load(open(TRACKS[track]["model"], encoding="utf-8"))
        diff = json.load(open(TRACKS[track]["diff"], encoding="utf-8"))["differential"]["element"]
        self.removed = {e["path"].split(".")[-1]: e for e in diff if e.get("max") == "0"}   # components the track forbids
        self.not_bound = {c["name"]: c for st in self.model["structures"].values() for c in st["components"]
                          if (c.get("json") or {}).get("max") == "0" and c["json"].get("citation")}   # not part of JSON
        self.by_name = {}                                 # name -> [(parent structure, source, scheme rule or None)]
        for sname, s in self.model["structures"].items():
            if s.get("source"):
                for n in {sname, (s.get("xml") or {}).get("name")} - {None}:
                    self.by_name.setdefault(n, []).append((None, s["source"], None))
            for m in s.get("components", []):
                names = {m["name"], (m.get("json") or {}).get("name"), (m.get("json") or {}).get("current_name"),
                         (m.get("xml") or {}).get("name")}
                for n in names - {None}:
                    self.by_name.setdefault(n, []).append((sname, m.get("source") or {}, m.get("scheme")))
        self.rules = {c["key"]: c for s in self.model["structures"].values() for c in s.get("constraint", [])}
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
                for c in e.get("constraint", []):
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
        e, _ = self.profile_rules.get(rule_id, (None, None))
        if not e:
            return {}
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

    def forbidden(self, name):
        """Citation of the track rule that forbids component name (Table 1 '/' for the implicit track), or None."""
        e = self.removed.get(name)
        return self.fmt(e["row"], e["citation"]) if e else None

    def unbound(self, name):
        """Citation of why component name is not part of the JSON binding (e.g. Signature: 6.8.0), or None."""
        c = self.not_bound.get(name)
        return self.fmt(f"Clause {(c.get('source') or {}).get('clause')}", c["json"]["citation"]) if c else None

    def component(self, name, parent=None, ancestors=(), presence=False):
        """Citation of the model component (or structure) called name, preferring the one inside parent. For an error
        about presence, a component the track made required cites the track rule (Table 1 / 6.3.0). Helper elements the
        text does not name (Name, URI, ...) fall back to the nearest ancestor that has a citation."""
        cands = self.by_name.get(name, [])
        if not cands:
            for i, anc in enumerate(ancestors):
                found = self.component(anc, ancestors[i + 1] if i + 1 < len(ancestors) else None)
                if found:
                    return found
            return {}
        pick = next((c for c in cands if parent and c[0] == parent), None) or \
            next((c for c in cands if c[1].get("citations")), cands[0])
        if presence and pick[2]:
            return self.fmt(pick[2]["row"], pick[2]["citation"])
        src = pick[1]
        cites = src.get("citations") or [{}]
        best = next((c for c in cites if name in (c.get("quote") or "")), cites[0])   # the sentence naming it
        return self.fmt(f"Clause {src.get('clause')}" if src.get("clause") else name, best)


def component_name(e):
    return [s for s in e["path"].split(".") if s not in ("uriValue", "value")][-1]


def local(tag):
    return re.sub(r"^.*[}:]", "", tag or "")


# ------------------------------------------------------------------ XML
def validate_xml(path, annex, C, gen):
    import xmlschema
    from lxml import etree, isoschematron
    out = []
    xsd = xmlschema.XMLSchema(os.path.join(gen, "lote_core.xsd"))
    for e in xsd.iter_errors(path):
        steps = [local(s) for s in re.sub(r"\[\d+\]", "", e.path or "").split("/") if s]
        reason = e.reason or str(e.message)
        expected = re.search(r"Tag '(?:\w+:)?(\w+)' expected", reason)
        attr = re.search(r"attribute '(\w+)'", reason)
        unexpected = re.search(r"Unexpected child with tag '(?:\{[^}]*\}|\w+:)?(\w+)'", reason)
        if unexpected and C.forbidden(unexpected.group(1)):          # an element the track does not allow
            out.append(Finding("xsd", unexpected.group(1), e.path or "/", reason, C.forbidden(unexpected.group(1))))
            continue
        name = expected.group(1) if expected else attr.group(1) if attr else (steps[-1] if steps else "")
        parent = steps[-1] if (expected or attr) and steps else (steps[-2] if len(steps) > 1 else None)
        anc = list(reversed(steps if (expected or attr) else steps[:-1]))
        out.append(Finding("xsd", name or "-", e.path or "/", reason, C.component(name, parent, anc, presence=bool(expected))))
    doc = etree.parse(path)
    schs = [("core-schematron", os.path.join(gen, "lote_core.sch"))]
    if annex:
        schs.append((f"profile-{annex}", glob.glob(os.path.join(gen, "profiles", f"lote_profile_{annex}_*.sch"))[0]))
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
                loc = re.sub(r"\*\[local-name\(\)='(\w+)' and namespace-uri\(\)='[^']*'\]", r"lote:\1", node.get("location") or "")
                out.append(Finding(layer, rule_id, loc, text, src))
    return out


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


def validate_json(path, annex, C, gen):
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
    out = []
    doc = json.load(open(path, encoding="utf-8"))
    core_fn = os.path.join(gen, "lote_core.schema.json")
    core = json.load(open(core_fn, encoding="utf-8"))
    reg = Registry().with_resource("file://" + core_fn, Resource.from_contents(core))
    if annex:
        fn = glob.glob(os.path.join(gen, "profiles", f"lote_profile_{annex}_*.json"))[0]
        schema = {**json.load(open(fn, encoding="utf-8")), "$id": "file://" + fn}
    else:
        schema = {**core, "$id": "file://" + core_fn}
    v = Draft202012Validator(schema, registry=reg, format_checker=FormatChecker())
    for e in v.iter_errors(doc):
        loc = "/" + "/".join(str(p) for p in e.absolute_path)
        rule_id = e.schema.get("$anchor") if isinstance(e.schema, dict) else None
        if rule_id:
            out.append(Finding(f"profile-{annex}", rule_id, loc, e.schema.get("title") and
                               e.schema["description"].split(". " + C.profile(rule_id).get("ref", "\0"))[0] or e.message,
                               C.profile(rule_id)))
            continue
        keys = [p for p in e.absolute_path if isinstance(p, str)]
        names = re.findall(r"'(\w+)'", e.message.split("(", 1)[-1]) if e.validator == "additionalProperties" else []
        extra = [n for n in names if C.forbidden(n) or C.unbound(n)]
        if extra:                                         # elements the track or the JSON binding does not allow
            for n in extra:
                why, src = (f"'{n}' is not allowed in this track", C.forbidden(n)) if C.forbidden(n) else \
                    (f"'{n}' is not part of the JSON binding", C.unbound(n))
                out.append(Finding("json-schema", n, loc, why, src))
            continue
        missing = re.match(r"'(\w+)' is a required property", e.message)
        name = missing.group(1) if missing else (keys[-1] if keys else "LoTE")
        parent = keys[-1] if missing and keys else (keys[-2] if len(keys) > 1 else None)
        anc = [k for k in reversed(keys[:-1] if not missing else keys)]
        out.append(Finding("json-schema", name, loc, e.message[:300], C.component(name, parent, anc, presence=bool(missing))))
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


# ------------------------------------------------------------------ report
def infer_track(path, is_xml):
    """Table 1: a list is explicit as soon as it contains an element forbidden for implicit lists."""
    if is_xml:
        from lxml import etree
        names = {local(el.tag) for el in etree.parse(path).iter() if isinstance(el.tag, str)}
    else:
        lote = json.load(open(path, encoding="utf-8")).get("LoTE") or {}
        names = set(lote) | set(lote.get("ListAndSchemeInformation") or {})
    found = [n for n in EXPLICIT_MARKERS if n in names]
    return ("explicit", f"inferred: contains {found[0]}") if found else \
        ("implicit", "inferred: no element that Table 1 forbids for implicit lists")


def text_report(path, annex, findings, track="", why=""):
    lines = [f"{path}: {track} track ({why}){', profile ' + annex if annex else ''} - "
             + (f"{len(findings)} failure(s)" if findings else "valid")]
    counts = {}
    for f in findings:
        counts.setdefault((f.layer, f.rule, f.source.get("ref")), [0, f.source])[0] += 1
    if counts:
        lines.append("\nSummary (layer, rule, failures, spec):")
        for (layer, rule, _), (n, s) in counts.items():
            lines.append(f"  {layer:16} {rule:42} {n:3}  {s.get('ref') or ''}" + (f", p. {s['page']}" if s.get("page") else ""))
    for f in findings:
        s = f.source
        lines.append(f"\n[{f.layer}] {f.rule}\n  at   {f.location}\n  why  {f.message}")
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
    track: str                                            # "explicit" or "implicit"
    track_reason: str                                     # why that track: a flag, a profile, or inferred from the content
    profile: str = None                                   # annex letter, or None
    findings: list = field(default_factory=list)          # [Finding]

    @property
    def valid(self):
        return not self.findings

    def to_dict(self):
        return {"track": self.track, "track_reason": self.track_reason, "profile": self.profile,
                "findings": [asdict(f) for f in self.findings]}


def validate(path, profile=None, track=None):
    """Validate the list at path. profile: an annex letter D-I (implies the explicit track); track: "explicit",
    "implicit" or None to infer it from the content (a list is explicit once it contains an element Table 1 forbids
    for implicit lists)."""
    path = str(path)
    if profile and track == "implicit":
        raise ValueError("a profile requires a scheme explicit list (D.1-I.1); it cannot be combined with the implicit track")
    with open(path, "rb") as fh:
        is_xml = fh.read(512).lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<")
    if track == "explicit" or profile:
        tr, why = "explicit", "--explicit" if track == "explicit" else f"--profile {profile}: D.1-I.1 require a scheme explicit list"
    elif track == "implicit":
        tr, why = "implicit", "--implicit"
    else:
        tr, why = infer_track(path, is_xml)
    C = Citations(tr)
    gen = TRACKS[tr]["gen"]
    findings = validate_xml(path, profile, C, gen) if is_xml else validate_json(path, profile, C, gen)
    return Report(path, tr, why, profile, findings)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lote-validate", description=__doc__.splitlines()[0])
    ap.add_argument("list", help="the LoTE to validate (.xml or .json)")
    ap.add_argument("--profile", choices=list("DEFGHI"), help="annex profile to apply (implies --explicit)")
    track = ap.add_mutually_exclusive_group()
    track.add_argument("--explicit", action="store_true", help="validate as a scheme-explicit list (Table 1, explicit column)")
    track.add_argument("--implicit", action="store_true", help="validate as a list with implicit scheme information")
    ap.add_argument("--json", action="store_true", help="print the findings as JSON")
    a = ap.parse_args(argv)
    if not os.path.isfile(a.list):
        ap.error(f"no such file: {a.list}")
    if a.profile and a.implicit:
        ap.error("--profile requires a scheme explicit list (D.1-I.1); it cannot be combined with --implicit")
    r = validate(a.list, a.profile, "explicit" if a.explicit else "implicit" if a.implicit else None)
    if a.json:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(text_report(a.list, a.profile, r.findings, r.track, r.track_reason))
    return 1 if r.findings else 0


if __name__ == "__main__":
    sys.exit(main())
