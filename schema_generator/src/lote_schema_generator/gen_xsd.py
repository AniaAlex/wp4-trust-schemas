"""Generate the core LoTE XML binding from the abstract model base/model/lote_model.json.

Writes base/generated/ (or a track's generated folder): lote_core.xsd (core), lote_tie.xsd and lote_sie.xsd (extension namespaces, each importing
the core), and lote_core.sch (ISO Schematron for the rules XSD 1.0 cannot express).

The model says WHAT the text requires; this script holds HOW the XML binding expresses it:
  - target namespace http://uri.etsi.org/019602/v1# (prefix lote), elementFormDefault qualified;
  - every structure is a named complexType '<Name>Type' (the root uses its 'xml.name'); components are local elements in
    the order of the text, or in the structure's 'xml.order' where the Forge binding orders them differently; min/max -> minOccurs/maxOccurs; 'xml.form: attribute' -> attribute;
  - 'items' -> a wrapper element containing the repeated item element; 'xml.wrapper' -> the same for a repeated structure;
  - content 'choice' -> xsd:choice; 'any-of' -> repeated 'xml.item_wrapper' element (DigitalId) holding one identifier;
  - multilingual values -> 'Name' / 'URI' elements with a required xml:lang attribute;
  - extension lists -> 'Extension' elements with open content and a 'Critical' attribute (required where the component
    says criticality 'required'); known extensions are global elements in their own namespace;
  - XSD 1.0 cannot express co-occurrence, "one entry must be English", lower-case language tags, value exclusions or
    "contains a mailto: URI": those are Schematron rules. Business rules are listed in a comment.
"""
import json, os
from xml.sax.saxutils import escape

from .model import CODE_ONLY, allowed
from .paths import BASE_GEN, MODEL, ROOT, SNAPSHOT, TRACK_GEN

OUT = BASE_GEN
# --scheme: the base (both kinds of list) or one track, read from its snapshot (explicit|implicit/model/)
SCHEMES = {"base": (MODEL, OUT),
           "explicit": (SNAPSHOT["explicit"], TRACK_GEN["explicit"]),
           "implicit": (SNAPSHOT["implicit"], TRACK_GEN["implicit"])}
NS = "http://uri.etsi.org/019602/v1#"
XMLNS_XSD = "http://www.w3.org/2001/XMLSchema"
DS = "http://www.w3.org/2000/09/xmldsig#"
XML_XSD = "http://www.w3.org/2001/xml.xsd"
DS_XSD = "http://www.w3.org/TR/2008/REC-xmldsig-core-20080610/xmldsig-core-schema.xsd"

# Value type -> XSD type (lote: types are defined in SIMPLE_TYPES / COMPLEX_TYPES below).
VALUE_TYPE = {
    "integer": "xsd:integer", "positive-integer": "xsd:positiveInteger", "non-negative-integer": "xsd:nonNegativeInteger",
    "uri": "lote:NonEmptyURIType", "uri-list": "lote:URIListType", "utc-datetime": "lote:UTCDateTimeType",
    "plain-text": "lote:PlainTextType", "multilang-text": "lote:MultiLangStringType", "multilang-uri": "lote:MultiLangURIType",
    "multilang-texts": "lote:MultiLangStringListType", "multilang-uris": "lote:MultiLangURIListType",
    "scheme-name": "lote:SchemeNameListType", "electronic-address": "lote:ElectronicAddressType",
    "country-code": "lote:CountryCodeType", "country-code-a": "lote:CountryCodeAType", "mime-type": "lote:MimeTypeType",
    "base64": "xsd:base64Binary", "string": "lote:NonEmptyStringType", "typed-uri": "lote:TypedURIType", "open": "lote:AnyType",
    "xml-id": "xsd:ID",
}
PLAIN_TEXT_PATTERN = ("[^\\t\\n\\r&#x7F;-&#x9F;&#xE000;-&#xF8FF;&#xFEFF;&#xE0000;-&#xE007F;&#xF0000;-&#x10FFFF;]+")


def doc(text, indent):
    return f'{indent}<xsd:annotation><xsd:documentation>{escape(text)}</xsd:documentation></xsd:annotation>\n' if text else ""


def cite(m):
    s = m.get("source")
    if s:
        c = s["citations"][0]
        return f"Clause {s['clause']}, p. {c['page']}: \"{c['quote']}\""
    c = m.get("citation")
    return f"p. {c['page']}: \"{c['quote']}\"" if c else ""


def occurs(mn, mx):
    out = "" if mn == 1 else f' minOccurs="{mn}"'
    out += "" if mx == 1 else f' maxOccurs="{"unbounded" if mx == "n" else mx}"'
    return out


def simple_and_complex_types(model):
    codes = "".join(f'      <xsd:enumeration value="{c}"/>\n' for c in model["value_types"]["country-code-a"]["codes"])
    vt = model["value_types"]
    d = lambda t: doc(vt[t]["description"], "    ")
    return f'''  <!-- ============================================================ value types -->
  <xsd:simpleType name="NonEmptyURIType">
{d("uri")}    <xsd:restriction base="xsd:anyURI"><xsd:minLength value="1"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="UTCDateTimeType">
{d("utc-datetime")}    <xsd:restriction base="xsd:dateTime"><xsd:pattern value="\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}Z"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="PlainTextType">
{doc(vt["plain-text"]["description"] + " U+FEFF is excluded everywhere (XSD regex has no look-ahead to exclude it only at the start).", "    ")}    <xsd:restriction base="xsd:string"><xsd:pattern value="{PLAIN_TEXT_PATTERN}"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="SchemeNameTextType">
{d("scheme-name")}    <xsd:restriction base="lote:PlainTextType"><xsd:pattern value="[A-Z]{{2,}}:.+"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="NonEmptyStringType">
{d("string")}    <xsd:restriction base="xsd:string"><xsd:minLength value="1"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="CountryCodeType">
{doc(vt["country-code"]["description"] + " GB and GR are excluded by Schematron.", "    ")}    <xsd:restriction base="xsd:string"><xsd:pattern value="[A-Z]{{2,}}"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="CountryCodeAType">
{d("country-code-a")}    <xsd:restriction base="xsd:string">
{codes}    </xsd:restriction>
  </xsd:simpleType>
  <xsd:simpleType name="MimeTypeType">
{d("mime-type")}    <xsd:restriction base="xsd:string"><xsd:pattern value="[a-zA-Z0-9!#$&amp;^_.+\\-]+/[a-zA-Z0-9!#$&amp;^_.+\\-]+(\\s*;.*)?"/></xsd:restriction>
  </xsd:simpleType>
  <xsd:complexType name="MultiLangStringType">
{d("multilang-text")}    <xsd:simpleContent><xsd:extension base="lote:PlainTextType"><xsd:attribute ref="xml:lang" use="required"/></xsd:extension></xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="SchemeNameStringType">
    <xsd:simpleContent><xsd:extension base="lote:SchemeNameTextType"><xsd:attribute ref="xml:lang" use="required"/></xsd:extension></xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="MultiLangURIType">
{d("multilang-uri")}    <xsd:simpleContent><xsd:extension base="lote:NonEmptyURIType"><xsd:attribute ref="xml:lang" use="required"/></xsd:extension></xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="MultiLangStringListType">
{d("multilang-texts")}    <xsd:sequence><xsd:element name="Name" type="lote:MultiLangStringType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="SchemeNameListType">
{d("scheme-name")}    <xsd:sequence><xsd:element name="Name" type="lote:SchemeNameStringType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="MultiLangURIListType">
{d("multilang-uris")}    <xsd:sequence><xsd:element name="URI" type="lote:MultiLangURIType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="ElectronicAddressType">
{doc(vt["electronic-address"]["description"] + " The mailto: and web-site entries are checked by Schematron.", "    ")}    <xsd:sequence><xsd:element name="URI" type="lote:MultiLangURIType" minOccurs="2" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="URIListType">
{d("uri-list")}    <xsd:sequence><xsd:element name="URI" type="lote:NonEmptyURIType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="TypedURIType">
{d("typed-uri")}    <xsd:simpleContent><xsd:extension base="lote:NonEmptyURIType"><xsd:attribute name="type" type="lote:NonEmptyURIType"/></xsd:extension></xsd:simpleContent>
  </xsd:complexType>
  <xsd:complexType name="AnyType" mixed="true">
{d("open")}    <xsd:sequence minOccurs="0" maxOccurs="unbounded"><xsd:any processContents="lax"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="ExtensionType">
{doc("Extension whose format is left open, with a mandatory criticality indication (clause 6.3.17).", "    ")}    <xsd:complexContent><xsd:extension base="lote:AnyType"><xsd:attribute name="Critical" type="xsd:boolean" use="required"/></xsd:extension></xsd:complexContent>
  </xsd:complexType>
  <xsd:complexType name="ExtensionsListType">
{d("extension-list")}    <xsd:sequence><xsd:element name="Extension" type="lote:ExtensionType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="OptionalCriticalityExtensionType">
{doc("Extension whose format is left open; the text does not require a criticality indication here.", "    ")}    <xsd:complexContent><xsd:extension base="lote:AnyType"><xsd:attribute name="Critical" type="xsd:boolean"/></xsd:extension></xsd:complexContent>
  </xsd:complexType>
  <xsd:complexType name="OptionalCriticalityExtensionsListType">
{d("extension-list")}    <xsd:sequence><xsd:element name="Extension" type="lote:OptionalCriticalityExtensionType" maxOccurs="unbounded"/></xsd:sequence>
  </xsd:complexType>
'''


class Gen:
    def __init__(self, model, source="base/model/lote_model.json"):
        self.m, self.source = model, source

    def type_name(self, sname):
        x = self.m["structures"][sname].get("xml") or {}
        return (x.get("name") or sname) + "Type"

    def value_type(self, m):
        if (m.get("xml") or {}).get("type") == "base64":
            return "xsd:base64Binary"
        if m.get("value") == "extension-list":
            return "lote:ExtensionsListType" if m.get("criticality") == "required" else "lote:OptionalCriticalityExtensionsListType"
        return VALUE_TYPE[m["value"]]

    def element(self, m, ind, mn=None, mx=None):
        x = m.get("xml") or {}
        mn = m["min"] if mn is None else mn
        mx = m["max"] if mx is None else mx
        note = cite(m)
        if x.get("name", "").startswith("ds:"):
            return f'{ind}<xsd:element ref="{x["name"]}"{occurs(mn, mx)}/>  <!-- {escape(note)} -->\n'
        name = x.get("name", m["name"])
        if m.get("items"):
            it = m["items"]
            itype = f'lote:{self.type_name(it["structure"])}' if it.get("structure") else VALUE_TYPE[it["value"]]
            return (f'{ind}<xsd:element name="{name}"{occurs(mn, mx)}>\n{doc(note, ind + "  ")}'
                    f'{ind}  <xsd:complexType><xsd:sequence>\n'
                    f'{ind}    <xsd:element name="{it["name"]}" type="{itype}"{occurs(max(1, it["min"]), "n")}/>\n'
                    f'{ind}  </xsd:sequence></xsd:complexType>\n{ind}</xsd:element>\n')
        if x.get("wrapper"):                                          # repeated structure inside a wrapper element
            inner = f'<xsd:element name="{m["name"]}" type="lote:{self.type_name(m["structure"])}"{occurs(1, "n")}/>'
            return (f'{ind}<xsd:element name="{x["wrapper"]}"{occurs(1 if mn >= 1 else 0, 1)}>\n{doc(note, ind + "  ")}'
                    f'{ind}  <xsd:complexType><xsd:sequence>{inner}</xsd:sequence></xsd:complexType>\n{ind}</xsd:element>\n')
        if m["name"] == "NextUpdate":
            return (f'{ind}<xsd:element name="NextUpdate"{occurs(mn, mx)}>\n{doc(note + " An empty NextUpdate (no dateTime child) is a closed LoTE.", ind + "  ")}'
                    f'{ind}  <xsd:complexType><xsd:sequence><xsd:element name="dateTime" type="lote:UTCDateTimeType" minOccurs="0"/>'
                    f'</xsd:sequence></xsd:complexType>\n{ind}</xsd:element>\n')
        typ = f'lote:{self.type_name(m["structure"])}' if m.get("structure") else self.value_type(m)
        d = doc(note, ind + "  ")
        if d:
            return f'{ind}<xsd:element name="{name}" type="{typ}"{occurs(mn, mx)}>\n{d}{ind}</xsd:element>\n'
        return f'{ind}<xsd:element name="{name}" type="{typ}"{occurs(mn, mx)}/>\n'

    def complex_type(self, sname, s):
        tname = self.type_name(sname)
        out = f'  <xsd:complexType name="{tname}">\n' + doc(" ".join(x for x in [cite(s), s.get("note")] if x), "    ")
        attrs = [m for m in s["components"] if (m.get("xml") or {}).get("form", "").startswith("attribute")]
        elems = [m for m in s["components"] if m not in attrs]
        order = (s.get("xml") or {}).get("order")             # the binding's element order, where it differs from the text
        if order:
            elems.sort(key=lambda m: order.index(m["name"]))
        if s["content"] == "choice":
            out += "    <xsd:choice>\n" + "".join(self.element(m, "      ") for m in elems) + "    </xsd:choice>\n"
        elif s["content"] == "any-of":
            w = (s.get("xml") or {}).get("item_wrapper", "Identifier")
            out += (f'    <xsd:sequence>\n      <xsd:element name="{w}" maxOccurs="unbounded">\n'
                    f'        <xsd:complexType><xsd:choice>\n'
                    + "".join(self.element(m, "          ", 1, 1) for m in elems)
                    + "        </xsd:choice></xsd:complexType>\n      </xsd:element>\n    </xsd:sequence>\n")
        else:
            out += "    <xsd:sequence>\n" + "".join(self.element(m, "      ") for m in elems) + "    </xsd:sequence>\n"
        for m in attrs:
            use = "required" if m["min"] >= 1 else "optional"
            if m["xml"]["form"] == "attribute xml:lang":
                out += f'    <xsd:attribute ref="xml:lang" use="{use}"/>\n'
            else:
                out += f'    <xsd:attribute name="{m["name"]}" type="{VALUE_TYPE[m["value"]]}" use="{use}"/>\n'
        return out + "  </xsd:complexType>\n"

    def constraints(self, check_type=None):
        """(structure, constraint) pairs of the model, in structure order; only those with the given check type if one is given."""
        return [(n, c) for n, st in self.m["structures"].items() for c in st.get("constraint", [])
                if check_type is None or (c.get("check") or {}).get("type") == check_type]

    def core(self):
        root = self.m["root"]
        rx = self.m["structures"][root].get("xml") or {}
        business = "\n".join(f"  - {c['clause']} {c['human']}" + (" (checked by the validator's code)" if c.get("check") else "")
                             for _, c in self.constraints() if not c.get("check") or c["check"]["type"] in CODE_ONLY)
        ext_imports = "".join(f'  <xsd:import namespace="{e["xml"]["namespace"]}" schemaLocation="{f}"/>\n'
                              for f, e in (("lote_tie.xsd", self.m["extensions"]["OtherAssociatedBodies"]),
                                           ("lote_sie.xsd", self.m["extensions"]["ServiceUniqueIdentifier"])))
        out = f'''<?xml version="1.0" encoding="UTF-8"?>
<!--
  ETSI TS 119 602 V1.1.1 - List of Trusted Entities (LoTE), XML binding (generated).
  Generated by lote_schema_generator/gen_xsd.py from {self.source}. Do not edit; change the model or the generator.
  Rules XSD 1.0 cannot express are in lote_core.sch (ISO Schematron).
  Business rules, to be enforced by a rules layer:
{escape(business)}
-->
<xsd:schema xmlns:xsd="{XMLNS_XSD}" xmlns:lote="{NS}" xmlns:ds="{DS}"
            targetNamespace="{NS}" elementFormDefault="qualified" attributeFormDefault="unqualified">
  <xsd:import namespace="http://www.w3.org/XML/1998/namespace" schemaLocation="{XML_XSD}"/>
  <xsd:import namespace="{DS}" schemaLocation="{DS_XSD}"/>
{ext_imports}
  <xsd:element name="{rx.get("name", root)}" type="lote:{self.type_name(root)}"/>

  <!-- ============================================================ structures -->
'''
        for sname, s in self.m["structures"].items():
            out += self.complex_type(sname, s)
        return out + simple_and_complex_types(self.m) + "</xsd:schema>\n"

    def extension(self, name):
        e = self.m["extensions"][name]
        ns = e["xml"]["namespace"]
        if e.get("items"):
            it = e["items"]
            body = (f'    <xsd:complexType><xsd:sequence><xsd:element name="{it["name"]}" type="lote:{self.type_name(it["structure"])}"'
                    f'{occurs(max(1, it["min"]), "n")}/></xsd:sequence></xsd:complexType>\n')
            el = f'  <xsd:element name="{name}">\n{doc(cite(e), "    ")}{body}  </xsd:element>\n'
        else:
            el = f'  <xsd:element name="{name}" type="{VALUE_TYPE[e["value"]]}">\n{doc(cite(e), "    ")}  </xsd:element>\n'
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- ETSI TS 119 602 V1.1.1 - extension {name} (generated by lote_schema_generator/gen_xsd.py). Do not edit. -->
<xsd:schema xmlns:xsd="{XMLNS_XSD}" xmlns:lote="{NS}" targetNamespace="{ns}"
            elementFormDefault="qualified" attributeFormDefault="unqualified">
  <xsd:import namespace="{NS}" schemaLocation="lote_core.xsd"/>
{el}</xsd:schema>
'''

    def schematron(self):
        root = (self.m["structures"][self.m["root"]].get("xml") or {}).get("name", self.m["root"])
        upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        lower = upper.lower()
        primary = "substring-before(concat(@xml:lang, '-'), '-')"
        ea = " | ".join(f"lote:{n}" for n in ("ElectronicAddress", "TEElectronicAddress", "AssociatedBodyElectronicAddress"))
        # the XML name of a has-entry field: 'lang' is the xml:lang attribute (the PostalAddress override says so)
        xml_attr = {c["name"]: "@" + c["xml"]["form"].split()[-1] for st in self.m["structures"].values()
                    for c in st["components"] if (c.get("xml") or {}).get("form", "").startswith("attribute ")}

        def q(c):
            cite = ((c.get("source") or {}).get("citations") or [c.get("citation")])[0]
            return escape(f"{c['key']} (clause {c['clause']}, p. {cite['page']}): {c['human']}")

        def pattern(key, context, test, msg):
            return (f'  <sch:pattern id="{key}">\n    <sch:rule context="{context}">\n'
                    f'      <sch:assert test="{test}">{msg}</sch:assert>\n    </sch:rule>\n  </sch:pattern>\n')

        # the constraints' checks, translated by type (constraints without a check are rules-layer: see the XSD comment)
        patterns = ""
        for sname, c in self.constraints("co-occurrence"):
            ck = c["check"]
            trig = " or ".join(f"lote:{x}" for x in ck["if_any_present"])
            need = " and ".join(f"lote:{x}" for x in ck["then_required"])
            patterns += pattern(c["key"], f"lote:{sname}", f"not({trig}) or ({need})", q(c))
        for sname, c in self.constraints("required-if"):
            ck = c["check"]
            cond = "/".join("lote:" + p for p in ck["if"]["path"].split(".")[1:])
            patterns += pattern(c["key"], f"lote:{sname}",
                                f"not(/lote:{root}/{cond} &gt;= {ck['if']['min']}) or lote:{ck['component']}", q(c))
        for sname, c in self.constraints("either-or"):
            ck = c["check"]
            xname = (self.m["structures"][sname].get("xml") or {}).get("name", sname)
            has = lambda names: " and ".join(f"lote:{x}" for x in names)
            none = lambda names: "not(" + " or ".join(f"lote:{x}" for x in names) + ")"
            patterns += pattern(c["key"], f"lote:{xname}",
                                f"({has(ck['first'])} and {none(ck['second'])}) or ({has(ck['second'])} and {none(ck['first'])})", q(c))
        for sname, c in self.constraints("has-entry"):
            ck = c["check"]
            attr = xml_attr[ck["field"]]
            patterns += pattern(c["key"], f"*[*[{attr}]]", f"*[{attr} = '{ck['match']['equals']}']", q(c))
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- ETSI TS 119 602 V1.1.1 - rules of the LoTE XML binding that XSD 1.0 cannot express (generated by gen_xsd.py). -->
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron" queryBinding="xslt">
  <sch:ns prefix="lote" uri="{NS}"/>
{patterns}  <sch:pattern id="LanguageTagCase">
    <sch:rule context="*[@xml:lang]">
      <sch:assert test="string-length({primary}) &gt;= 2 and string-length({primary}) &lt;= 3 and translate({primary}, '{lower}', '') = ''">Clause 6.1.4: the language tag "<sch:value-of select="@xml:lang"/>" must start with a 2-3 letter lower-case language code.</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern id="CountryCodeExclusions">
    <sch:rule context="lote:SchemeTerritory">
      <sch:assert test="not(. = 'GB' or . = 'GR')">Clause 6.1.5 a): the United Kingdom is "UK" and Greece is "EL".</sch:assert>
    </sch:rule>
  </sch:pattern>
  <sch:pattern id="ElectronicAddressContent">
    <sch:rule context="{ea}">
      <sch:assert test="lote:URI[starts-with(., 'mailto:')] and lote:URI[starts-with(., 'http://') or starts-with(., 'https://')]">Clause 6.3.5.2: an electronic address contains a mailto: URI and a web-site URI.</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
'''


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scheme", choices=list(SCHEMES), default="base",
                    help="base: both kinds of list (Table 1 in Schematron); explicit / implicit: one track (Table 1 column as structure)")
    model_path, out = SCHEMES[ap.parse_args().scheme]
    model = allowed(json.load(open(model_path, encoding="utf-8")))
    g = Gen(model, os.path.relpath(model_path, ROOT))
    os.makedirs(out, exist_ok=True)
    files = {"lote_core.xsd": g.core(), "lote_tie.xsd": g.extension("OtherAssociatedBodies"),
             "lote_sie.xsd": g.extension("ServiceUniqueIdentifier"), "lote_core.sch": g.schematron()}
    for name, text in files.items():
        with open(out + name, "w", encoding="utf-8") as f:
            f.write(text)
    print("wrote " + ", ".join(os.path.relpath(out + n, ROOT) for n in files))


if __name__ == "__main__":
    main()
