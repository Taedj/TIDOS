"""TIDOS orb.

  run [--port N] [--show]  show the floating orb (one per user; a second run opens the panel of the first)
  launch              start the orb in the background if the `orb` switch is on (what START TIDOS does)
  open                show the orb with its panel open, even when the switch is off (/tidos-orb)
  show | quit         tell the running orb to open its panel / close
  snapshot            print what the panel shows, as JSON
"""
import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_orb import launch  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tidos_orb")
    sub = parser.add_subparsers(dest="command")
    r = sub.add_parser("run")
    r.add_argument("--port", type=int, default=launch.PORT)
    r.add_argument("--show", action="store_true", help="open the panel as soon as the orb appears")
    sub.add_parser("launch")
    sub.add_parser("open")
    sub.add_parser("show")
    sub.add_parser("quit")
    sub.add_parser("snapshot")
    args = parser.parse_args(argv)

    if args.command in (None, "run"):
        from tidos_orb import app
        return app.main(getattr(args, "port", launch.PORT), show=getattr(args, "show", False))
    if args.command in ("launch", "open"):
        state = launch.spawn(show=args.command == "open")
        print("TIDOS orb: %s" % {"off": "off (turn the `orb` switch on in the Control Center, or use /tidos-orb)",
                                 "running": "already on your desktop", "started": "started"}[state])
        return 0
    if args.command in ("show", "quit"):
        ok = launch.send(args.command.encode())
        print("sent" if ok else "no orb is running")
        return 0 if ok else 1
    from tidos_brain import db
    from tidos_orb import data
    conn = db.connect()
    try:
        print(json.dumps(data.snapshot(conn), indent=1, default=str))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
