#!/usr/bin/env bash
# Self-updater for the Claude Code enterprise agent kit (macOS / Linux / WSL).
# Runs from a SessionStart hook in the background. At most once per interval it
# fetches release tags from the configured repo and, if a newer released
# version exists, re-runs the installer from that tag. It never blocks or
# fails a Claude Code session: every error path exits 0 and is logged.
#
# Opt out:  export CLAUDE_AGENTS_AUTO_UPDATE=0   (or create the file
#           __CLAUDE_HOME__/enterprise-agents/auto-update-disabled)
# Options:  CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS (default 24)
#           CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS=1 (only install GPG/SSH-signed tags)
set -u

# Everything runs inside main() and the file ends with exit, so bash has parsed the
# whole script before the installer replaces this file on disk.
main() {

  CLAUDE_HOME="__CLAUDE_HOME__"
  STATE="$CLAUDE_HOME/enterprise-agents"
  SRC="$STATE/src"
  LOG="$STATE/update.log"
  LOCK="$STATE/update.lock"

  log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG" 2>/dev/null || true; }

  [ "${CLAUDE_AGENTS_AUTO_UPDATE:-1}" = "0" ] && exit 0
  [ -f "$STATE/auto-update-disabled" ] && exit 0
  [ -d "$SRC/.git" ] || exit 0
  command -v git >/dev/null 2>&1 || exit 0

  interval_h="${CLAUDE_AGENTS_UPDATE_INTERVAL_HOURS:-24}"
  case "$interval_h" in ''|*[!0-9]*) interval_h=24 ;; esac
  now="$(date +%s)"
  last="$(cat "$STATE/last-check" 2>/dev/null || echo 0)"
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  [ $((now - last)) -lt $((interval_h * 3600)) ] && exit 0

  # Single instance; clear a lock left by a crashed run after an hour.
  if ! mkdir "$LOCK" 2>/dev/null; then
    lock_age=$(( now - $(stat -c %Y "$LOCK" 2>/dev/null || stat -f %m "$LOCK" 2>/dev/null || echo "$now") ))
    [ "$lock_age" -gt 3600 ] && rmdir "$LOCK" 2>/dev/null
    exit 0
  fi
  trap 'rmdir "$LOCK" 2>/dev/null' EXIT
  echo "$now" > "$STATE/last-check"

  # Keep the log small.
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 200000 ]; then tail -n 200 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"; fi

  export GIT_TERMINAL_PROMPT=0
  G() { git -C "$SRC" -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=30 "$@"; }

  # Branch first, then tags without '+': a tag that was moved upstream is refused
  # (the rest still arrive), so a tampered tag can never replace a known one.
  if ! G fetch --quiet --no-tags origin '+refs/heads/main:refs/remotes/origin/main' >/dev/null 2>>"$LOG"; then
    fails=$(( $(cat "$STATE/fetch-failures" 2>/dev/null || echo 0) + 1 ))
    echo "$fails" > "$STATE/fetch-failures"
    log "fetch failed ($fails in a row; offline or repo unreachable); will retry next interval"
    exit 0
  fi
  rm -f "$STATE/fetch-failures"
  if ! G fetch --quiet --no-tags origin 'refs/tags/v*:refs/tags/v*' >/dev/null 2>>"$LOG"; then
    log "warning: some release tags were rejected (moved upstream?); using the tags that verify"
  fi

  installed="$(cat "$STATE/VERSION" 2>/dev/null || echo 0.0.0)"
  latest=""
  target=""
  # Newest first; take the first release that passes every check.
  for tag in $(G tag -l 'v[0-9]*' --sort=-v:refname); do
    v="${tag#v}"
    case "$v" in *[!0-9.]*|'') continue ;; esac
    [ "$v" = "$installed" ] && break
    [ "$(printf '%s\n%s\n' "$installed" "$v" | sort -V | tail -n 1)" = "$installed" ] && break  # never downgrade
    if ! G merge-base --is-ancestor "$tag^{commit}" origin/main 2>/dev/null; then
      log "tag $tag is not on origin/main; skipping"; continue
    fi
    if [ "$(G show "$tag:VERSION" 2>/dev/null | tr -d '[:space:]')" != "$v" ]; then
      log "tag $tag does not contain VERSION $v; skipping"; continue
    fi
    if [ "${CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS:-0}" = "1" ] && ! G verify-tag "$tag" >/dev/null 2>&1; then
      log "tag $tag has no valid signature; skipping (CLAUDE_AGENTS_REQUIRE_SIGNED_TAGS=1)"; continue
    fi
    latest="$tag"; target="$v"; break
  done
  [ -n "$latest" ] || exit 0

  if ! G -c advice.detachedHead=false checkout --quiet --force "$latest" 2>>"$LOG"; then
    log "checkout of $latest failed"
    exit 0
  fi
  if CLAUDE_HOME="$CLAUDE_HOME" bash "$SRC/install.sh" --quiet --self-update >> "$LOG" 2>&1; then
    log "updated $installed -> $target (takes effect in the next Claude Code session)"
  else
    log "installer for $latest failed; previous version left in place"
  fi
}
main "$@"
exit 0
