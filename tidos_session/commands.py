"""User-level slash commands: START TIDOS installs /TIDOSZIT for the whole machine.

Claude Code loads project commands only from the folder a session opens in, so a TIDOS submodule's
.claude/commands/ is invisible from the parent project. install() copies TIDOS's user commands into
~/.claude/commands/ with this machine's TIDOS path filled in, so /TIDOSZIT works in every folder.
A file is (re)written only when it is missing or was written by TIDOS (marker line): a command you edited
yourself is never overwritten. New sessions pick the command up.
"""
import os

from .detect import REPO_ROOT

MARK = "<!-- installed by TIDOS (START TIDOS) - edit freely: TIDOS stops updating it once this line is removed -->"
COMMANDS = ["TIDOSZIT.md"]


def user_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "commands")


def render(name, repo=REPO_ROOT):
    with open(os.path.join(repo, ".claude", "commands", name), "r", encoding="utf-8") as f:
        text = f.read()
    path = repo.replace("\\", "/")
    text = text.replace("use `$TIDOS_HOME` if it is set, otherwise the folder that contains",
                        "use `$TIDOS_HOME` if it is set, otherwise `%s` (this machine), otherwise the folder that "
                        "contains" % path)
    return text.rstrip() + "\n\n" + MARK + "\n"


def install(target=None, repo=REPO_ROOT):
    """Install/refresh the user-level commands. Returns the paths written (empty when all were current)."""
    target = target or user_dir()
    written = []
    for name in COMMANDS:
        dest = os.path.join(target, name)
        text = render(name, repo)
        try:
            with open(dest, "r", encoding="utf-8") as f:
                current = f.read()
        except OSError:
            current = None
        if current == text or (current is not None and MARK not in current):
            continue  # already current, or edited by the user: leave it alone
        os.makedirs(target, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(dest)
    return written
