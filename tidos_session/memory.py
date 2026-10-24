"""User memory lives in ~/.tidos/memory/ (private), never in the TIDOS repository.

The repo's memory/ folder only holds empty templates. migrate() (run by START TIDOS) copies any
personal content found in the repo's memory/ files into ~/.tidos/memory/ - never overwriting what is
already there - and resets the repo copies to templates, so personal data cannot be pushed to GitHub.
"""
import os
import shutil

from .detect import REPO_ROOT, tidos_home

TEMPLATE_MARK = "<!-- tidos-memory-template -->"
REPO_MEMORY = os.path.join(REPO_ROOT, "memory")

TEMPLATES = {
    "USER_PROFILE.md": "Who the user is: role, domains, languages, tools they use daily.",
    "PREFERENCES.md": "Explicit user directives: style, workflow, what to always / never do.",
    "PATTERNS.md": "Reusable code patterns validated in the user's projects (promote after 2+ uses).",
    "LESSONS.md": "Post-mortems: issue, root cause, resolution, lesson, evidence.",
    "BEST_PRACTICES.md": "Engineering practices that proved themselves in the user's projects.",
    "PROJECT_HISTORY.md": "Milestones and decisions per project.",
}


def memory_dir():
    return os.path.join(tidos_home(), "memory")


def template_text(name):
    title = os.path.splitext(name)[0].replace("_", " ").title()
    return ("%s\n# %s (template)\n\n%s\n\nYour real file lives in `~/.tidos/memory/%s` (private, outside every repository).\n"
            "TIDOS reads and writes it there; this repository copy stays empty so personal data is never published.\n"
            % (TEMPLATE_MARK, title, TEMPLATES.get(name, "User memory."), name))


def is_template(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return TEMPLATE_MARK in f.read(200)
    except OSError:
        return True


def migrate(repo_memory=REPO_MEMORY):
    """Move personal memory out of the repo. Returns (moved, kept_existing) file names."""
    target = memory_dir()
    os.makedirs(target, exist_ok=True)
    moved, kept = [], []
    for name in sorted(os.listdir(repo_memory)) if os.path.isdir(repo_memory) else []:
        src = os.path.join(repo_memory, name)
        if name == "README.md" or not name.endswith(".md") or not os.path.isfile(src):
            continue
        if not is_template(src):
            dst = os.path.join(target, name)
            if os.path.exists(dst):
                # never overwrite: keep both, the repo version gets a dated suffix
                base, ext = os.path.splitext(name)
                dst = os.path.join(target, "%s.from-repo%s" % (base, ext))
                kept.append(name)
            shutil.copy2(src, dst)
            moved.append(name)
            if name in TEMPLATES:
                with open(src, "w", encoding="utf-8", newline="\n") as f:
                    f.write(template_text(name))
            else:
                os.remove(src)  # not a standard memory file: keep it private only, no repo template
    for name in TEMPLATES:  # make sure every memory file exists privately
        path = os.path.join(target, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("# %s\n\n" % os.path.splitext(name)[0].replace("_", " ").title())
    return moved, kept
