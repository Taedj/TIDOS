"""tidos_session - START TIDOS mode detection and briefs.

  start [--tool T] [--model M] [--project DIR] [--json]   detect tool/model/tier, pick LEARN or GUIDE mode,
                                                           save ~/.tidos/session.json, print report + brief
  status                                                   show the current session
  tier MODEL                                               show the tier a model id maps to
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from . import brief, detect, memory


def _session_path():
    return os.path.join(detect.tidos_home(), "session.json")


def refresh_learning():
    """Import new sessions and regenerate playbooks so the brief uses everything learned so far."""
    try:
        from tidos_brain import claude_code, db, opencode
        from tidos_learn import distill
        conn = db.connect()
        claude_code.import_all(conn)
        opencode.import_all(conn)
        distill.distill(conn)
        conn.close()
        return True
    except Exception:  # noqa: BLE001 - learning must never block START TIDOS
        return False


def start(tool=None, model=None, project=".", env=None, learn=False):
    project = os.path.abspath(project)
    try:
        memory.migrate()  # personal memory never stays in the repository
    except OSError:
        pass
    if learn:
        refresh_learning()
    tool = detect.detect_tool(tool, env)
    model, source = detect.detect_model(tool, model, project)
    tier, pattern = detect.tier_for(model)
    session = {"tool": tool, "model": model, "model_source": source, "tier": tier, "tier_rule": pattern,
               "mode": "learn" if tier == "frontier" else "guide", "project": project,
               "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    facts = detect.project_facts(project)
    text = brief.learn_brief(session, facts) if session["mode"] == "learn" else brief.guide_brief(session, facts)
    os.makedirs(detect.tidos_home(), exist_ok=True)
    with open(_session_path(), "w", encoding="utf-8") as f:
        json.dump(dict(session, facts=facts), f, indent=2)
    with open(os.path.join(detect.tidos_home(), "brief.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return session, facts, text


def report(session, facts):
    return ("TIDOS session\n"
            "  tool : %(tool)s\n  model: %(model)s  (%(model_source)s)\n  tier : %(tier)s  (rule %(tier_rule)s)\n"
            "  mode : %(mode)s\n" % session
            + "  project: %s  [%s]\n" % (facts["name"], ", ".join(facts["stack"])))


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    parser = argparse.ArgumentParser(prog="tidos_session")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start")
    p.add_argument("--tool", default="auto")
    p.add_argument("--model", default="auto")
    p.add_argument("--project", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-learn", action="store_true", help="skip refreshing the brain and playbooks")
    sub.add_parser("status")
    t = sub.add_parser("tier")
    t.add_argument("model")
    args = parser.parse_args(argv)

    if args.command == "start":
        session, facts, text = start(args.tool, args.model, args.project, learn=not args.no_learn)
        if args.json:
            print(json.dumps(dict(session, facts=facts, brief=text), indent=2))
        else:
            print(report(session, facts))
            print(text)
        return 0
    if args.command == "status":
        try:
            with open(_session_path(), "r", encoding="utf-8") as f:
                print(json.dumps(json.load(f), indent=2))
        except OSError:
            print("No TIDOS session yet. Run START TIDOS.")
        return 0
    tier, pattern = detect.tier_for(args.model)
    print("%s -> %s  (rule %s, mode %s)" % (args.model, tier, pattern, "learn" if tier == "frontier" else "guide"))
    return 0
