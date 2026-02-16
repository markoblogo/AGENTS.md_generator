#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/release.sh v0.1.2 A
#   ./scripts/release.sh v0.1.2 B
#   ./scripts/release.sh v0.1.2 C
#   ./scripts/release.sh A

REPO="markoblogo/AGENTS.md_generator"
VERSION="${1:-}"
MODE="${2:-A}"
PYTHON_BIN=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release.sh vX.Y.Z A|B|C
  ./scripts/release.sh A|B|C

Examples:
  ./scripts/release.sh v0.1.2 A
  ./scripts/release.sh v0.2.0 B
  ./scripts/release.sh A
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

ok() {
  echo "OK: $*"
}

warn() {
  echo "WARN: $*" >&2
}

confirm() {
  local prompt="${1}"
  local ans
  read -r -p "${prompt} [y/N] " ans
  case "${ans}" in
    y|Y) return 0 ;;
    *) die "Cancelled." ;;
  esac
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

pick_python() {
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    return
  fi
  die "Missing command: python (or python3)"
}

require_clean_git_tree() {
  git diff --quiet || die "Working tree has unstaged changes."
  git diff --cached --quiet || die "Index has staged changes."
  if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    die "Working tree has untracked files."
  fi
}

require_no_existing_tag() {
  if git rev-parse -q --verify "refs/tags/${VERSION}" >/dev/null 2>&1; then
    die "Tag already exists locally: ${VERSION}"
  fi
  if git ls-remote --exit-code --tags origin "refs/tags/${VERSION}" >/dev/null 2>&1; then
    die "Tag already exists on origin: ${VERSION}"
  fi
}

is_mode() {
  case "${1:-}" in
    A|B|C) return 0 ;;
    *) return 1 ;;
  esac
}

is_version() {
  [[ "${1:-}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

bump_patch() {
  local v="${1:-}"
  if [[ "${v}" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    local major="${BASH_REMATCH[1]}"
    local minor="${BASH_REMATCH[2]}"
    local patch="${BASH_REMATCH[3]}"
    echo "v${major}.${minor}.$((patch + 1))"
    return 0
  fi
  return 1
}

suggest_next_version() {
  local latest=""
  latest="$(git tag --list 'v*' --sort=-v:refname | head -n 1 || true)"
  if [ -z "${latest}" ]; then
    latest="$(ls RELEASES 2>/dev/null | sed -n 's/^\(v[0-9]\+\.[0-9]\+\.[0-9]\+\)\.md$/\1/p' | sort -V | tail -n 1 || true)"
  fi
  if [ -n "${latest}" ] && bump_patch "${latest}" >/dev/null 2>&1; then
    bump_patch "${latest}"
  else
    echo "v0.1.0"
  fi
}

pick_version_if_missing() {
  if [ -n "${VERSION}" ]; then
    return
  fi
  local suggested
  suggested="$(suggest_next_version)"
  echo "Suggested next version: ${suggested}"
  local ans
  read -r -p "Use suggested version ${suggested}? [Y/n] " ans
  case "${ans}" in
    ""|y|Y) VERSION="${suggested}" ;;
    *)
      read -r -p "Enter version (vX.Y.Z): " VERSION
      ;;
  esac
  is_version "${VERSION}" || die "Invalid version format: ${VERSION} (expected vX.Y.Z)"
}

require_notes_headings() {
  local file="${1}"
  local headings=(
    "## What’s inside"
    "## Safety model"
    "## Quickstart"
    "## Known limitations"
  )
  local missing=0
  for h in "${headings[@]}"; do
    if ! grep -Fq "${h}" "${file}"; then
      warn "Missing heading in ${file}: ${h}"
      missing=1
    fi
  done
  if [ "${missing}" -ne 0 ]; then
    die "Release notes sanity check failed."
  fi
}

run_checks() {
  echo "== Running checks =="
  "${PYTHON_BIN}" -m agentsgen._smoke
  if command -v pytest >/dev/null 2>&1; then
    pytest -q
  else
    warn "pytest not found; skipping pytest -q."
  fi
  ok "Checks completed."
}

gh_ready() {
  command -v gh >/dev/null 2>&1 || return 1
  gh auth status -h github.com >/dev/null 2>&1 || return 1
  return 0
}

main() {
  if [ $# -eq 0 ]; then
    usage
    exit 1
  fi

  if [ "${VERSION}" = "-h" ] || [ "${VERSION}" = "--help" ]; then
    usage
    exit 1
  fi

  # Support shorthand invocation: ./scripts/release.sh A|B|C
  if is_mode "${VERSION}" && [ -z "${2:-}" ]; then
    MODE="${VERSION}"
    VERSION=""
  fi
  if is_mode "${MODE}" && [ -z "${VERSION}" ]; then
    :
  elif [ -n "${VERSION}" ] && [ -z "${MODE:-}" ]; then
    MODE="A"
  fi
  is_mode "${MODE}" || { usage; die "Mode must be A, B, or C."; }

  if [ -n "${VERSION}" ]; then
    is_version "${VERSION}" || die "Invalid version format: ${VERSION} (expected vX.Y.Z)"
  fi
  pick_version_if_missing

  require_cmd git
  pick_python

  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Not inside a git repository."

  local notes_file="RELEASES/${VERSION}.md"
  [ -f "${notes_file}" ] || die "Release notes file not found: ${notes_file}"
  require_notes_headings "${notes_file}"

  echo "== Pre-flight =="
  echo "Version: ${VERSION}"
  echo "Mode: ${MODE}"
  echo "Notes: ${notes_file}"
  require_clean_git_tree
  ok "Git tree is clean."
  require_no_existing_tag
  ok "Tag is available locally and on origin."

  confirm "Run release checks now (smoke + pytest if available)?"
  run_checks

  confirm "Create annotated tag ${VERSION}?"
  git tag -a "${VERSION}" -m "${VERSION}"
  ok "Tag created: ${VERSION}"

  confirm "Push tag ${VERSION} to origin?"
  git push origin "${VERSION}"
  ok "Tag pushed: ${VERSION}"

  echo "== GitHub Release =="
  if gh_ready; then
    confirm "Create GitHub Release ${VERSION} with gh now?"
    gh release create "${VERSION}" \
      --repo "${REPO}" \
      --verify-tag \
      --title "${VERSION}" \
      --notes-file "${notes_file}"
    ok "GitHub Release created."
  else
    warn "gh is missing or not authenticated. Skipping GitHub Release creation."
    echo "Run manually:"
    echo "  gh auth login -h github.com -p https -s repo"
    echo "  gh release create ${VERSION} \\"
    echo "    --repo ${REPO} \\"
    echo "    --verify-tag \\"
    echo "    --title \"${VERSION}\" \\"
    echo "    --notes-file ${notes_file}"
  fi

  ok "Done."
}

main "$@"
