"""TIDOS tool scout: sense missing capabilities, score trust, vet, propose - never install.

State (private): ~/.tidos/tools.json   {name: {status: proposed|approved|blacklisted, at, note}}
Cache:           ~/.tidos/scout_cache.json  GitHub/Scorecard trust data, refreshed after CACHE_DAYS
Only public tool/repo names ever leave the machine (GitHub + OpenSSF Scorecard APIs); never project data.
"""
import fnmatch
import glob
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from tidos_session import detect

CATALOG = os.path.join(detect.REPO_ROOT, "config", "tools.json")
CACHE_DAYS = 7
NO_SCORECARD_CAP = 85
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "MPL-2.0", "0BSD"}
COPYLEFT = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"}


def catalog():
    with open(CATALOG, "r", encoding="utf-8") as f:
        return json.load(f)["tools"]


def _home_file(name):
    return os.path.join(detect.tidos_home(), name)


def _load(name):
    try:
        with open(_home_file(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(name, data):
    os.makedirs(detect.tidos_home(), exist_ok=True)
    tmp = _home_file(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _home_file(name))


def state():
    return _load("tools.json")


def set_status(name, status, note=""):
    if status not in ("proposed", "approved", "blacklisted", "none"):
        raise ValueError("unknown status %s" % status)
    if not any(t["name"] == name for t in catalog()) and status != "blacklisted":
        raise KeyError(name)
    data = state()
    if status == "none":
        data.pop(name, None)
    else:
        data[name] = {"status": status, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "note": note}
    _save("tools.json", data)


# --- detection -------------------------------------------------------------------------------------
def _mcp_servers(project=None):
    names = set()
    paths = [os.path.join(os.path.expanduser("~"), ".claude.json")]
    if project:
        paths.append(os.path.join(project, ".mcp.json"))
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        names.update(k.lower() for k in data.get("mcpServers", {}))  # names only, never the values
        for proj in (data.get("projects") or {}).values():
            if isinstance(proj, dict):
                names.update(k.lower() for k in proj.get("mcpServers", {}))
    return names


_MODULES = {}


def _module_available(name):
    """Ask a normal interpreter (TIDOS itself may run with -I, which hides user site-packages)."""
    if name not in _MODULES:
        if importlib.util.find_spec(name) is not None:
            _MODULES[name] = True
        else:
            proc = subprocess.run([sys.executable, "-c", "import importlib.util, sys; "
                                   "sys.exit(importlib.util.find_spec(%r) is None)" % name],
                                  capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            _MODULES[name] = proc.returncode == 0
    return _MODULES[name]


def installed(tool, project=None, _mcp=None):
    d = tool.get("detect", {})
    if d.get("bin") and shutil.which(d["bin"]):
        return True
    if d.get("module") and _module_available(d["module"]):
        return True
    if d.get("npm_local") and project and os.path.isdir(os.path.join(project, "node_modules", d["npm_local"])):
        return True
    if d.get("mcp"):
        mcp = _mcp if _mcp is not None else _mcp_servers(project)
        return any(d["mcp"] in name for name in mcp)
    return False


def applies(tool, facts, project):
    if tool["stacks"] and not set(tool["stacks"]) & set(facts["stack"]):
        return False
    if tool.get("when_files"):
        return any(glob.glob(os.path.join(project, pattern)) for pattern in tool["when_files"])
    return True


def needs(project):
    """Capabilities this project lacks: {capability: [candidate tools]} (blacklisted tools excluded)."""
    facts = detect.project_facts(project)
    banned = {n for n, s in state().items() if s["status"] == "blacklisted"}
    mcp = _mcp_servers(project)
    by_cap = {}
    for tool in catalog():
        if applies(tool, facts, project):
            by_cap.setdefault(tool["capability"], []).append(tool)
    missing = {}
    for cap, tools in by_cap.items():
        if any(installed(t, project, mcp) for t in tools):
            continue
        candidates = [t for t in tools if t["name"] not in banned]
        if candidates:
            missing[cap] = candidates
    return facts, missing


def extra_checks(project, facts=None, limit=2):
    """Installed catalog tools whose `check` fits this project (used by the GUIDE brief)."""
    facts = facts or detect.project_facts(project)
    banned = {n for n, s in state().items() if s["status"] == "blacklisted"}
    out = []
    for tool in catalog():
        if tool.get("check") and tool["name"] not in banned and applies(tool, facts, project) \
                and installed(tool, project, _mcp=set()):
            out.append(tool["check"])
    return out[:limit]


# --- trust -----------------------------------------------------------------------------------------
def _get_json(url, timeout=15):
    headers = {"User-Agent": "TIDOS-tool-scout", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        # Python's CA bundle can miss an issuer the OS trusts: retry with the system curl (still verified)
        if "CERTIFICATE_VERIFY_FAILED" not in str(e) or not shutil.which("curl"):
            raise
        argv = ["curl", "-sSf", "--max-time", str(timeout)]
        for k, v in headers.items():
            argv += ["-H", "%s: %s" % (k, v)]
        proc = subprocess.run(argv + [url], capture_output=True, timeout=timeout + 5)
        if proc.returncode:
            raise
        return json.loads(proc.stdout.decode("utf-8"))


def score(repo_info, scorecard=None, now=None):
    """Trust 0-100 from public signals. Returns (score, reasons)."""
    if repo_info.get("archived"):
        return 0, ["archived: not maintained"]
    now = now or datetime.now(timezone.utc)
    stars = repo_info.get("stargazers_count", 0)
    pts = {"stars": min(30.0, 7.5 * math.log10(stars + 1))}
    pushed = repo_info.get("pushed_at")
    days = (now - datetime.fromisoformat(pushed.replace("Z", "+00:00"))).days if pushed else 9999
    pts["recent"] = 25 if days <= 30 else 15 if days <= 180 else 5 if days <= 365 else 0
    lic = ((repo_info.get("license") or {}).get("spdx_id")) or "NOASSERTION"
    pts["license"] = 15 if lic in PERMISSIVE else 10 if lic in COPYLEFT else 0
    reasons = ["%d stars" % stars, "last push %d days ago" % days, "license %s" % lic]
    if scorecard is not None:
        pts["scorecard"] = 3.0 * scorecard
        reasons.append("OpenSSF Scorecard %.1f/10" % scorecard)
        total = sum(pts.values())
    else:
        total = min(NO_SCORECARD_CAP, sum(pts.values()) * 100.0 / 70.0)  # popularity alone never earns full trust
        reasons.append("no Scorecard data (capped at %d)" % NO_SCORECARD_CAP)
    if lic in COPYLEFT:
        reasons.append("copyleft: fine to run as a tool, not to vendor into closed code")
    return int(round(min(100.0, total))), reasons


def trust(tool, refresh=False):
    cache = _load("scout_cache.json")
    hit = cache.get(tool["repo"])
    if hit and not refresh and time.time() - hit["fetched"] < CACHE_DAYS * 86400:
        return hit
    try:
        info = _get_json("https://api.github.com/repos/" + tool["repo"])
    except Exception as e:  # offline, rate-limited: keep the old value if any
        return hit or {"score": None, "reasons": ["unavailable: %s" % type(e).__name__], "fetched": 0}
    try:
        sc = _get_json("https://api.securityscorecards.dev/projects/github.com/" + tool["repo"]).get("score")
    except Exception:
        sc = None
    value, reasons = score(info, sc)
    entry = {"score": value, "reasons": reasons, "fetched": time.time(), "stars": info.get("stargazers_count", 0)}
    cache[tool["repo"]] = entry
    _save("scout_cache.json", cache)
    return entry


def search(query, limit=8):
    """GitHub repository search for a capability (only the query words are sent)."""
    q = urllib.parse.quote("%s in:name,description,topics archived:false" % query)
    data = _get_json("https://api.github.com/search/repositories?q=%s&sort=stars&order=desc&per_page=%d" % (q, limit))
    results = []
    for item in data.get("items", []):
        value, reasons = score(item)
        results.append({"repo": item["full_name"], "description": (item.get("description") or "")[:140],
                        "score": value, "reasons": reasons, "url": item["html_url"]})
    return sorted(results, key=lambda r: -r["score"])


# --- vetting + learning ----------------------------------------------------------------------------
def vet(tool, timeout=60):
    """Run an INSTALLED tool's version command in an empty temp dir; report exit code and stray writes."""
    if not tool.get("version"):
        return {"ok": False, "detail": "no version command in the catalog"}
    argv = list(tool["version"])
    argv[0] = sys.executable if argv[0] == "python" else (shutil.which(argv[0]) or argv[0])
    if not os.path.isfile(argv[0]):
        return {"ok": False, "detail": "%s is not installed" % tool["version"][0]}
    with tempfile.TemporaryDirectory(prefix="tidos-vet-") as tmp:
        start = time.time()
        try:
            proc = subprocess.run(argv, cwd=tmp, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=timeout, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"ok": False, "detail": "failed to run: %s" % type(e).__name__}
        written = [os.path.relpath(p, tmp) for p in glob.glob(os.path.join(tmp, "**", "*"), recursive=True)]
        out = (proc.stdout or proc.stderr).strip().splitlines()
        return {"ok": proc.returncode == 0 and not written, "exit": proc.returncode,
                "version": out[0][:120] if out else "", "seconds": round(time.time() - start, 1),
                "wrote": written[:10],
                "detail": "clean" if not written else "wrote files in an empty dir during a version check"}


def usage_xp(conn):
    """Tool XP from real sessions: how often each catalog tool ran as a check, and how often it passed."""
    stats = {}
    for tool in catalog():
        names = [tool["name"]] + [v for k, v in tool.get("detect", {}).items() if k in ("bin", "module", "npm_local")]
        pats = sorted(set(names))
        clauses = " OR ".join(["command LIKE ? OR command LIKE ? OR command LIKE ?"] * len(pats))
        params = []
        for n in pats:
            params += [n + " %", "python -m " + n + "%", "npx " + n + "%"]
        row = conn.execute("SELECT COUNT(*) n, COALESCE(SUM(passed), 0) p FROM verifications WHERE %s" % clauses,
                           params).fetchone()
        if row["n"]:
            stats[tool["name"]] = {"runs": row["n"], "passed": row["p"], "xp": 5 * row["p"] - 2 * (row["n"] - row["p"])}
    return stats


def install_command(tool):
    return tool["install"]["windows" if os.name == "nt" else "unix"]


def report(project, with_trust=False):
    facts, missing = needs(project)
    st = state()
    rows = []
    for cap, tools in missing.items():
        for t in tools:
            entry = trust(t) if with_trust else None
            rows.append({"capability": cap, "name": t["name"], "why": t["why"], "install": install_command(t),
                         "status": st.get(t["name"], {}).get("status", ""),
                         "trust": entry["score"] if entry else None,
                         "trust_reasons": entry["reasons"] if entry else []})
    rows.sort(key=lambda r: (r["capability"], -(r["trust"] or 0)))
    return facts, rows


def overview(conn=None, project=None):
    """Every catalog tool: installed?, status, cached trust, usage XP (for the dashboard)."""
    st, cache = state(), _load("scout_cache.json")
    mcp = _mcp_servers(project)
    xp = usage_xp(conn) if conn is not None else {}
    out = []
    for t in catalog():
        c = cache.get(t["repo"], {})
        out.append({"name": t["name"], "capability": t["capability"], "why": t["why"], "repo": t["repo"],
                    "installed": installed(t, project, mcp), "status": st.get(t["name"], {}).get("status", ""),
                    "trust": c.get("score"), "trust_reasons": c.get("reasons", []), "install": install_command(t),
                    "usage": xp.get(t["name"])})
    return out
