"""Dungeon tasks: discovery, isolated workdirs, hidden-test verification.

Layout of one task:  evals/dungeons/<suite>/<name>/
  task.json   suite, name, difficulty (E..S), title, prompt, verify (argv), tags, timeout
  fixture/    the project the agent starts from
  hidden/     tests copied in only AFTER the agent finished (the agent never sees them)
  solution/   reference solution overlay (used to validate the task itself)
"""
import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUNGEONS = os.path.join(REPO_ROOT, "evals", "dungeons")
PROTOCOL = os.path.join(REPO_ROOT, "evals", "tidos_protocol.md")
VERIFY_TIMEOUT = 240


class Task:
    def __init__(self, path):
        self.path = path
        with open(os.path.join(path, "task.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.suite = meta["suite"]
        self.name = meta["name"]
        self.difficulty = meta.get("difficulty", "C")
        self.title = meta.get("title", self.name)
        self.prompt = meta["prompt"]
        self.verify = meta["verify"]
        self.tags = meta.get("tags", [])
        self.timeout = int(meta.get("timeout", 600))

    @property
    def id(self):
        return "%s/%s" % (self.suite, self.name)

    def tool_available(self):
        exe = self.verify[0]
        return exe == "{python}" or shutil.which(exe) is not None

    def prepare(self, workdir, with_tidos=False, ablate=None, unit=None):
        """Create a fresh workdir: fixture + TASK.md (+ TIDOS_PROTOCOL.md / GUIDE.md / UNIT.md)."""
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        shutil.copytree(os.path.join(self.path, "fixture"), workdir)
        with open(os.path.join(workdir, "TASK.md"), "w", encoding="utf-8") as f:
            f.write("# Task: %s\n\n%s" % (self.title, self.prompt))
        if with_tidos == "guide":
            # the real GUIDE mode: brief for this workdir + per-request guidance (never counted as "served")
            from tidos_session import brief, detect, guide
            facts = detect.project_facts(workdir)
            text = brief.guide_brief({"model": "weak model", "tier": "weak", "tool": "opencode"}, facts, record=False, ablate=ablate)
            text = text.split("## For EVERY new request")[0] + "\n" + guide.guidance(self.prompt, workdir, record=False)[1]
            with open(os.path.join(workdir, "GUIDE.md"), "w", encoding="utf-8") as f:
                f.write(text)
        elif with_tidos == "unit":  # Shadow Army trial: the subagent's own instructions
            from tidos_learn import army
            with open(os.path.join(workdir, "UNIT.md"), "w", encoding="utf-8") as f:
                f.write(army.unit_prompt(unit))
        elif with_tidos:
            shutil.copy(PROTOCOL, os.path.join(workdir, "TIDOS_PROTOCOL.md"))

    def overlay(self, part, workdir):
        src = os.path.join(self.path, part)
        if os.path.isdir(src):
            shutil.copytree(src, workdir, dirs_exist_ok=True)

    def run_verify(self, workdir):
        """Copy hidden tests in (overwriting anything the agent wrote there) and run the verify command."""
        hidden_target = os.path.join(workdir, "hidden_tests")
        if os.path.isdir(hidden_target):
            shutil.rmtree(hidden_target)
        self.overlay("hidden", workdir)
        argv = [sys.executable if a == "{python}" else a for a in self.verify]
        exe = shutil.which(argv[0]) or argv[0]
        try:
            proc = subprocess.run([exe] + argv[1:], cwd=workdir, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=VERIFY_TIMEOUT,
                                  env=_clean_env())
        except subprocess.TimeoutExpired:
            return False, "verify timed out after %ds" % VERIFY_TIMEOUT
        except OSError as e:
            return False, "verify could not start: %s" % e
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-4000:]


def _clean_env():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def load_tasks(suite=None, task=None):
    tasks = []
    for root, _, files in os.walk(DUNGEONS):
        if "task.json" in files:
            t = Task(root)
            if (suite is None or t.suite == suite) and (task is None or task in (t.name, t.id)):
                tasks.append(t)
    return sorted(tasks, key=lambda t: t.id)
