#!/usr/bin/env bash
# Structurally synced with script.easymovie/.github/sync-labels.sh. Keep parallel.
#
# Make the repository's labels match the list below, which is the source of truth.
#
#   .github/sync-labels.sh            create or update every listed label
#   .github/sync-labels.sh --prune    also delete labels that are not listed
#
# Labels say what an issue is or what it waits on; its milestone (Next or Later)
# says when it ships. GitHub issue types need an organization account, so the
# bug and enhancement labels carry the type, set by the issue forms.
# Without --prune an unlisted label is only reported: deleting one strips it from
# every issue that carries it.
#
# Dependabot applies dependencies, python and github_actions to its PRs and
# recreates them if missing, so they are listed to survive --prune.

set -euo pipefail

REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

# name|colour|description
LABELS="$(cat <<'EOF'
bug|d73a4a|Something isn't working
enhancement|a2eeef|New feature or request
documentation|0075ca|Improvements or additions to documentation
needs-info|fbca04|Waiting on the reporter for details
needs-upstream|5319e7|Waiting on Kodi or a skin; cannot be fixed in the add-on alone
duplicate|cfd3d7|This issue or pull request already exists
invalid|e4e669|This doesn't seem right
wontfix|ffffff|This will not be worked on
dependencies|0366d6|Pull requests that update a dependency file
python|2b67c6|Pull requests that update python code
github_actions|000000|Pull requests that update GitHub Actions code
EOF
)"

prune=false
case "${1:-}" in
    "") ;;
    --prune) prune=true ;;
    *) echo "usage: sync-labels.sh [--prune]" >&2; exit 2 ;;
esac

while IFS='|' read -r name color description; do
    gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force >/dev/null
    echo "ok       $name"
done <<< "$LABELS"

listed="$(cut -d'|' -f1 <<< "$LABELS")"
gh label list --repo "$REPO" --limit 200 --json name --jq '.[].name' | while IFS= read -r name; do
    grep -qxF "$name" <<< "$listed" && continue
    if $prune; then
        gh label delete "$name" --repo "$REPO" --yes >/dev/null
        echo "deleted  $name"
    else
        echo "unlisted $name (kept; --prune deletes it)"
    fi
done
