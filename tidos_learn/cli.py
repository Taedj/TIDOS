"""tidos_learn - TIDOS learns how tasks are solved in the user's projects.

  distill                         import new sessions, then regenerate all playbooks
  list                            show playbooks (rank, confidence, evidence)
  show PATH_OR_NAME               print one playbook
  note --project P --stack S "advice"   (LEARN mode) a strong model records advice for weaker models
"""
import argparse
import glob
import os
import sys

from tidos_brain import claude_code, db

from . import distill


def cmd_distill(args):
    conn = db.connect(args.db)
    if not args.no_import:
        claude_code.import_all(conn)
    written = distill.distill(conn)
    conn.close()
    if not args.quiet:
        for path, ttype, stack, project, conf, n in sorted(written, key=lambda w: (w[3], w[1])):
            print("%-10s %-10s %-34s conf %.2f  %3d tasks" % (project, ttype, stack[:34], conf, n))
        print("%d playbook(s) in %s" % (len(written), distill.playbooks_dir()))
    return 0


def cmd_list(args):
    conn = db.connect(args.db)
    rows = conn.execute("SELECT * FROM playbooks ORDER BY task_type").fetchall()
    for r in rows:
        print("[%s] %-9s %-30s %3d tasks, %3d verified  %s" % (r["rank"], r["task_type"], r["stack"][:30], r["uses"],
                                                               r["successes"], os.path.relpath(r["path"], distill.playbooks_dir())))
    for notes in glob.glob(os.path.join(distill.playbooks_dir(), "*", "notes.md")):
        print("[notes]  %s" % os.path.relpath(notes, distill.playbooks_dir()))
    conn.close()
    return 0


def cmd_show(args):
    candidates = [args.name] + glob.glob(os.path.join(distill.playbooks_dir(), "**", "*%s*" % args.name), recursive=True)
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                print(f.read())
            return 0
    print("No playbook matching %r" % args.name)
    return 1


def cmd_note(args):
    path = distill.add_note(args.project, args.stack, args.text, args.type)
    print("Noted in %s" % path)
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    parser = argparse.ArgumentParser(prog="tidos_learn")
    parser.add_argument("--db")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("distill")
    p.add_argument("--no-import", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_distill)
    sub.add_parser("list").set_defaults(func=cmd_list)
    p = sub.add_parser("show")
    p.add_argument("name")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("note")
    p.add_argument("--project", required=True)
    p.add_argument("--stack", default="any")
    p.add_argument("--type", default="notes")
    p.add_argument("text")
    p.set_defaults(func=cmd_note)
    args = parser.parse_args(argv)
    return args.func(args)
