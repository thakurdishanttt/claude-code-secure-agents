#!/usr/bin/env bash
# Run after every Claude step in the auto-update `propose` job, from the pinned
# read-only copy in $TRUSTED. Expected hashes arrive as step outputs (EXPECT_*),
# which the bot cannot alter. Fails if the bot tampered with the guardrails,
# git metadata or watcher state, then runs the pinned validator in bot mode.
set -euo pipefail
: "${TRUSTED:?}" "${RUNNER_TEMP:?}" "${EXPECT_TRUSTED:?}" "${EXPECT_GITMETA:?}" "${EXPECT_GITCONFIG:?}"

# 1. .git/config first, by file hash, before ANY git command could act on it.
if [ "$(sha256sum < .git/config | cut -c1-64)" != "$EXPECT_GITCONFIG" ]; then
  echo "FAIL  .git/config was modified during the bot run; aborting before running git"
  exit 1
fi
status=0
# 2. The manifest itself, then every pinned file against it.
if [ "$(sha256sum < "$RUNNER_TEMP/trusted.sha256" | cut -c1-64)" != "$EXPECT_TRUSTED" ]; then
  echo "FAIL  guardrail manifest was modified"
  exit 1
fi
if ! ( cd "$TRUSTED" && sha256sum --quiet -c "$RUNNER_TEMP/trusted.sha256" ); then
  echo "FAIL  pinned guardrails were modified during the bot run"
  status=1
fi
if [ -n "$(find "$TRUSTED" -newer "$RUNNER_TEMP/trusted.sha256" -print -quit 2>/dev/null)" ]; then
  echo "FAIL  files were added under the pinned guardrail directory"
  status=1
fi
# 3. Git hooks and local config.
if [ "$({ git config --local --list; ls -la .git/hooks; } | sha256sum | cut -c1-64)" != "$EXPECT_GITMETA" ]; then
  echo "FAIL  .git/hooks or local git config were modified during the bot run"
  status=1
fi
# 4. Watcher state.
if [ -f "$RUNNER_TEMP/state.sha256" ] && ! ( cd "$STATE_OUT" && sha256sum --quiet -c "$RUNNER_TEMP/state.sha256" ); then
  echo "FAIL  watcher state was modified during the bot run"
  status=1
fi
# 5. The validator, from the pinned copy.
python3 "$TRUSTED/scripts/validate.py" --root . --base origin/main --bot || status=1
exit "$status"
