"""tidos_learn - TIDOS learns how tasks are solved in the user's projects.

  distill                         import new sessions, then regenerate all playbooks
  list                            show playbooks (rank, confidence, evidence)
  status                          TIDOS STATUS window: level, rank, stats, domains, daily quests, unlocked drafts
  show PATH_OR_NAME               print one playbook
  note --project P --stack S "advice"   (LEARN mode) a strong model records advice for weaker models
  summarize [--pending | --session ID]  a cheap strong model turns finished sessions into advice notes
"""
import argparse
import glob
import os
import sys

from tidos_brain import claude_code, db, opencode

from . import distill


def cmd_distill(args):
    conn = db.connect(args.db)
    if not args.no_import:
        claude_code.import_all(conn)
        opencode.import_all(conn)
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


def cmd_dataset(args):
    from . import dataset
    conn = db.connect(args.db)
    path, stats = dataset.export(conn, args.out, strong_only=not args.all,
                                 include_projects=set(args.project) if args.project else None)
    conn.close()
    print("%d record(s), %d verified -> %s" % (stats.get("records", 0), stats.get("verified", 0), path))
    return 0


def cmd_proposals(args):
    """Evolution queue: list, add, accept/reject, or draft a GitHub issue for a proposal."""
    from . import evolve
    if args.add:
        item = evolve.add(args.add, args.reason or args.add, args.priority)
        print("Added proposal #%d" % item["id"])
        return 0
    for flag, status in ((args.accept, "accepted"), (args.reject, "rejected")):
        if flag:
            evolve.set_status(flag, status)
            print("Proposal #%d %s" % (flag, status))
            return 0
    if args.issue:
        item = next((i for i in evolve.load() if i["id"] == args.issue), None)
        if not item:
            print("No proposal #%d" % args.issue)
            return 1
        path, command = evolve.issue_draft(item)
        print("Issue draft: %s\nTo publish it on GitHub (your decision), run:\n  %s" % (path, command))
        return 0
    items = evolve.ranked()
    for i in items:
        print("#%-3d %-11s %-6s %s" % (i["id"], i["status"], i["priority"], i["title"][:90]))
    if not items:
        print("No proposals yet. Add one with: tidos_learn proposals --add \"title\" --reason \"why\"")
    return 0


def cmd_status(args):
    """TIDOS STATUS - the Solo Leveling status window in the terminal."""
    from tidos_dashboard import stats
    from . import xp
    conn = db.connect(args.db)
    summary = xp.compute(conn)
    data = stats.status(conn)
    conn.close()
    bar = int(20 * (summary["xp"] - summary["floor_xp"]) / max(1, summary["next_xp"] - summary["floor_xp"]))
    lines = ["+-------------------------- [ SYSTEM ] --------------------------+",
             "  TIDOS   LEVEL %-3d  RANK %s   XP %d / %d" % (summary["level"], summary["rank"], summary["xp"],
                                                          summary["next_xp"]),
             "  [%s%s]" % ("#" * bar, "." * (20 - bar)), "", "  STATS"]
    lines += ["   %-4s %3d  %s" % (s["key"], s["value"], s["name"]) for s in data["stats"]]
    lines += ["", "  DOMAINS"]
    for name, info in sorted(summary["domains"].items(), key=lambda d: -d[1]["xp"])[:8]:
        lines.append("   [%s] %-14s LV %-3d %6d XP" % (info["rank"], name[:14], info["level"], info["xp"]))
    lines += ["", "  DAILY QUESTS"]
    lines += ["   [%s] %s (%d/%d)" % ("x" if q["done"] else ("!" if q.get("failed") else " "), q["title"],
                                     min(q["progress"], q["goal"]), q["goal"]) for q in data["quests"]]
    drafts = os.path.join(os.path.dirname(distill.playbooks_dir()), "drafts")
    n_skills = len(glob.glob(os.path.join(drafts, "skills", "*", "SKILL.md")))
    n_agents = len(glob.glob(os.path.join(drafts, "agents", "*.md")))
    if n_skills or n_agents:
        lines += ["", "  UNLOCKED (drafts to review in ~/.tidos/drafts): %d skill(s), %d specialist(s)" % (n_skills, n_agents)]
    lines.append("+----------------------------------------------------------------+")
    print("\n".join(lines))
    return 0


def cmd_summarize(args):
    from . import summarize
    conn = db.connect(args.db)
    if args.session:
        results = [(args.session,) + summarize.summarize_session(conn, args.session)]
    else:
        results = summarize.summarize_pending(conn)
    conn.close()
    for sid, lines, error in results:
        print("%s: %d note(s)%s" % (sid[:12], len(lines), " (error: %s)" % error if error else ""))
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
    sub.add_parser("status", help="TIDOS STATUS: level, rank, stats, domains, quests").set_defaults(func=cmd_status)
    p = sub.add_parser("dataset", help="export verified workflows (requests + steps + checks, no model text) as JSONL")
    p.add_argument("--out")
    p.add_argument("--all", action="store_true", help="include medium/weak-model tasks too")
    p.add_argument("--project", action="append", help="only these projects (repeatable)")
    p.set_defaults(func=cmd_dataset)
    p = sub.add_parser("proposals", help="evolution queue for improving TIDOS itself")
    p.add_argument("--add", metavar="TITLE")
    p.add_argument("--reason")
    p.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    p.add_argument("--accept", type=int, metavar="ID")
    p.add_argument("--reject", type=int, metavar="ID")
    p.add_argument("--issue", type=int, metavar="ID", help="write a GitHub issue draft + the gh command")
    p.set_defaults(func=cmd_proposals)
    p = sub.add_parser("show")
    p.add_argument("name")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser("note")
    p.add_argument("--project", required=True)
    p.add_argument("--stack", default="any")
    p.add_argument("--type", default="notes")
    p.add_argument("text")
    p.set_defaults(func=cmd_note)
    p = sub.add_parser("summarize")
    p.add_argument("--session")
    p.add_argument("--pending", action="store_true")
    p.set_defaults(func=cmd_summarize)
    args = parser.parse_args(argv)
    return args.func(args)
