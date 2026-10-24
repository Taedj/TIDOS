#!/usr/bin/env bash
# Scenario tests for scripts/update.sh and scripts/update.ps1 (local fake upstream, no network).
# Usage: bash tests/update_gate_scenarios.sh <sh|ps1>   (ps1 needs Windows PowerShell + cygpath)
set -u
KIND="$1"
SRC="$(cd "$(dirname "$0")/../scripts" && pwd)"
W=$(cygpath -m "$(mktemp -d)")
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.com GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.com
pass=0; failn=0
ok()  { echo "  PASS: $1"; pass=$((pass+1)); }
bad() { echo "  FAIL: $1"; failn=$((failn+1)); }

CHANNEL=main   # scenario defaults: follow main and apply (A-G); H-J test the release channel
APPLY=1
run_update() { # $1 = cwd, $2 = optional dir arg
  local sh_args=(--channel "$CHANNEL") ps_args=(-Channel "$CHANNEL")
  [ "$APPLY" = 1 ] && sh_args+=(--apply) && ps_args+=(-Apply)
  if [ "$KIND" = sh ]; then (cd "$1" && bash "$SRC/update.sh" ${2:+"$2"} "${sh_args[@]}") >"$W/out.txt" 2>&1
  else (cd "$1" && powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$SRC/update.ps1")" ${2:+-TidosDir "$2"} "${ps_args[@]}") >"$W/out.txt" 2>&1
  fi
  echo $?
}

# --- fake upstream "GitHub" with two commits --------------------------------
git init -q --bare "$W/upstream.git"
git clone -q "$W/upstream.git" "$W/seed" 2>/dev/null
cd "$W/seed" && git checkout -q -b main
mkdir -p core config memory personas && touch personas/.gitkeep && echo v1 > TIDSTART.md && echo k > core/kernel.md && echo c > config/framework.md
echo "upstream lesson" > memory/LESSONS.md && git add -A && git commit -qm v1 && git push -q origin main
export TIDOS_UPDATE_TEST_URL="$W/upstream.git"
fresh_clone() { git clone -q -b main "$W/upstream.git" "$1" 2>/dev/null; git -C "$1" remote set-url origin "$W/upstream.git"; }
push_v2() { cd "$W/seed" && echo "v$1" > TIDSTART.md && git commit -qam "v$1" && git push -q origin main; }

echo "== [$KIND] A: project root with copied TIDSTART.md is NOT touched"
mkdir -p "$W/proj" && cd "$W/proj" && git init -q && echo app > app.txt && cp "$W/seed/TIDSTART.md" . && git add -A && git commit -qm app
git remote add origin https://example.com/my/project.git
rc=$(run_update "$W/proj")
[ "$rc" = 2 ] && [ "$(git -C "$W/proj" remote get-url origin)" = https://example.com/my/project.git ] && [ -f "$W/proj/app.txt" ] \
  && ok "refused (rc=2), project origin + files intact" || { bad "project touched (rc=$rc)"; cat "$W/out.txt"; }

echo "== [$KIND] B: fork origin is refused, not rewritten"
fresh_clone "$W/fork" && git -C "$W/fork" remote set-url origin https://github.com/someone/TIDOS-fork.git
rc=$(run_update "$W" "$W/fork")
[ "$rc" = 2 ] && [ "$(git -C "$W/fork" remote get-url origin)" = https://github.com/someone/TIDOS-fork.git ] \
  && ok "refused, fork origin kept" || { bad "fork rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] C/D/E: normal update keeps memory, untracked personas; dirty system file blocks update"
fresh_clone "$W/client"
push_v2 2
echo "my local lesson" > "$W/client/memory/LESSONS.md"
echo "# generated" > "$W/client/personas/tidosrust.md"
echo "dev edit" > "$W/client/core/kernel.md"
rc=$(run_update "$W" "$W/client")
[ "$rc" = 0 ] && grep -q "dev edit" "$W/client/core/kernel.md" && grep -q "update skipped" "$W/out.txt" \
  && ok "dirty system file protected, update skipped" || { bad "dirty rc=$rc"; cat "$W/out.txt"; }
git -C "$W/client" checkout -q core/kernel.md
rc=$(run_update "$W" "$W/client")
[ "$rc" = 0 ] && grep -q v2 "$W/client/TIDSTART.md" && ok "updated to v2" || { bad "update rc=$rc"; cat "$W/out.txt"; }
grep -q "my local lesson" "$W/client/memory/LESSONS.md" && ok "memory preserved" || bad "memory lost"
[ -f "$W/client/personas/tidosrust.md" ] && ok "untracked generated persona preserved" || bad "persona deleted"

echo "== [$KIND] F: unpushed local commit blocks update"
cd "$W/client" && echo "local feature" > core/feature.md && git add -A && git commit -qm local
push_v2 3
rc=$(run_update "$W" "$W/client")
[ "$rc" = 0 ] && git -C "$W/client" log --oneline | grep -q local && grep -q "are not in" "$W/out.txt" \
  && ok "unpushed commit protected" || { bad "ahead rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] G: .tidos local copy (no .git) inside a project repo"
mkdir -p "$W/proj2" && cd "$W/proj2" && git init -q && echo app > app.txt && git add -A && git commit -qm app
git remote add origin https://example.com/my/project2.git
mkdir .tidos && cp -r "$W/seed/core" "$W/seed/config" "$W/seed/TIDSTART.md" .tidos/ && echo v1 > .tidos/TIDSTART.md
rc=$(run_update "$W/proj2")
[ "$rc" = 0 ] && grep -q v3 "$W/proj2/.tidos/TIDSTART.md" && [ "$(git -C "$W/proj2" remote get-url origin)" = https://example.com/my/project2.git ] \
  && [ -f "$W/proj2/app.txt" ] && [ "$(git -C "$W/proj2" log --oneline | wc -l)" = 1 ] \
  && ok ".tidos updated, parent project untouched" || { bad "local copy rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] H: release channel reports, installs only with approval"
cd "$W/seed" && git tag -a v1.0.0 -m "release 1" && git push -q origin v1.0.0
git clone -q "$W/upstream.git" "$W/rel" 2>/dev/null && git -C "$W/rel" checkout -q --detach v1.0.0
push_v2 4
cd "$W/seed" && git tag -a v1.1.0 -m "release 1.1" && git push -q origin v1.1.0
push_v2 5                                   # newer main commit that is NOT released
CHANNEL=release; APPLY=0
rc=$(run_update "$W" "$W/rel")
[ "$rc" = 0 ] && grep -q "Update available" "$W/out.txt" && grep -q "NOT installed" "$W/out.txt" && grep -q v3 "$W/rel/TIDSTART.md"   && ok "update reported, nothing installed without approval" || { bad "report rc=$rc"; cat "$W/out.txt"; }
APPLY=1
rc=$(run_update "$W" "$W/rel")
[ "$rc" = 0 ] && grep -q v4 "$W/rel/TIDSTART.md" && ok "approved: installed release v1.1.0 (not unreleased main)"   || { bad "apply rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] I: TIDOS_REQUIRE_SIGNED refuses an unsigned release"
cd "$W/seed" && git tag -a v1.2.0 -m "release 1.2" && git push -q origin v1.2.0
rc=$(TIDOS_REQUIRE_SIGNED=1 run_update "$W" "$W/rel")
[ "$rc" = 2 ] && grep -q "unsigned" "$W/out.txt" && grep -q v4 "$W/rel/TIDSTART.md"   && ok "unsigned release refused" || { bad "signed rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] J: a checkout newer than the latest release is never moved backwards"
push_v2 6                                   # main moves past the latest release v1.2.0
fresh_clone "$W/newer"
rc=$(run_update "$W" "$W/newer")
[ "$rc" = 0 ] && grep -q "already contains" "$W/out.txt" && grep -q v6 "$W/newer/TIDSTART.md"   && ok "no downgrade" || { bad "downgrade rc=$rc"; cat "$W/out.txt"; }

echo "== [$KIND] result: $pass passed, $failn failed"
rm -rf "$W"
[ "$failn" = 0 ]
