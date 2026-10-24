"""Start the control center: python -I tidos_dashboard/__main__.py [--port 8767] [--no-browser]"""
import argparse
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_dashboard.server import serve  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tidoszit")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--db", help="brain database (default ~/.tidos/brain.db)")
    args = parser.parse_args(argv)
    try:
        serve(port=args.port, open_browser=not args.no_browser, db_path=args.db)
    except OSError as e:
        print("[TIDOSZIT] Cannot start on port %d: %s (already running? try http://localhost:%d/)"
              % (args.port, e, args.port), file=sys.stderr)
        return 2
    return 0


sys.exit(main())
