"""The text of ETSI TS 119 602 V1.1.1 as a searchable index, for verifying quotes and computing their page and line.

    text, pos_line, page_of_line = load_spec()
    k = text.find(norm(quote))            # -1 if the quote is not in the text
    line = pos_line[k]; page = page_of_line[line - 1]

The text is whitespace-collapsed, and page headers and footers are left out, so a quote that crosses a line or page break
is still found.
"""
import os, re

from .paths import ROOT, SPEC  # noqa: F401
SPEC_ID = "ETSI TS 119 602 V1.1.1 (2025-11)"
HEADER = re.compile(r"^\s*(\d+)\s+ETSI TS 119 602 V1\.1\.1 \(2025-11\)\s*$")


def load_spec():
    lines = open(SPEC, encoding="utf-8").read().split("\n")
    page_of_line, page = [], 1
    flat, pos_line = [], []                      # whitespace-collapsed text and the source line of each char
    for i, ln in enumerate(lines, 1):
        m = HEADER.match(ln)
        if m:
            page = int(m.group(1))
        page_of_line.append(page)
        if m or SPEC_ID in ln or ln.strip() == "ETSI":
            continue                             # page headers/footers would break quotes across pages
        for w in ln.split():
            if flat:
                flat.append(" "); pos_line.append(i)
            for ch in w:
                flat.append(ch); pos_line.append(i)
    return "".join(flat), pos_line, page_of_line


def norm(s):
    return " ".join(s.split())
