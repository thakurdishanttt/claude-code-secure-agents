#!/usr/bin/env bash
# Create the GitHub release for the VERSION at a given main commit, if it does
# not exist yet. Idempotent: safe to call from every run and on every push.
# Usage: release.sh <commit-sha>     (needs GH_TOKEN with contents:write)
set -euo pipefail
sha="${1:?commit sha required}"
git cat-file -e "$sha^{commit}"
version="$(git show "$sha:VERSION" | tr -d '[:space:]')"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "bad VERSION '$version' at $sha" >&2; exit 1; }
tag="v$version"

if gh release view "$tag" >/dev/null 2>&1; then
  echo "release $tag already exists"
  exit 0
fi
# Only main's history may be released.
git fetch -q origin main 2>/dev/null || true
if ! git merge-base --is-ancestor "$sha" origin/main; then
  echo "commit $sha is not on main; not releasing" >&2
  exit 1
fi

notes="$(mktemp)"
git show "$sha:CHANGELOG.md" 2>/dev/null \
  | awk -v v="$version" 'index($0, "## v" v " ")==1 || $0=="## v" v {f=1; next} /^## /{if(f) exit} f' > "$notes" || true
[ -s "$notes" ] || echo "Release $tag" > "$notes"
gh release create "$tag" --target "$sha" --title "$tag" --notes-file "$notes"
echo "released $tag at $sha"
