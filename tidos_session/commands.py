"""TIDOS slash commands for every tool: START TIDOS installs them into each tool's own "/" menu.

One registry (COMMANDS) is rendered into every format a tool reads, user-level, so the commands appear in the
drop-down list when the user types "/" in any folder:
  Claude Code  ~/.claude/commands/<name>.md          (always)
  OpenCode     ~/.config/opencode/command/<name>.md   (when ~/.config/opencode exists)
  Gemini CLI   ~/.gemini/commands/<name>.toml         (when ~/.gemini exists)
  Antigravity  ~/.gemini/config/skills/<name>/SKILL.md, ~/.gemini/antigravity/global_workflows/<name>.md
  Cline        ~/Documents/Cline/Workflows/<name>.md
  Cursor       ~/.cursor/commands/<name>.md
  Codex CLI    ~/.codex/prompts/<name>.md
  Windsurf     ~/.codeium/windsurf/global_workflows/<name>.md
A tool is served only when its folder already exists (TIDOS never creates another tool's config). Tools without
a "/" menu still get every command from the START TIDOS brief (brief.commands_footer).
A file is (re)written only when it is missing or was written by TIDOS (marker line): a command you edited
yourself is never overwritten. New sessions pick the commands up.
"""
import os
import sys
from collections import namedtuple

from .detect import REPO_ROOT

MARK = "<!-- installed by TIDOS (START TIDOS) - edit freely: TIDOS stops updating it once this line is removed -->"
MARK_TEXT = "installed by TIDOS (START TIDOS)"
ARGS = "{ARGS}"  # replaced by each tool's own argument placeholder

Command = namedtuple("Command", "name args description cli body")

PASSWORD_RULE = ("NEVER ask for, accept, repeat or store the control password in this chat or any terminal command; "
                 "login happens in the browser only. If the user types it here, tell them to change it from the "
                 "Security panel.")

COMMANDS = [
    Command("TIDOSZIT", "", "Open the TIDOS Control Center (login in the browser) and list every TIDOS / command",
            "launcher", "Then run `{run:tidos_session commands}` and show the user that list of TIDOS commands. Say the "
            "control center is open at http://localhost:8767/ and that they sign in there with Google, then enter "
            "the control password in the browser.\n" + PASSWORD_RULE + "\nTo stop it later: the same launcher with "
            "`-Stop` (PowerShell) or `--stop` (bash)."),
    Command("tidos-help", "", "List every TIDOS / command with what it does", "tidos_session commands",
            "Show the list as it is printed, then ask the user which one to run."),
    Command("tidos-start", "", "START TIDOS: load TIDOS for this project (detects the tool and model)",
            "tidos_session start --project .", "Then follow the brief it prints for the rest of this session."),
    Command("tidos", "<what you want done>", "TIDOS end-to-end for one request: plan, implement, verify, review, learn",
            None, "Run the TIDOS loop for this request: " + ARGS + "\n\n"
            "1. Context: run `{run:tidos_session guide \"<request>\" --project .}` and follow its \"define done\" step.\n"
            "2. Plan: for anything beyond a one-line change, show a short plan first.\n"
            "3. Implement in small steps (read before edit).\n"
            "4. Verify: run the project's real checks; fix until they pass.\n"
            "5. Review the diff yourself; fix blocking findings, then verify again.\n"
            "6. Learn: leave one piece of advice for weaker models with `/tidos-note`.\n"
            "7. Report: files changed, check output, anything left UNVERIFIED."),
    Command("tidos-guide", "<request>", "Just-in-time guidance for one request: playbooks, checks and traps",
            "tidos_session guide \"" + ARGS + "\" --project .", "Follow the guidance while you do the request."),
    Command("tidos-status", "", "TIDOS STATUS: level, rank, stats, domains and daily quests", "tidos_learn status", ""),
    Command("tidos-note", "<advice>", "Leave one piece of advice for weaker models working on this project",
            "tidos_learn note --project \"<this project's folder name>\" \"" + ARGS + "\"", ""),
    Command("tidos-learn", "", "Learn now: import recent sessions and refresh the playbooks", "tidos_learn distill", ""),
    Command("tidos-army", "", "Shadow Army: your subagents ranked by mission evidence", "tidos_learn army", ""),
    Command("tidos-tools", "", "Tool Scout: tools this project needs and their state", "tidos_scout needs --project .",
            "Never install a tool unless the user approves it."),
    Command("tidos-center", "", "Deep review of the TIDOS Control Center in this session: pending actions, jobs, trust, next moves",
            "tidos_brain center", "Show the report briefly, then ask the user which pending item(s) they want "
            "handled: owner-only ones go to /TIDOSZIT (you never handle them here), agent ones may run via "
            "`{run:tidos_brain center-act run_job <job>}` only when its trust level allows it."),
    Command("tidos-share", "[agree|decline|status]", "Community learning: agree or not to share anonymous lessons",
            "tidos_session consent " + ARGS, "If no answer was given, use `status`. Never choose agree or decline for "
            "the user. Not agree never limits TIDOS."),
    Command("tidos-backup", "", "Back up the TIDOS brain (your private learning)", "tidos_brain backup", ""),
    Command("tidos-orb", "", "Show the floating TIDOS orb and open its panel (journey, evolution, solutions, next moves)",
            "tidos_orb open", "The orb can be dragged anywhere; a click opens or closes the panel."),
]

PLACEHOLDER = {"claude": "$ARGUMENTS", "opencode": "$ARGUMENTS", "cursor": "$ARGUMENTS", "codex": "$ARGUMENTS",
               "gemini": "{{args}}"}
SPOKEN_ARGS = "<what the user typed after the command>"


def _slash(path):
    return path.replace("\\", "/")


def launcher(repo=REPO_ROOT, nt=None):
    nt = os.name == "nt" if nt is None else nt
    if nt:
        return 'powershell -NoProfile -ExecutionPolicy Bypass -File "%s/scripts/tidoszit.ps1"' % _slash(repo)
    return 'bash "%s/scripts/tidoszit.sh"' % _slash(repo)


def run_line(cli, repo=REPO_ROOT, python=None):
    """'tidos_learn status' -> the exact command line on this machine."""
    if cli == "launcher":
        return launcher(repo)
    package, _, rest = cli.partition(" ")
    python = python or _slash(sys.executable or "python")
    return ('"%s" -I "%s/%s/__main__.py" %s' % (python, _slash(repo), package, rest)).rstrip()


def _expand(text, repo):
    while "{run:" in text:
        start = text.index("{run:")
        end = text.index("}", start)
        text = text[:start] + run_line(text[start + 5:end], repo) + text[end + 1:]
    return text


def prompt(cmd, args=SPOKEN_ARGS, repo=REPO_ROOT):
    """The instructions a model follows when the user types /<name>, in any tool."""
    lines = []
    if cmd.cli:
        lines.append("%s.\n\nRun this once, from the user's current project folder:\n  %s\n"
                     % (cmd.description, run_line(cmd.cli, repo)))
    if cmd.body:
        lines.append(_expand(cmd.body, repo))
    if cmd.cli and cmd.name != "TIDOSZIT":
        lines.append("Show the user the result briefly, in their language, keeping the command's own numbers and "
                     "wording. If it fails, show the error; do not guess.")
    return "\n".join(lines).replace(ARGS, args).strip() + "\n"


def _md(cmd, tool, repo, front=True):
    text = prompt(cmd, PLACEHOLDER.get(tool, SPOKEN_ARGS), repo)
    head = ""
    if front:
        head = "---\ndescription: %s\n" % cmd.description
        if cmd.args and tool in ("claude", "codex"):
            head += "argument-hint: %s\n" % cmd.args
        head += "---\n\n"
    return head + text + "\n" + MARK + "\n"


def _skill(cmd, repo):
    return ("---\nname: %s\ndescription: >-\n  TIDOS command /%s. %s. Use when the user types /%s or %s.\n---\n\n%s\n%s\n"
            % (cmd.name.lower(), cmd.name.lower(), cmd.description, cmd.name.lower(), cmd.name,
               prompt(cmd, SPOKEN_ARGS, repo), MARK))


def _toml(cmd, repo):
    body = prompt(cmd, PLACEHOLDER["gemini"], repo)
    return "# %s - edit freely: TIDOS stops updating it once this line is removed\ndescription = %s\nprompt = '''\n%s'''\n" % (
        MARK_TEXT, '"%s"' % cmd.description.replace('"', "'"), body.replace("'''", '"""'))


def targets(home=None):
    """(tool, folder, render(cmd, repo) -> (relative path, text)) for every tool installed on this machine."""
    home = home or os.path.expanduser("~")
    j = os.path.join
    out = [("claude", j(home, ".claude", "commands"), lambda c, r: (c.name + ".md", _md(c, "claude", r)))]
    optional = [
        (j(home, ".config", "opencode"), "opencode", j(home, ".config", "opencode", "command"),
         lambda c, r: (c.name + ".md", _md(c, "opencode", r))),
        (j(home, ".gemini"), "gemini", j(home, ".gemini", "commands"), lambda c, r: (c.name + ".toml", _toml(c, r))),
        (j(home, ".gemini"), "antigravity", j(home, ".gemini", "config", "skills"),
         lambda c, r: (j(c.name.lower(), "SKILL.md"), _skill(c, r))),
        (j(home, ".gemini", "antigravity"), "antigravity-workflows", j(home, ".gemini", "antigravity", "global_workflows"),
         lambda c, r: (c.name + ".md", _md(c, "antigravity", r))),
        (j(home, "Documents", "Cline"), "cline", j(home, "Documents", "Cline", "Workflows"),
         lambda c, r: (c.name + ".md", _md(c, "cline", r, front=False))),
        (j(home, ".cursor"), "cursor", j(home, ".cursor", "commands"), lambda c, r: (c.name + ".md", _md(c, "cursor", r, front=False))),
        (j(home, ".codex"), "codex", j(home, ".codex", "prompts"), lambda c, r: (c.name + ".md", _md(c, "codex", r))),
        (j(home, ".codeium", "windsurf"), "windsurf", j(home, ".codeium", "windsurf", "global_workflows"),
         lambda c, r: (c.name + ".md", _md(c, "windsurf", r))),
    ]
    out += [(tool, folder, render) for root, tool, folder, render in optional if os.path.isdir(root)]
    return out


def user_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "commands")


def _write(dest, text):
    try:
        with open(dest, "r", encoding="utf-8") as f:
            current = f.read()
    except OSError:
        current = None
    if current == text or (current is not None and MARK_TEXT not in current):
        return False  # already current, or edited by the user: leave it alone
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return True


def install(target=None, repo=REPO_ROOT, home=None):
    """Install/refresh the commands for every tool on this machine (target: only Claude Code, into that folder).
    Returns the paths written (empty when all were current)."""
    chosen = targets(home)
    if target:
        chosen = [("claude", target, chosen[0][2])]
    written = []
    for _tool, folder, render in chosen:
        for cmd in COMMANDS:
            rel, text = render(cmd, repo)
            dest = os.path.join(folder, rel)
            if _write(dest, text):
                written.append(dest)
    return written


def installed_tools(home=None):
    return [tool for tool, folder, _ in targets(home)
            if os.path.isfile(os.path.join(folder, "TIDOSZIT.md")) or os.path.isfile(os.path.join(folder, "TIDOSZIT.toml"))
            or os.path.isfile(os.path.join(folder, "tidoszit", "SKILL.md"))]


def listing(repo=REPO_ROOT):
    """[{name, args, description, run}] for the dashboard, /tidos-help and the brief."""
    return [{"name": "/" + c.name, "args": c.args, "description": c.description,
             "run": run_line(c.cli, repo).replace(ARGS, c.args) if c.cli else None} for c in COMMANDS]


def text_listing(home=None):
    rows = listing()
    width = max(len(r["name"] + (" " + r["args"] if r["args"] else "")) for r in rows)
    lines = ["TIDOS commands (type / in your tool to pick one):"]
    for r in rows:
        lines.append("  %-*s  %s" % (width, r["name"] + (" " + r["args"] if r["args"] else ""), r["description"]))
    tools = installed_tools(home)
    lines.append("Installed in: %s" % (", ".join(tools) if tools else "none yet (say START TIDOS)"))
    lines.append("Any other tool: type the command anyway; the START TIDOS brief tells the model what to run.")
    return "\n".join(lines)
