#!/usr/bin/env bash
# Installs the Claude Code enterprise agent team globally (all projects) on macOS / Linux / WSL.
# Usage:  bash install.sh [--no-auto-update] [--quiet]
# Env:    CLAUDE_HOME          install target (default ~/.claude)
#         CLAUDE_AGENTS_REPO   git URL the self-updater pulls releases from
#                              (default: this checkout's origin, else the public repo;
#                              point it at your internal mirror in enterprise setups)
set -euo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
STATE="$CLAUDE_HOME/enterprise-agents"
DEFAULT_REPO="https://github.com/thakurdishanttt/claude-code-secure-agents.git"
REMINDER_MARKER="prompt-reminder.txt"
UPDATE_MARKER="self-update"
AUTO_UPDATE=1
QUIET=0
SELF_UPDATE=0
KEEP_BACKUPS=5

for arg in "$@"; do
  case "$arg" in
    --no-auto-update) AUTO_UPDATE=0 ;;
    --quiet) QUIET=1 ;;
    --self-update) SELF_UPDATE=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done
[ "${CLAUDE_AGENTS_AUTO_UPDATE:-1}" = "0" ] && AUTO_UPDATE=0
# A self-update keeps the user's earlier opt-out.
[ "$SELF_UPDATE" = 1 ] && [ -f "$STATE/auto-update-disabled" ] && AUTO_UPDATE=0

say() { [ "$QUIET" = 1 ] || echo "$@"; }

# Back up a file only when it is about to change; keep the newest few backups.
backup() {
  local f="$1" new="${2:-}"
  [ -e "$f" ] || return 0
  if [ -n "$new" ] && cmp -s "$f" "$new"; then return 1; fi
  cp "$f" "$f.bak-$STAMP"
  say "  backup: $f.bak-$STAMP"
  # shellcheck disable=SC2012
  ls -1t "$f".bak-* 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | while read -r old; do rm -f "$old"; done
  return 0
}
SED_HOME="$(printf '%s' "$CLAUDE_HOME" | sed 's/[\\&|]/\\&/g')"
render() { sed "s|__CLAUDE_HOME__|$SED_HOME|g" "$1"; }
# Replace via a temp file + rename so a running script (the self-updater) keeps its old inode.
place() { cp "$1" "$2.new-$$" && mv -f "$2.new-$$" "$2"; }

say "Installing into $CLAUDE_HOME"
mkdir -p "$CLAUDE_HOME"/{agents,commands,standards,hooks} "$STATE"

# 0. Stage everything first so a failure never leaves a half-installed kit.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
FILES=()
for f in "$SRC"/agents/*.md "$SRC"/commands/*.md "$SRC"/standards/*.md \
         "$SRC"/hooks/prompt-reminder.txt "$SRC"/hooks/self-update.sh; do
  [ -f "$f" ] || continue
  if [ -L "$f" ]; then echo "  WARNING: skipping symlink ${f#"$SRC"/}" >&2; continue; fi
  rel="${f#"$SRC"/}"
  FILES+=("$rel")
  mkdir -p "$STAGE/$(dirname "$rel")"
  render "$f" > "$STAGE/$rel"
done
render "$SRC/CLAUDE.global.md" > "$STAGE/CLAUDE.global.md"

# 1. Agents, commands, standards, hook scripts
for rel in "${FILES[@]}"; do
  dest="$CLAUDE_HOME/$rel"
  if [ -e "$dest" ] && cmp -s "$dest" "$STAGE/$rel"; then continue; fi
  backup "$dest" "$STAGE/$rel" || true
  place "$STAGE/$rel" "$dest"
  say "  installed: $rel"
done
chmod +x "$CLAUDE_HOME/hooks/self-update.sh"

# Files a previous version installed but this version dropped: set aside, never silently delete.
MANIFEST="$STATE/manifest.txt"
if [ -f "$MANIFEST" ]; then
  while read -r old; do
    [ -n "$old" ] || continue
    keep=0; for rel in "${FILES[@]}"; do [ "$rel" = "$old" ] && keep=1; done
    if [ "$keep" = 0 ] && [ -f "$CLAUDE_HOME/$old" ]; then
      mv "$CLAUDE_HOME/$old" "$CLAUDE_HOME/$old.removed-$STAMP"
      say "  retired: $old (kept as $old.removed-$STAMP)"
    fi
  done < "$MANIFEST"
fi
printf '%s\n' "${FILES[@]}" > "$MANIFEST"

# 2. Global CLAUDE.md: replace our marked block, or append it
BLOCK_FILE="$STAGE/CLAUDE.global.md"
CLAUDE_MD="$CLAUDE_HOME/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  if grep -q '<!-- BEGIN claude-enterprise-agents -->' "$CLAUDE_MD"; then
    awk -v blockfile="$BLOCK_FILE" '
      /<!-- BEGIN claude-enterprise-agents -->/ { while ((getline line < blockfile) > 0) print line; skip=1; next }
      /<!-- END claude-enterprise-agents -->/ { skip=0; next }
      !skip { print }
    ' "$CLAUDE_MD" > "$STAGE/CLAUDE.md.new"
  else
    { cat "$CLAUDE_MD"; printf '\n'; cat "$BLOCK_FILE"; } > "$STAGE/CLAUDE.md.new"
  fi
  if ! cmp -s "$CLAUDE_MD" "$STAGE/CLAUDE.md.new"; then
    backup "$CLAUDE_MD" "$STAGE/CLAUDE.md.new" || true
    place "$STAGE/CLAUDE.md.new" "$CLAUDE_MD"
    say "  updated: CLAUDE.md"
  fi
else
  cp "$BLOCK_FILE" "$CLAUDE_MD"
  say "  created: CLAUDE.md"
fi

# 3. settings.json: merge UserPromptSubmit (rules) and SessionStart (self-update) hooks
SETTINGS="$CLAUDE_HOME/settings.json"
REMINDER_CMD="cat \"$CLAUDE_HOME/hooks/$REMINDER_MARKER\""
UPDATE_CMD="bash \"$CLAUDE_HOME/hooks/self-update.sh\""
MERGE='
import json, os, sys
p, out, rcmd, rmark, ucmd, umark, auto = sys.argv[1:8]
s = {}
if os.path.exists(p) and open(p, encoding="utf-8").read().strip():
    s = json.load(open(p, encoding="utf-8"))
hooks = s.setdefault("hooks", {})
def has(event, mark):
    return any(mark in h.get("command", "") for e in hooks.get(event, []) for h in e.get("hooks", []))
if not has("UserPromptSubmit", rmark):
    hooks.setdefault("UserPromptSubmit", []).append({"hooks": [{"type": "command", "command": rcmd, "timeout": 10}]})
    print("  added rules hook (UserPromptSubmit)")
if auto == "1" and not has("SessionStart", umark):
    hooks.setdefault("SessionStart", []).append({"matcher": "startup", "hooks": [{"type": "command", "command": ucmd, "async": True, "timeout": 120}]})
    print("  added self-update hook (SessionStart)")
if auto == "0" and has("SessionStart", umark):
    hooks["SessionStart"] = [e for e in hooks["SessionStart"] if not any(umark in h.get("command", "") for h in e.get("hooks", []))]
    if not hooks["SessionStart"]: del hooks["SessionStart"]
    print("  removed self-update hook (auto-update disabled)")
json.dump(s, open(out, "w", encoding="utf-8"), indent=2)
open(out, "a", encoding="utf-8").write("\n")
'
NEW_SETTINGS="$STAGE/settings.json"
if command -v python3 >/dev/null 2>&1; then
  python3 -c "$MERGE" "$SETTINGS" "$NEW_SETTINGS" "$REMINDER_CMD" "$REMINDER_MARKER" "$UPDATE_CMD" "$UPDATE_MARKER" "$AUTO_UPDATE" | while read -r l; do say "$l"; done
elif command -v node >/dev/null 2>&1; then
  node -e '
    const fs=require("fs"); const [p,out,rcmd,rmark,ucmd,umark,auto]=process.argv.slice(1);
    let s={}; if (fs.existsSync(p) && fs.readFileSync(p,"utf8").trim()) s=JSON.parse(fs.readFileSync(p,"utf8"));
    const hooks=s.hooks=s.hooks||{};
    const has=(ev,m)=>(hooks[ev]||[]).some(e=>(e.hooks||[]).some(h=>(h.command||"").includes(m)));
    if(!has("UserPromptSubmit",rmark)){(hooks.UserPromptSubmit=hooks.UserPromptSubmit||[]).push({hooks:[{type:"command",command:rcmd,timeout:10}]});console.log("  added rules hook (UserPromptSubmit)");}
    if(auto==="1"&&!has("SessionStart",umark)){(hooks.SessionStart=hooks.SessionStart||[]).push({matcher:"startup",hooks:[{type:"command",command:ucmd,async:true,timeout:120}]});console.log("  added self-update hook (SessionStart)");}
    if(auto==="0"&&has("SessionStart",umark)){hooks.SessionStart=hooks.SessionStart.filter(e=>!(e.hooks||[]).some(h=>(h.command||"").includes(umark)));if(!hooks.SessionStart.length)delete hooks.SessionStart;console.log("  removed self-update hook (auto-update disabled)");}
    fs.writeFileSync(out, JSON.stringify(s,null,2)+"\n");
  ' "$SETTINGS" "$NEW_SETTINGS" "$REMINDER_CMD" "$REMINDER_MARKER" "$UPDATE_CMD" "$UPDATE_MARKER" "$AUTO_UPDATE" | while read -r l; do say "$l"; done
else
  NEW_SETTINGS=""
  echo "  WARNING: python3/node not found - add the hooks manually (see INTEGRATION.md, section 4)." >&2
fi
if [ -n "$NEW_SETTINGS" ] && { [ ! -f "$SETTINGS" ] || ! cmp -s "$SETTINGS" "$NEW_SETTINGS"; }; then
  backup "$SETTINGS" "$NEW_SETTINGS" || true
  place "$NEW_SETTINGS" "$SETTINGS"
fi

# 4. Version + self-update source
cp "$SRC/VERSION" "$STATE/VERSION"
if [ "$AUTO_UPDATE" = 1 ]; then
  rm -f "$STATE/auto-update-disabled"
  if [ "$SELF_UPDATE" = 0 ] && command -v git >/dev/null 2>&1; then
    REPO="${CLAUDE_AGENTS_REPO:-$(git -C "$SRC" remote get-url origin 2>/dev/null || echo "$DEFAULT_REPO")}"
    if [ -d "$STATE/src/.git" ]; then
      git -C "$STATE/src" remote set-url origin "$REPO"
    elif GIT_TERMINAL_PROMPT=0 git clone --quiet --no-checkout "$REPO" "$STATE/src" 2>/dev/null; then
      say "  self-update source: $REPO"
    else
      echo "  WARNING: could not clone $REPO; auto-update will stay idle until it is reachable." >&2
    fi
  fi
  date +%s > "$STATE/last-check"
else
  touch "$STATE/auto-update-disabled"
  say "  auto-update: disabled"
fi

say ""
say "Done ($(cat "$SRC/VERSION")). Restart Claude Code, then run /agents and /hooks to verify."
