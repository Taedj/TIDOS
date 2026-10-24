"""TIDOS plugin launcher: finds the TIDOS checkout and runs its hook handler or MCP server.

Installed plugins live in Claude Code's cache, away from the TIDOS code, so this launcher locates the checkout:
  1. $TIDOS_REPO   2. ~/.tidos/repo_path (written by START TIDOS)   3. common folders
Usage: tidos_launch.py hook | mcp
A hook must never break the session: if TIDOS is not found, the hook does nothing (exit 0).
"""
import os
import subprocess
import sys


def find_repo():
    candidates = [os.environ.get("TIDOS_REPO", "")]
    try:
        with open(os.path.join(os.path.expanduser("~"), ".tidos", "repo_path"), "r", encoding="utf-8") as f:
            candidates.append(f.read().strip())
    except OSError:
        pass
    here = os.getcwd()
    candidates += [os.path.join(here, "TIDOS"), os.path.join(here, ".tidos"), os.path.join(os.path.dirname(here), "TIDOS"),
                   os.path.join(os.path.expanduser("~"), "TIDOS")]
    for path in candidates:
        if path and os.path.isfile(os.path.join(path, "tidos_brain", "__main__.py")):
            return path
    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    repo = find_repo()
    if not repo:
        if mode == "mcp":
            sys.stderr.write("TIDOS checkout not found: run START TIDOS once, or set TIDOS_REPO.\n")
            return 1
        sys.stdin.read()
        return 0
    target = {"hook": [os.path.join(repo, "tidos_brain", "__main__.py"), "hook"],
              "mcp": [os.path.join(repo, "tidos_mcp", "__main__.py")]}.get(mode)
    if not target:
        sys.stderr.write("usage: tidos_launch.py hook|mcp\n")
        return 2
    # stdin/stdout/stderr are inherited: hook payloads and MCP messages flow straight through
    return subprocess.call([sys.executable, "-I"] + target)


if __name__ == "__main__":
    sys.exit(main())
