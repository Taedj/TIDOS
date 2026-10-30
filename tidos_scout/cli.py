"""tidos_scout - find, vet and propose tools for missing capabilities; install only what you approved.

  needs [--project DIR] [--trust]   capabilities the project lacks + candidate tools (trust needs network)
  list                              the catalog: installed?, status, cached trust, usage XP
  trust NAME [--refresh]            trust score 0-100 (GitHub stars/recency/license + OpenSSF Scorecard)
  search "capability words"         GitHub search for other candidates (only the words are sent)
  vet NAME                          run an installed tool's version check in an empty temp dir
  propose NAME                      mark as proposed and print the exact install command for YOU to run
  approve NAME | blacklist NAME [--note why] | reset NAME
  install NAME [--yes]              install an APPROVED tool: pinned version or SHA-256-verified download, your
                                    user account only (needs the tool_install switch; without --yes: dry run)
  uninstall NAME [--yes]            remove a tool TIDOS installed (never one you installed yourself)
  setup NAME [--project DIR] [--yes]    recipe: detect, install (approved only), configure, verify, roll back on
                                        failure (gitleaks hook, ruff.toml, pytest.ini); without --yes: dry run
  unsetup NAME [--project DIR]      undo a setup (files you changed since are kept)
"""
import argparse
import os
import sys

from tidos_brain import db

from . import scout


def _tool(name):
    tool = next((t for t in scout.catalog() if t["name"] == name), None)
    if not tool:
        print("Unknown tool %r. See: tidos_scout list" % name)
    return tool


def cmd_needs(args):
    facts, rows = scout.report(args.project, with_trust=args.trust)
    print("Project %s (%s)" % (facts["name"], ", ".join(facts["stack"])))
    if not rows:
        print("No missing capabilities for this stack.")
        return 0
    last = None
    for r in rows:
        if r["capability"] != last:
            print("\nMISSING: %s" % r["capability"])
            last = r["capability"]
        trust = "" if r["trust"] is None else "  trust %d" % r["trust"]
        print("  - %-14s %s%s%s" % (r["name"], r["why"], trust, "  [%s]" % r["status"] if r["status"] else ""))
    print("\nNothing is installed automatically. `tidos_scout approve NAME`, then `tidos_scout install NAME`.")
    return 0


def cmd_list(args):
    conn = db.connect(args.db)
    rows = scout.overview(conn, os.getcwd())
    conn.close()
    for r in rows:
        usage = r["usage"]
        print("%-15s %-9s %-11s trust %-4s %-36s %s" % (
            r["name"], "installed" if r["installed"] else "-", r["status"] or "-",
            "?" if r["trust"] is None else r["trust"], r["capability"][:36],
            "used %d (%d passed)" % (usage["runs"], usage["passed"]) if usage else ""))
    return 0


def cmd_trust(args):
    tool = _tool(args.name)
    if not tool:
        return 1
    entry = scout.trust(tool, refresh=args.refresh)
    print("%s (%s): trust %s/100" % (tool["name"], tool["repo"], entry["score"]))
    for reason in entry["reasons"]:
        print("  - " + reason)
    return 0


def cmd_search(args):
    try:
        results = scout.search(args.query)
    except Exception as e:
        print("Search failed (%s). Offline or rate-limited; set GITHUB_TOKEN for higher limits." % type(e).__name__)
        return 1
    for r in results:
        print("%3d  %-40s %s" % (r["score"], r["repo"], r["description"]))
    print("\nTrust here excludes Scorecard. Vet a candidate yourself before adding it to config/tools.json.")
    return 0


def cmd_vet(args):
    tool = _tool(args.name)
    if not tool:
        return 1
    result = scout.vet(tool)
    print("%s: %s" % (tool["name"], "PASS" if result["ok"] else "FAIL"))
    for k in ("version", "exit", "seconds", "wrote", "detail"):
        if k in result:
            print("  %-8s %s" % (k, result[k]))
    return 0 if result["ok"] else 1


def cmd_status(args, status):
    tool = _tool(args.name)
    if not tool:
        return 1
    scout.set_status(tool["name"], status, getattr(args, "note", "") or "")
    if status == "proposed":
        entry = scout.trust(tool)
        print("PROPOSAL: %s - %s\n  why:     %s\n  trust:   %s (%s)\n  install: %s\n\nRun it yourself if you "
              "agree, or approve it and let TIDOS install it (tidos_scout install)." % (tool["name"], tool["capability"], tool["why"], entry["score"],
                                                     "; ".join(entry["reasons"]), scout.install_command(tool)))
    else:
        print("%s -> %s" % (tool["name"], status if status != "none" else "reset"))
    return 0


def cmd_install(args, remove=False):
    tool = _tool(args.name)
    if not tool:
        return 1
    if not args.yes:
        auto = scout.describe_auto(tool)
        if not remove and not auto:
            print("No automatic install for %s on this machine. Run it yourself:\n  %s"
                  % (tool["name"], scout.install_command(tool)))
            return 0
        print("Would %s\nAdd --yes to do it." % ("remove %s (only if TIDOS installed it)" % tool["name"] if remove else auto))
        return 0
    try:
        result = scout.uninstall(tool["name"]) if remove else scout.install(tool["name"])
    except scout.InstallRefused as e:
        print("REFUSED: %s" % e)
        return 1
    print("%s: %s" % (tool["name"], result["detail"]))
    for line in result.get("output", []):
        print("  " + line)
    if result.get("vet"):
        print("  vet: %s %s" % ("PASS" if result["vet"]["ok"] else "FAIL", result["vet"].get("version", "")))
    return 0 if result["ok"] else 1


def cmd_setup(args, undo=False):
    from . import recipes
    try:
        if undo:
            for line in recipes.unconfigure(args.name, args.project):
                print(line)
            return 0
        if not args.yes:
            p = recipes.plan(args.name, args.project)
            print("%s in %s: %s" % (args.name, args.project, p["what"] if p["applies"] else "not needed: " + p["reason"]))
            if p["applies"]:
                print("Would %swrite %s, then verify with `%s`. Add --yes to do it." % (
                    "" if p["installed"] else "install it (approved tools only), ", ", ".join(p["files"]), p["verify"]))
            return 0
        result = recipes.apply(args.name, args.project)
    except ValueError as e:
        print("REFUSED: %s" % e)
        return 1
    for step, status, detail in result["steps"]:
        print("%-10s %-7s %s" % (step, status, detail))
    return 0 if result["ok"] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tidos_scout", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("needs")
    p.add_argument("--project", default=os.getcwd())
    p.add_argument("--trust", action="store_true")
    p.set_defaults(func=cmd_needs)
    sub.add_parser("list").set_defaults(func=cmd_list)
    p = sub.add_parser("trust")
    p.add_argument("name")
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(func=cmd_trust)
    p = sub.add_parser("search")
    p.add_argument("query")
    p.set_defaults(func=cmd_search)
    p = sub.add_parser("vet")
    p.add_argument("name")
    p.set_defaults(func=cmd_vet)
    for name, status in (("propose", "proposed"), ("approve", "approved"), ("blacklist", "blacklisted"),
                         ("reset", "none")):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("--note")
        p.set_defaults(func=lambda a, s=status: cmd_status(a, s))
    for name, remove in (("install", False), ("uninstall", True)):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("--yes", action="store_true")
        p.set_defaults(func=lambda a, r=remove: cmd_install(a, r))
    for name, undo in (("setup", False), ("unsetup", True)):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("--project", default=os.getcwd())
        p.add_argument("--yes", action="store_true")
        p.set_defaults(func=lambda a, u=undo: cmd_setup(a, u))
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
