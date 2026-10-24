"""Learn the user's standing directives ("do not change trading logic", "never commit") from their prompts.

Only directive-shaped sentences count, and only when they RECUR (similar wording at least MIN_REPEAT times),
so one-off task details never become rules. Learned per project, plus "all projects" when a directive
recurs in several projects. Output: ~/.tidos/memory/LEARNED_PREFERENCES.md (generated, private).
"""
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from tidos_brain.claude_code import is_synthetic
from tidos_session.detect import tidos_home

MIN_REPEAT = 2
SIMILARITY = 0.5
MIN_SPECIFIC_WORDS = 3
DIRECTIVE = re.compile(
    r"^(?:[-*\d.)\s]*)(?:please\s+)?(do not|don'?t|dont|never|always|make sure|must( not)?|avoid|"
    r"i (?:do not|don'?t|dont) want|i prefer|keep|preserve|toujours|jamais|ne (?:pas|jamais))\b", re.IGNORECASE)
STOP = {"the", "a", "an", "to", "of", "in", "on", "and", "or", "any", "this", "that", "it", "is", "be", "for",
        "with", "do", "not", "don't", "dont", "never", "always", "please", "i", "you", "your", "my", "yet", "pass"}


def _sentences(text):
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        s = raw.strip().strip("-*• ").strip()
        if 15 <= len(s) <= 220 and DIRECTIVE.match(s):
            yield s


def _tokens(sentence):
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+", sentence.lower()) if w not in STOP and len(w) > 2}


NEGATIVE = re.compile(r"\b(do not|don'?t|dont|never|must not|avoid|i (?:do not|don'?t|dont) want|jamais|"
                      r"ne (?:pas|jamais))\b", re.IGNORECASE)


def polarity(sentence):
    """'-' for a prohibition (never / do not / avoid), '+' for an instruction (always / keep / make sure)."""
    return "-" if NEGATIVE.search(sentence) else "+"


def _cluster(items):
    """items: [(sentence, project, ts)] -> clusters of similar sentences WITH THE SAME polarity: 'always run
    the tests' and 'never run the tests' share their words but must never merge into one rule."""
    clusters = []
    for sentence, project, ts in items:
        toks = _tokens(sentence)
        if len(toks) < MIN_SPECIFIC_WORDS:
            continue  # "Do NOT modify code" is a review-time instruction, harmful as a general rule
        sign = polarity(sentence)
        for c in clusters:
            inter = len(toks & c["tokens"])
            if c["polarity"] == sign and inter and inter / len(toks | c["tokens"]) >= SIMILARITY:
                c["members"].append((sentence, project, ts))
                c["tokens"] |= toks
                break
        else:
            clusters.append({"tokens": set(toks), "polarity": sign, "members": [(sentence, project, ts)]})
    return clusters


def resolve_conflicts(entries):
    """Opposite rules about the same thing (same words, opposite polarity): keep the one you said most
    recently. Returns (kept entries, [{"kept", "dropped"}])."""
    dropped, conflicts = set(), []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if a["polarity"] == b["polarity"] or id(a) in dropped or id(b) in dropped:
                continue
            ta, tb = _tokens(a["text"]), _tokens(b["text"])
            if ta and tb and len(ta & tb) / len(ta | tb) >= SIMILARITY:
                newer, older = (a, b) if a["last"] >= b["last"] else (b, a)
                dropped.add(id(older))
                conflicts.append({"kept": newer["text"], "dropped": older["text"]})
    return [e for e in entries if id(e) not in dropped], conflicts


def learn(conn):
    """Return {"projects": {name: [pref,...]}, "all": [pref,...]} ordered by strength."""
    items = []
    for r in conn.execute("SELECT t.prompt, t.started_at, s.project, s.cwd FROM tasks t JOIN sessions s "
                          "ON s.id = t.session_id WHERE t.prompt IS NOT NULL"):
        if is_synthetic(r[3]) or r[2] in ("~", "?", None):
            continue
        for sentence in _sentences(r[0]):
            items.append((sentence, r[2], r[1] or ""))
    per_project, general = defaultdict(list), []
    for c in _cluster(items):
        members = c["members"]
        if len(members) < MIN_REPEAT:
            continue
        best = min((m[0] for m in members), key=len)
        projects = {m[1] for m in members}
        entry = {"text": best, "count": len(members), "last": max(m[2] for m in members), "projects": sorted(projects),
                 "polarity": c["polarity"]}
        if len(projects) > 1:
            general.append(entry)
        for p in projects:
            per_project[p].append(entry)
    order = lambda lst: sorted(lst, key=lambda e: (-e["count"], e["last"]), reverse=False)  # noqa: E731
    conflicts, seen = [], set()
    general, found = resolve_conflicts(general)
    for p in list(per_project):  # a project's rules + the all-projects rules must agree with each other
        kept, more = resolve_conflicts(per_project[p] + [g for g in general if g not in per_project[p]])
        per_project[p] = [e for e in per_project[p] if e in kept]
        found += [dict(c, project=p) for c in more]
    for c in found:
        if (c["kept"], c["dropped"]) not in seen:
            seen.add((c["kept"], c["dropped"]))
            conflicts.append(dict(c, project=c.get("project", "All projects")))
    return {"projects": {p: order(v) for p, v in per_project.items()}, "all": order(general), "conflicts": conflicts}


def write(prefs, path=None):
    path = path or os.path.join(tidos_home(), "memory", "LEARNED_PREFERENCES.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["# Learned preferences (generated by TIDOS - edit PREFERENCES.md for your own rules)", "",
             "_Updated %s. Directives you repeated at least %d times._" % (
                 datetime.now(timezone.utc).date().isoformat(), MIN_REPEAT), ""]
    if prefs["all"]:
        lines += ["## All projects"] + ["- %s _(x%d)_" % (e["text"], e["count"]) for e in prefs["all"][:10]] + [""]
    for project in sorted(prefs["projects"]):
        lines += ["## %s" % project] + ["- %s _(x%d)_" % (e["text"], e["count"])
                                         for e in prefs["projects"][project][:10]] + [""]
    if prefs.get("conflicts"):  # not a project section: briefs never serve these lines
        lines += ["## Contradictions resolved (TIDOS kept your most recent instruction)"]
        lines += ["- [%s] kept: \"%s\" | dropped: \"%s\"" % (c["project"], c["kept"], c["dropped"])
                  for c in prefs["conflicts"][:20]] + [""]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return path


def for_project(prefs, project, limit=4):
    chosen, seen = [], set()
    for e in prefs["projects"].get(project, []) + prefs["all"]:
        if e["text"] not in seen:
            seen.add(e["text"])
            chosen.append(e["text"])
    return chosen[:limit]
