"""lote-schemas: build, check and publish the LoTE schemas generated from ETSI TS 119 602.

    lote-schemas build                  generate the schemas from the models (core, tracks, profiles)
    lote-schemas build --publish        ... and copy the results into the validator package
    lote-schemas publish [--to DIR]     copy the current results into the validator package (or DIR)
    lote-schemas check SCHEMA ...       check a schema against the model (see lote_schema_generator.check)
"""
import argparse
import sys

from . import check, pipeline
from .paths import VALIDATOR_SCHEMAS


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["check"]:                         # the checker has its own options
        return check.main(argv[1:])
    ap = argparse.ArgumentParser(prog="lote-schemas", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="run the whole generation chain")
    b.add_argument("--publish", action="store_true", help="then copy the results into the validator package")
    b.add_argument("--quiet", action="store_true")
    p = sub.add_parser("publish", help="copy the generated schemas into the validator package")
    p.add_argument("--to", default=VALIDATOR_SCHEMAS, help="target directory (default: %(default)s)")
    sub.add_parser("check", help="check a schema against the model (options: lote-schemas check --help)")
    a = ap.parse_args(argv)
    if a.command == "build":
        rc = pipeline.build(quiet=a.quiet)
        return rc or (pipeline.publish(quiet=a.quiet) if a.publish else 0)
    return pipeline.publish(a.to)


if __name__ == "__main__":
    sys.exit(main())
