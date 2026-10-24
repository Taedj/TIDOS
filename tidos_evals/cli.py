"""tidos_evals - "Dungeons": measure models with and without TIDOS on verified tasks.

  list                                   show tasks
  validate [--suite S] [--task T]        each task must FAIL untouched and PASS with its reference solution
  run --agent SPEC [--tidos on|off|both] [--suite S] [--task T] [--budget USD] [--repeat N]
  report [--run RUN_ID]                  pass rates per agent, with vs without TIDOS ("lift")
  new --suite S --name N [--source DIR]  scaffold a dungeon from a real bug (every fixed bug grows the dungeon)

Results: ~/.tidos/brain.db (table evals) + ~/dungeon-runs/<run_id>/ (workdirs, logs; override with TIDOS_EVAL_DIR).
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

from tidos_brain import db

from . import agents, dungeon

# Neutral location on purpose: a run path containing "tidos" made a weak model misspell its own
# workdir ("~/.cidos/...") in TIDOS mode, contaminating the with/without comparison.
RUNS_DIR = os.environ.get("TIDOS_EVAL_DIR") or os.path.join(os.path.expanduser("~"), "dungeon-runs")


RANKS = "EDCBAS"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cmd_list(args):
    tasks = dungeon.load_tasks(args.suite, args.task)
    for t in tasks:
        flag = "" if t.tool_available() else "  (needs %s)" % t.verify[0]
        print("%-42s %s  %s%s" % (t.id, t.difficulty, t.title, flag))
    print("%d task(s)" % len(tasks))
    return 0


def cmd_validate(args):
    tasks = dungeon.load_tasks(args.suite, args.task)
    base = os.path.join(RUNS_DIR, "_validate")
    bad = 0
    for t in tasks:
        if not t.tool_available():
            print("SKIP  %-42s (%s not installed)" % (t.id, t.verify[0]))
            continue
        work = os.path.join(base, t.suite, t.name)
        t.prepare(work)
        fixture_passed, fixture_log = t.run_verify(work)
        t.prepare(work)
        t.overlay("solution", work)
        solution_passed, solution_log = t.run_verify(work)
        ok = (not fixture_passed) and solution_passed
        bad += not ok
        print("%s  %-42s fixture=%s solution=%s" % ("OK  " if ok else "BAD ", t.id,
                                                    "fail" if not fixture_passed else "PASS(!)",
                                                    "pass" if solution_passed else "FAIL(!)"))
        if not ok and args.verbose:
            print((solution_log if not solution_passed else fixture_log)[-1500:])
    shutil.rmtree(base, ignore_errors=True)
    print("%d task(s), %d invalid" % (len(tasks), bad))
    return 1 if bad else 0


def cmd_run(args):
    tasks = [t for t in dungeon.load_tasks(args.suite, args.task) if t.tool_available()
             and RANKS.index(t.difficulty) >= RANKS.index(args.min_difficulty)]
    modes = {"on": [True], "off": [False], "both": [False, True], "guide": ["guide"],
             "compare": [False, "guide"]}[args.tidos]
    # unique even for parallel runs started in the same second
    slug = "".join(c if c.isalnum() else "-" for c in args.agent)[:40].strip("-")
    run_id = "%s-%s-%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"), slug, os.urandom(2).hex())
    run_dir = os.path.join(RUNS_DIR, run_id)
    conn = db.connect(args.db)
    results = []
    total = len(tasks) * len(modes) * args.repeat
    n = 0
    print("Run %s: agent=%s tasks=%d tidos=%s repeat=%d -> %s" % (
        run_id, args.agent, len(tasks), args.tidos, args.repeat, run_dir))
    for t in tasks:
        for with_tidos in modes:
            for rep in range(args.repeat):
                n += 1
                tag = "-guide" if with_tidos == "guide" else "-tidos" if with_tidos else ""
                label = "%s%s%s" % (t.id, {"-guide": " +GUIDE", "-tidos": " +TIDOS", "": ""}[tag],
                                    " #%d" % (rep + 1) if args.repeat > 1 else "")
                work = os.path.join(run_dir, t.suite, "%s%s-%d" % (t.name, tag, rep + 1))
                t.prepare(work, with_tidos)
                print("[%d/%d] %-52s ..." % (n, total, label), end="", flush=True)
                res, seconds = agents.timed_attempt(args.agent, t, work, with_tidos, args.budget)
                passed, verify_log = t.run_verify(work)
                with open(os.path.join(work, "_tidos_eval_log.txt"), "w", encoding="utf-8") as f:
                    f.write("AGENT (%s, ok=%s, error=%s)\n%s\n\nVERIFY\n%s" % (
                        args.agent, res.ok, res.error, res.log, verify_log))
                row = {"suite": t.suite, "task_name": t.name, "model": args.agent,
                       "agent": args.agent.partition(":")[0], "with_tidos": 2 if with_tidos == "guide" else int(with_tidos),
                       "passed": int(passed), "duration_s": seconds, "cost_usd": res.cost_usd,
                       "run_at": _now(), "run_id": run_id, "difficulty": t.difficulty,
                       "turns": res.turns, "error": res.error}
                with conn:
                    conn.execute("INSERT INTO evals (%s) VALUES (%s)" % (
                        ", ".join(row), ", ".join("?" * len(row))), tuple(row.values()))
                results.append(row)
                print(" %s  %5.1fs%s%s" % ("CLEAR" if passed else "FAIL ", seconds,
                                           "  $%.3f" % res.cost_usd if res.cost_usd else "",
                                           "  (%s)" % res.error if res.error else ""))
    with open(os.path.join(run_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print()
    _print_report(conn, run_id)
    conn.close()
    return 0


def _print_report(conn, run_id=None):
    where, params = ("WHERE run_id = ?", (run_id,)) if run_id else ("WHERE 1=1", ())
    where += " AND COALESCE(error, '') NOT LIKE 'contaminated%'"
    rows = conn.execute(
        "SELECT model, with_tidos, COUNT(*) n, SUM(passed) p, SUM(COALESCE(cost_usd,0)) c, AVG(duration_s) d"
        " FROM evals %s GROUP BY model, with_tidos ORDER BY model, with_tidos" % where, params).fetchall()
    if not rows:
        print("No eval results yet.")
        return
    print("%-44s %-6s %8s %9s %8s %8s" % ("agent", "TIDOS", "cleared", "rate", "cost", "avg s"))
    by_model = {}
    for r in rows:
        rate = 100.0 * (r["p"] or 0) / r["n"]
        by_model.setdefault(r["model"], {})[r["with_tidos"]] = rate
        print("%-44s %-6s %5d/%-3d %8.0f%% %8s %8.0f" % (r["model"], {0: "off", 1: "on", 2: "guide"}[r["with_tidos"]],
                                                       r["p"] or 0, r["n"], rate,
                                                       "$%.2f" % r["c"] if r["c"] else "-", r["d"] or 0))
    for model, rates in by_model.items():
        for mode, name in ((1, "TIDOS"), (2, "GUIDE")):
            if 0 in rates and mode in rates:
                print("%s lift for %s: %+.0f points" % (name, model, rates[mode] - rates[0]))


def cmd_new(args):
    """Scaffold a dungeon from a real bug: copy the buggy project in as the fixture."""
    target = os.path.join(dungeon.DUNGEONS, args.suite, args.name)
    if os.path.exists(target):
        print("Task already exists: %s" % target)
        return 1
    if args.source:
        ignore = shutil.ignore_patterns(".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist",
                                        ".dart_tool", "*.pyc", ".env*")
        shutil.copytree(args.source, os.path.join(target, "fixture"), ignore=ignore)
    else:
        os.makedirs(os.path.join(target, "fixture"))
    os.makedirs(os.path.join(target, "hidden", "hidden_tests"))
    os.makedirs(os.path.join(target, "solution"))
    meta = {"suite": args.suite, "name": args.name, "difficulty": args.difficulty, "title": args.title or args.name,
            "prompt": "Describe the bug exactly as a user would report it (no hints about the fix).\n",
            "verify": ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider", "hidden_tests"],
            "tags": ["from-real-bug"], "timeout": 600}
    with open(os.path.join(target, "task.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    print("Created %s\nNext:\n  1. edit task.json (prompt, verify command, difficulty)\n"
          "  2. put the regression test(s) in hidden/hidden_tests/ (the agent never sees them)\n"
          "  3. put the fixed files in solution/ (same relative paths as the fixture)\n"
          "  4. python -I tidos_evals/__main__.py validate --task %s" % (target, args.name))
    return 0


def cmd_report(args):
    conn = db.connect(args.db)
    _print_report(conn, args.run)
    conn.close()
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # cp1252 consoles cannot print test-runner symbols
        try:
            stream.reconfigure(errors="replace")
        except AttributeError:
            pass
    parser = argparse.ArgumentParser(prog="tidos_evals")
    parser.add_argument("--db", help="brain database (default ~/.tidos/brain.db)")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("list", cmd_list), ("validate", cmd_validate), ("run", cmd_run), ("report", cmd_report)):
        p = sub.add_parser(name)
        p.set_defaults(func=func)
        if name != "report":
            p.add_argument("--suite")
            p.add_argument("--task")
    sub.choices["validate"].add_argument("-v", "--verbose", action="store_true")
    run = sub.choices["run"]
    run.add_argument("--agent", required=True, help="reference | noop | claude:<model> | opencode:<provider/model>")
    run.add_argument("--tidos", choices=["on", "off", "both", "guide", "compare"], default="both",
                     help="off=plain, on=v4 protocol text, guide=v4.1 GUIDE brief + per-request guidance, compare=off+guide")
    run.add_argument("--budget", type=float, default=1.0, help="max USD per Claude attempt")
    run.add_argument("--repeat", type=int, default=1)
    run.add_argument("--min-difficulty", default="E", choices=list("EDCBAS"), help="only tasks of this rank or harder")
    sub.choices["report"].add_argument("--run", help="only this run id")
    new = sub.add_parser("new", help="scaffold a dungeon from a real bug")
    new.add_argument("--suite", required=True)
    new.add_argument("--name", required=True)
    new.add_argument("--source", help="folder with the buggy project to use as fixture")
    new.add_argument("--title")
    new.add_argument("--difficulty", default="C", choices=list("EDCBAS"))
    new.set_defaults(func=cmd_new)
    args = parser.parse_args(argv)
    return args.func(args)
