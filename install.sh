#!/usr/bin/env bash
# Installs the Claude Code enterprise agent team globally (all projects) on macOS / Linux / WSL.
# Usage:  bash install.sh
set -euo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
MARKER="prompt-reminder.txt"

backup() { if [ -e "$1" ]; then cp "$1" "$1.bak-$STAMP"; echo "  backup: $1.bak-$STAMP"; fi; }
render() { sed "s|__CLAUDE_HOME__|$CLAUDE_HOME|g" "$1"; }

echo "Installing into $CLAUDE_HOME"
mkdir -p "$CLAUDE_HOME"/{agents,commands,standards,hooks}

# 1. Agents, command, standard, hook text
for f in agents/planner.md agents/researcher.md agents/coder.md agents/reviewer.md \
         agents/cleaner.md commands/build.md standards/ai-security.md hooks/prompt-reminder.txt; do
  backup "$CLAUDE_HOME/$f"
  render "$SRC/$f" > "$CLAUDE_HOME/$f"
  echo "  installed: $f"
done

# 2. Global CLAUDE.md: replace our marked block, or append it
BLOCK_FILE="$(mktemp)"
render "$SRC/CLAUDE.global.md" > "$BLOCK_FILE"
CLAUDE_MD="$CLAUDE_HOME/CLAUDE.md"
if [ -f "$CLAUDE_MD" ]; then
  backup "$CLAUDE_MD"
  if grep -q '<!-- BEGIN claude-enterprise-agents -->' "$CLAUDE_MD"; then
    awk -v blockfile="$BLOCK_FILE" '
      /<!-- BEGIN claude-enterprise-agents -->/ { while ((getline line < blockfile) > 0) print line; skip=1; next }
      /<!-- END claude-enterprise-agents -->/ { skip=0; next }
      !skip { print }
    ' "$CLAUDE_MD" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
  else
    printf '\n' >> "$CLAUDE_MD"; cat "$BLOCK_FILE" >> "$CLAUDE_MD"
  fi
else
  cp "$BLOCK_FILE" "$CLAUDE_MD"
fi
rm -f "$BLOCK_FILE"
echo "  updated: CLAUDE.md"

# 3. settings.json: merge UserPromptSubmit hook
SETTINGS="$CLAUDE_HOME/settings.json"
backup "$SETTINGS"
HOOK_CMD="cat \"$CLAUDE_HOME/hooks/$MARKER\""
MERGE='
import json, os, sys
p, cmd, marker = sys.argv[1], sys.argv[2], sys.argv[3]
s = {}
if os.path.exists(p) and open(p, encoding="utf-8").read().strip():
    s = json.load(open(p, encoding="utf-8"))
ups = s.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
if any(marker in h.get("command", "") for e in ups for h in e.get("hooks", [])):
    print("  hook already present in settings.json, skipped")
else:
    ups.append({"hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
    json.dump(s, open(p, "w", encoding="utf-8"), indent=2)
    print("  added hook to settings.json")
'
if command -v python3 >/dev/null 2>&1; then
  python3 -c "$MERGE" "$SETTINGS" "$HOOK_CMD" "$MARKER"
elif command -v node >/dev/null 2>&1; then
  node -e '
    const fs=require("fs"); const [p,cmd,marker]=process.argv.slice(1);
    let s={}; if (fs.existsSync(p) && fs.readFileSync(p,"utf8").trim()) s=JSON.parse(fs.readFileSync(p,"utf8"));
    s.hooks=s.hooks||{}; const ups=s.hooks.UserPromptSubmit=s.hooks.UserPromptSubmit||[];
    if (ups.some(e=>(e.hooks||[]).some(h=>(h.command||"").includes(marker)))) console.log("  hook already present in settings.json, skipped");
    else { ups.push({hooks:[{type:"command",command:cmd,timeout:10}]}); fs.writeFileSync(p, JSON.stringify(s,null,2)+"\n"); console.log("  added hook to settings.json"); }
  ' "$SETTINGS" "$HOOK_CMD" "$MARKER"
else
  echo "  WARNING: python3/node not found - add the hook manually (see INTEGRATION.md, step 4)."
fi

echo
echo "Done. Restart Claude Code, then run /agents and /hooks to verify."
