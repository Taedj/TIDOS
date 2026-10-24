"""tidos_brain command line.

  hook                         read a Claude Code hook event (JSON on stdin); silent, always exit 0
  import-claude [--transcript PATH]   import one transcript, or all of ~/.claude/projects
  stats                        print a summary of what the brain has learned so far
  prune [--live-days N] [--session-days N]   retention: drop old live events / sessions
  install-hooks [--settings PATH] [--dry-run] [--uninstall]   wire the hooks into Claude Code
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

from . import claude_code, db

HOOK_EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "SessionEnd")
HOOK_MARKER = "tidos_brain"


def cmd_hook(args):
    # Hooks must never disturb the session: no stdout (UserPromptSubmit stdout reaches the model), no failure.
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        conn = db.connect(args.db)
        claude_code.handle_hook(conn, payload)
        conn.close()
    except Exception as e:  # noqa: BLE001 - a broken trace must never break the user's session
        try:
            log = os.path.join(os.path.dirname(db.default_path()), "brain-hook-errors.log")
            with open(log, "a", encoding="utf-8") as f:
                f.write("%s %s: %s\n" % (datetime.now().isoformat(), type(e).__name__, e))
        except OSError:
            pass
    return 0


def cmd_import(args):
    conn = db.connect(args.db)
    if args.transcript:
        results = [claude_code.import_transcript(conn, args.transcript)]
    else:
        results = claude_code.import_all(conn, args.projects_dir or claude_code.PROJECTS_DIR)
    if not args.quiet:
        tasks = sum(len(t) for _, t in results)
        print("Imported %d session(s), %d task(s) into %s" % (len(results), tasks, args.db or db.default_path()))
    return 0


def cmd_stats(args):
    conn = db.connect(args.db)
    q = lambda sql, *p: conn.execute(sql, p).fetchall()  # noqa: E731
    sessions = q("SELECT COUNT(*) n FROM sessions")[0]["n"]
    tasks = q("SELECT COUNT(*) n, AVG(score) s, SUM(input_tokens) i, SUM(output_tokens) o FROM tasks")[0]
    print("TIDOS Brain - %s" % (args.db or db.default_path()))
    print("  sessions: %d   tasks: %d   avg score: %s   tokens in/out: %s / %s"
          % (sessions, tasks["n"], "%.2f" % tasks["s"] if tasks["s"] is not None else "-",
             tasks["i"] or 0, tasks["o"] or 0))
    print("  outcomes: " + ", ".join("%s=%d" % (r["outcome"], r["n"]) for r in
                                     q("SELECT outcome, COUNT(*) n FROM tasks GROUP BY outcome ORDER BY n DESC")))
    v = q("SELECT COUNT(*) n, SUM(verify_passed) p FROM tasks WHERE verify_passed IS NOT NULL")[0]
    print("  verified tasks: %d (last verify passed: %d)" % (v["n"], v["p"] or 0))
    print("  corrected by user: %d" % q("SELECT COUNT(*) n FROM tasks WHERE corrected = 1")[0]["n"])
    print("  models:   " + ", ".join("%s=%d" % (r["model"], r["n"]) for r in
                                     q("SELECT model, COUNT(*) n FROM tasks WHERE model IS NOT NULL"
                                       " GROUP BY model ORDER BY n DESC LIMIT 5")))
    print("  projects: " + ", ".join("%s=%d" % (r["project"], r["n"]) for r in
                                     q("SELECT s.project, COUNT(*) n FROM tasks t JOIN sessions s"
                                       " ON s.id = t.session_id GROUP BY s.project ORDER BY n DESC LIMIT 8")))
    print("  tools:    " + ", ".join("%s=%d" % (r["tool"], r["n"]) for r in
                                     q("SELECT tool, COUNT(*) n FROM tool_calls GROUP BY tool ORDER BY n DESC LIMIT 8")))
    print("  live events: %d" % q("SELECT COUNT(*) n FROM live_events")[0]["n"])
    return 0


def cmd_prune(args):
    conn = db.connect(args.db)
    now = datetime.now(timezone.utc)
    with conn:
        live = conn.execute("DELETE FROM live_events WHERE ts < ?",
                            ((now - timedelta(days=args.live_days)).isoformat(),)).rowcount
        old = 0
        if args.session_days:
            old = conn.execute("DELETE FROM sessions WHERE ended_at < ?",
                               ((now - timedelta(days=args.session_days)).isoformat(),)).rowcount
    conn.execute("VACUUM")
    print("Pruned %d live event(s), %d session(s)." % (live, old))
    return 0


def _hook_command():
    main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__main__.py")
    return '"%s" -I "%s" hook' % (sys.executable, main)


def cmd_install_hooks(args):
    path = args.settings or os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
    settings = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)  # refuse to touch a file we cannot parse
    hooks = settings.setdefault("hooks", {})

    for event in HOOK_EVENTS:
        groups = [g for g in hooks.get(event, [])
                  if not any(HOOK_MARKER in h.get("command", "") for h in g.get("hooks", []))]
        if not args.uninstall:
            group = {"hooks": [{"type": "command", "command": _hook_command(), "timeout": 10}]}
            if event == "PostToolUse":
                group = {"matcher": "*", **group}
            groups.append(group)
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks")

    text = json.dumps(settings, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    if os.path.exists(path):
        backup = "%s.tidos-backup-%s" % (path, datetime.now().strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, backup)
        print("Backup: %s" % backup)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("%s TIDOS brain hooks in %s" % ("Removed" if args.uninstall else "Installed", path))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tidos_brain")
    parser.add_argument("--db", help="brain database path (default ~/.tidos/brain.db or $TIDOS_BRAIN_DB)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hook").set_defaults(func=cmd_hook)

    p = sub.add_parser("import-claude")
    p.add_argument("--transcript")
    p.add_argument("--projects-dir")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_import)

    sub.add_parser("stats").set_defaults(func=cmd_stats)

    p = sub.add_parser("prune")
    p.add_argument("--live-days", type=int, default=14)
    p.add_argument("--session-days", type=int)
    p.set_defaults(func=cmd_prune)

    p = sub.add_parser("install-hooks")
    p.add_argument("--settings")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--uninstall", action="store_true")
    p.set_defaults(func=cmd_install_hooks)

    args = parser.parse_args(argv)
    return args.func(args)
