"""Generate LoTE schemas (JSON Schema, XSD, Schematron) from the text of ETSI TS 119 602 V1.1.1.

The chain: the spec text and its citations (spec_text, sources) -> the core model (build_model) -> the explicit and
implicit tracks (build_schemes) -> the annex D-I profiles (build_profiles) -> the schemas (gen_json, gen_xsd,
gen_profiles_from_model). pipeline runs it in order; check compares any schema with the text; cli is `lote-schemas`.
"""

__version__ = "0.1.0"
