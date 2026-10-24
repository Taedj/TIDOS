"""Build plugin/ (the TIDOS Claude Code plugin) from the repository sources.

  python scripts/build_plugin.py          write plugin/ files
  python scripts/build_plugin.py --check  exit 1 if plugin/ is out of date (CI)

Sources of truth: .claude/agents/*.md, .claude/skills/*/SKILL.md, .claude/commands/{tidos,TIDOSZIT}.md, VERSION.md.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugin")
LAUNCH = 'python -I "${CLAUDE_PLUGIN_ROOT}/bin/tidos_launch.py"'
COMMANDS = ["tidos.md", "TIDOSZIT.md"]


def version():
    with open(os.path.join(ROOT, "VERSION.md"), encoding="utf-8") as f:
        return re.search(r"\*\*Current Version\*\*:\s*(\S+)", f.read()).group(1)


def expected_files():
    files = {}
    for path in sorted(glob.glob(os.path.join(ROOT, ".claude", "agents", "tidos-*.md"))):
        with open(path, encoding="utf-8") as f:
            files["agents/" + os.path.basename(path)] = f.read()
    for path in sorted(glob.glob(os.path.join(ROOT, ".claude", "skills", "*", "SKILL.md"))):
        with open(path, encoding="utf-8") as f:
            files["skills/%s/SKILL.md" % os.path.basename(os.path.dirname(path))] = f.read()
    for name in COMMANDS:
        with open(os.path.join(ROOT, ".claude", "commands", name), encoding="utf-8") as f:
            files["commands/" + name] = f.read()
    hook = {"type": "command", "command": LAUNCH + " hook", "timeout": 10}
    files["hooks/hooks.json"] = json.dumps({"hooks": {
        "SessionStart": [{"hooks": [hook]}],
        "UserPromptSubmit": [{"hooks": [hook]}],
        "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [hook]}],
        "PostToolUse": [{"matcher": "*", "hooks": [hook]}],
        "Stop": [{"hooks": [hook]}],
        "SessionEnd": [{"hooks": [hook]}],
    }}, indent=2) + "\n"
    files[".mcp.json"] = json.dumps({"mcpServers": {"tidos": {
        "command": "python", "args": ["-I", "${CLAUDE_PLUGIN_ROOT}/bin/tidos_launch.py", "mcp"]}}}, indent=2) + "\n"
    files[".claude-plugin/plugin.json"] = json.dumps({
        "name": "tidos", "version": version(),
        "description": "TIDOS learns how your projects are built while you work with strong models, and guides weak or "
                       "free models with that knowledge: per-request playbooks, read-before-edit and "
                       "no-done-without-checks enforcement, subagents and an MCP server.",
        "author": {"name": "Tidjani Zitouni"}, "homepage": "https://github.com/Taedj/TIDOS",
        "repository": "https://github.com/Taedj/TIDOS", "license": "MIT",
        "keywords": ["learning", "guidance", "weak-models", "playbooks", "mcp", "hooks"],
    }, indent=2) + "\n"
    return files


def main():
    check = "--check" in sys.argv
    stale = []
    for rel, content in expected_files().items():
        path = os.path.join(PLUGIN, *rel.split("/"))
        current = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                current = f.read()
        if current != content:
            stale.append(rel)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
    if check and stale:
        print("plugin/ is out of date (run python scripts/build_plugin.py): " + ", ".join(stale))
        return 1
    print("plugin/ %s (%d file(s) %s)" % ("up to date" if check else "built", len(stale),
                                           "stale" if check else "written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
