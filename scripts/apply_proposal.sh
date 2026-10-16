#!/usr/bin/env bash
# Apply the bot's proposal patch only if every path it touches is kit content.
# The patch comes from the job Claude ran in, so it is untrusted input here.
# Usage: apply_proposal.sh <kit.patch>
set -euo pipefail
patch="${1:?patch file required}"
[ -f "$patch" ] || { echo "no patch file" >&2; exit 1; }
[ -s "$patch" ] || { echo "empty patch"; exit 0; }

python3 -I - "$patch" <<'EOF'
import re, sys
ALLOWED = ("agents/", "commands/", "standards/")
ALLOWED_FILES = {"hooks/prompt-reminder.txt", "CLAUDE.global.md", "README.md", "INTEGRATION.md", "CHANGELOG.md"}
FORBIDDEN_HEADERS = ("rename from", "rename to", "copy from", "copy to", "old mode", "new mode",
                     "deleted file mode", "GIT binary patch", "Binary files")
bad = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    line = line.rstrip("\n")
    m = re.match(r"^diff --git a/(\S+) b/(\S+)$", line)
    if m:
        a, b = m.groups()
        for p in (a, b):
            if ".." in p.split("/") or p.startswith("/") or not (p.startswith(ALLOWED) or p in ALLOWED_FILES):
                bad.append(f"path not allowed: {p}")
        if a != b:
            bad.append(f"rename/copy not allowed: {a} -> {b}")
    elif line.startswith("new file mode") and not line.endswith(("100644",)):
        bad.append(f"file mode not allowed: {line}")
    elif line.startswith(FORBIDDEN_HEADERS):
        bad.append(f"patch header not allowed: {line}")
if bad:
    print("\n".join(sorted(set(bad))))
    sys.exit(1)
EOF

git apply --check "$patch"
git apply --index "$patch"
echo "applied $(grep -c '^diff --git ' "$patch") file(s) from the proposal"
