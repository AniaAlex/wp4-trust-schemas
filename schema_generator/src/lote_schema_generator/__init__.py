"""Generate LoTE schemas (JSON Schema, XSD, Schematron) from the JSON models of ETSI TS 119 602 V1.1.1.

The models (the core model, the explicit and implicit track snapshots, the annex D-I overlays) are written by hand and
proofread against the text. The chain: the models -> the schemas (gen_json, gen_xsd, gen_profiles_from_model).
pipeline runs it in order; check compares any schema with the model; cli is `lote-schemas`.
"""

__version__ = "0.1.0"
