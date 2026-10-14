"""Validate lists of trusted entities (ETSI TS 119 602, LoTE) against schemas generated from the text, and report
every failure with the sentence of the spec it breaks.

    from lote_schema_validator import validate
    report = validate("list.json", profile="D")
    report.valid, report.track, report.findings
"""
from .validate import Finding, Report, validate

__all__ = ["Finding", "Report", "validate"]
__version__ = "0.1.0"
