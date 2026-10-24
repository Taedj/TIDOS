"""TIDOS weak-model driver: the loop is code, the models only do bounded steps.

  1. DEFINE DONE  teacher (or the student) turns the task into executable checks in driver_checks/
                  gate: checks must exist, run, and FAIL on the untouched code
  2. IMPLEMENT    student changes project code until the checks pass (checks are hash-protected)
  3. VERIFY       the driver runs the checks itself
  4. REPAIR       failing output goes back to the student (max_repairs rounds)
  5. ESCALATE     still failing -> the teacher gets the same step plus the failure log

Working files use neutral names (no "tidos"): a weak model misspelled a "tidos" path in evals.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

from tidos_evals.agents import run_agent

STEP_FILE = "driver_step.md"
CHECKS_DIR = "driver_checks"
PROMPT = "Read driver_step.md in the current directory and do exactly what it says. Use relative paths only."
CHECK_TIMEOUT = 180
OUTPUT_LIMIT = 3500

# Per-language check templates: (relative check file, verify argv, example)
LANGUAGES = {
    "python": ("driver_checks/test_driver_checks.py",
               ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider", "driver_checks"],
               "pytest functions (`def test_...():` with plain `assert`). Import project modules directly "
               "(the project root is the current directory). To test a script or another language, use "
               "`subprocess.run([...], capture_output=True, text=True)`; for SQL use the `sqlite3` module."),
    "javascript": ("driver_checks/checks.test.js", ["node", "--test", "driver_checks/*.test.js"],
                   "`node:test` + `node:assert` (CommonJS `require`), importing project files with `require('../file.js')`."),
    "dart": ("driver_checks/checks_test.dart", ["dart", "run", "driver_checks/checks_test.dart"],
             "a Dart script with `void main()` that imports `'../file.dart'`, prints a message and calls "
             "`exit(1)` (from `dart:io`) on the first failed check."),
}

IGNORED = {STEP_FILE, "TASK.md", "TIDOS_PROTOCOL.md", "opencode.json", "_tidos_eval_log.txt"}


def detect_language(workdir):
    counts = {"python": 0, "javascript": 0, "dart": 0}
    for root, dirs, files in os.walk(workdir):
        dirs[:] = [d for d in dirs if d not in (CHECKS_DIR, "node_modules", ".git", "hidden_tests")]
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext == ".js":
                counts["javascript"] += 1
            elif ext == ".dart":
                counts["dart"] += 1
            elif ext in (".py", ".sql", ".ps1"):
                counts["python"] += 1
    return max(counts, key=counts.get) if any(counts.values()) else "python"


class DriverResult:
    def __init__(self):
        self.passed = False
        self.reason = ""
        self.cost_usd = 0.0
        self.agent_calls = 0
        self.steps = []

    def note(self, step, detail):
        self.steps.append((time.strftime("%H:%M:%S"), step, detail))

    def log(self):
        return "\n".join("[%s] %-10s %s" % s for s in self.steps)[-6000:]


class Driver:
    def __init__(self, student, teacher=None, max_repairs=2, budget_usd=1.0, checks_by=None):
        self.student = student
        self.teacher = teacher
        self.max_repairs = max_repairs
        self.budget_usd = budget_usd
        # the strong model defines "done" when available: cheap for it, hard for weak models
        self.checks_by = checks_by or ("teacher" if teacher else "student")

    # --- agent + check plumbing ----------------------------------------------
    def _agent(self, spec, workdir, instructions, timeout, result, label):
        with open(os.path.join(workdir, STEP_FILE), "w", encoding="utf-8") as f:
            f.write(instructions)
        res = run_agent(spec, workdir, PROMPT, timeout, self.budget_usd)
        os.remove(os.path.join(workdir, STEP_FILE))
        result.agent_calls += 1
        result.cost_usd += res.cost_usd or 0.0
        result.note(label, "%s ok=%s%s" % (spec, res.ok, " error=%s" % res.error if res.error else ""))
        return res

    def _run_checks(self, workdir, language):
        argv = [sys.executable if a == "{python}" else a for a in LANGUAGES[language][1]]
        exe = shutil.which(argv[0]) or argv[0]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PWD=workdir)
        try:
            proc = subprocess.run([exe] + argv[1:], cwd=workdir, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=CHECK_TIMEOUT, env=env)
        except subprocess.TimeoutExpired:
            return False, "checks timed out after %ds" % CHECK_TIMEOUT
        except OSError as e:
            return False, "checks could not start: %s" % e
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-OUTPUT_LIMIT:]

    @staticmethod
    def _snapshot(workdir):
        """Hash + content of every check file, to detect and undo tampering."""
        snap = {}
        base = os.path.join(workdir, CHECKS_DIR)
        for root, _, files in os.walk(base):
            for f in files:
                path = os.path.join(root, f)
                with open(path, "rb") as fh:
                    data = fh.read()
                snap[os.path.relpath(path, workdir)] = (hashlib.sha256(data).hexdigest(), data)
        return snap

    @staticmethod
    def _restore(workdir, snap):
        base = os.path.join(workdir, CHECKS_DIR)
        if os.path.isdir(base):
            shutil.rmtree(base)
        for rel, (_, data) in snap.items():
            path = os.path.join(workdir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(data)

    @staticmethod
    def _project_snapshot(workdir):
        snap = {}
        for root, dirs, files in os.walk(workdir):
            dirs[:] = [d for d in dirs if d not in (CHECKS_DIR, "__pycache__", "node_modules", ".pytest_cache")]
            for f in files:
                if f in IGNORED:
                    continue
                path = os.path.join(root, f)
                with open(path, "rb") as fh:
                    snap[os.path.relpath(path, workdir)] = fh.read()
        return snap

    # --- step instructions ----------------------------------------------------
    @staticmethod
    def _define_done_instructions(language, task_text, feedback=""):
        check_file, argv, how = LANGUAGES[language]
        return (
            "# Step: write executable checks (do NOT change the project)\n\n"
            "Below is a task for this project. Your ONLY job in this step is to write automated checks that\n"
            "verify EVERY requirement of the task, including each example and edge case it mentions.\n\n"
            "- Write them in `%s` using %s\n"
            "- Do NOT modify any other file. Do NOT implement the task.\n"
            "- The checks must fail on the current code (the task is not done yet) and must pass once the task\n"
            "  is correctly implemented. Assert exact expected values from the task text.\n"
            "- Run them once with: `%s` (they are expected to fail now).\n\n%s"
            "## Task\n\n%s\n" % (check_file, how, " ".join(a if a != "{python}" else "python" for a in argv),
                                  feedback, task_text))

    @staticmethod
    def _implement_instructions(language, task_text, failure=""):
        argv = " ".join(a if a != "{python}" else "python" for a in LANGUAGES[language][1])
        return (
            "# Step: implement\n\n"
            "Change the project code so that the task below is done and ALL checks in `%s/` pass.\n\n"
            "Rules:\n"
            "1. First read the relevant project files and the checks in `%s/`.\n"
            "2. NEVER edit, delete or add files in `%s/` (they are restored automatically).\n"
            "3. Make small, targeted edits; keep function names and signatures.\n"
            "4. Run `%s` and fix the code until every check passes.\n"
            "5. Use relative paths only.\n\n%s"
            "## Task\n\n%s\n" % (CHECKS_DIR, CHECKS_DIR, CHECKS_DIR, argv,
                                 ("## Last check run FAILED - fix exactly this\n\n```\n%s\n```\n\n" % failure)
                                 if failure else "", task_text))

    # --- the loop -------------------------------------------------------------
    def drive(self, workdir, timeout=900):
        result = DriverResult()
        deadline = time.time() + timeout * 3
        with open(os.path.join(workdir, "TASK.md"), "r", encoding="utf-8") as f:
            task_text = f.read()
        language = detect_language(workdir)
        result.note("start", "student=%s teacher=%s language=%s checks_by=%s" % (
            self.student, self.teacher, language, self.checks_by))

        # 1. DEFINE DONE (+ gate)
        author = self.teacher if self.checks_by == "teacher" else self.student
        original = self._project_snapshot(workdir)
        feedback = ""
        checks_ok = False
        for attempt in range(2):
            self._agent(author, workdir, self._define_done_instructions(language, task_text, feedback),
                        timeout, result, "define")
            # the check author must not touch the project: undo anything it changed
            current = self._project_snapshot(workdir)
            for rel in set(current) - set(original):
                os.remove(os.path.join(workdir, rel))
            for rel, data in original.items():
                if current.get(rel) != data:
                    with open(os.path.join(workdir, rel), "wb") as fh:
                        fh.write(data)
            check_path = os.path.join(workdir, LANGUAGES[language][0])
            if not os.path.isfile(check_path):
                feedback = "## Previous attempt problem\n\nNo check file was written at `%s`.\n\n" % LANGUAGES[language][0]
                result.note("gate", "no check file")
                continue
            passed, output = self._run_checks(workdir, language)
            if passed:
                feedback = ("## Previous attempt problem\n\nYour checks PASS on the unfinished code, so they do not "
                            "test the task. Make them assert the required behavior.\n\n")
                result.note("gate", "checks pass on untouched code -> rejected")
                continue
            if "SyntaxError" in output or "ModuleNotFoundError: No module named 'pytest'" in output:
                feedback = "## Previous attempt problem\n\nThe checks do not run:\n```\n%s\n```\n\n" % output[-1500:]
                result.note("gate", "checks broken")
                continue
            checks_ok = True
            break
        if not checks_ok:
            result.reason = "could not define executable checks"
            return result
        checks = self._snapshot(workdir)
        result.note("gate", "%d check file(s) accepted (fail on untouched code)" % len(checks))

        # 2-4. IMPLEMENT -> VERIFY -> REPAIR
        failure = ""
        for round_no in range(1 + self.max_repairs):
            if time.time() > deadline:
                result.reason = "driver deadline reached"
                break
            self._agent(self.student, workdir, self._implement_instructions(language, task_text, failure),
                        timeout, result, "implement" if round_no == 0 else "repair")
            if self._snapshot(workdir) != checks:
                result.note("guard", "checks were modified by the model -> restored")
                self._restore(workdir, checks)
            passed, output = self._run_checks(workdir, language)
            result.note("verify", "PASS" if passed else "FAIL: " + output.strip().splitlines()[-1][:150]
                        if output.strip() else "FAIL")
            if passed:
                result.passed = True
                break
            failure = output

        # 5. ESCALATE
        if not result.passed and self.teacher and time.time() < deadline:
            self._agent(self.teacher, workdir, self._implement_instructions(language, task_text, failure),
                        timeout, result, "escalate")
            if self._snapshot(workdir) != checks:
                result.note("guard", "checks were modified by the teacher -> restored")
                self._restore(workdir, checks)
            passed, output = self._run_checks(workdir, language)
            result.note("verify", "PASS (teacher)" if passed else "FAIL after escalation")
            result.passed = passed

        shutil.rmtree(os.path.join(workdir, CHECKS_DIR), ignore_errors=True)
        if not result.passed and not result.reason:
            result.reason = "checks still failing"
        return result
