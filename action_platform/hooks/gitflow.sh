#!/usr/bin/env bash
# Git-flow rules. Source it for the functions, or run:
#   gitflow.sh branch <name>              branch name is allowed
#   gitflow.sh commit-msg <file|message>  message follows Conventional Commits
#   gitflow.sh target <head> <base>       head may merge into base
#   gitflow.sh protect <branch>           direct commits on this branch are refused
set -euo pipefail

AP_KINDS="${AP_KINDS:-feature|bugfix|hotfix|release|support|chore|docs|refactor|test|ci|perf}"
AP_TYPES="${AP_TYPES:-feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert}"
AP_PROTECTED="${AP_PROTECTED:-main|master|develop}"

gitflow_kind() {
  printf '%s' "$1" | sed -n -E "s#^(${AP_KINDS})/.*#\\1#p"
}

gitflow_branch() {
  local name="$1"
  if printf '%s' "$name" | grep -Eq "^(${AP_PROTECTED})$"; then return 0; fi
  if printf '%s' "$name" | grep -Eq "^(${AP_KINDS})/[A-Za-z0-9][A-Za-z0-9._-]*$"; then return 0; fi
  echo "::error::branch '$name' is not git-flow: use <kind>/<code>[-slug], kind in ${AP_KINDS//|/, }" >&2
  return 1
}

gitflow_commit_msg() {
  local msg="$1"
  [ -f "$msg" ] && msg=$(head -1 "$msg")
  printf '%s' "$msg" | grep -Eq '^(Merge |Revert )' && return 0
  if printf '%s' "$msg" | grep -Eq "^(${AP_TYPES})(\([a-z0-9._/-]+\))?!?: .+"; then return 0; fi
  echo "::error::not a conventional commit: '$msg' — use type(scope): description, type in ${AP_TYPES//|/, }" >&2
  return 1
}

gitflow_current_branch() {
  git symbolic-ref --short -q HEAD 2>/dev/null || git rev-parse --abbrev-ref HEAD
}

gitflow_protect() {
  local branch="$1" msg="${2:-}"
  printf '%s' "$branch" | grep -Eq "^(${AP_PROTECTED})$" || return 0
  printf '%s' "$msg" | grep -Eq '^(chore\(release\): |chore\(platform\): |chore: bootstrap)' && return 0
  git rev-parse -q --verify HEAD >/dev/null 2>&1 || return 0
  echo "::error::direct commits on '$branch' are not allowed — start a branch: action-platform branch feature <code>" >&2
  return 1
}

gitflow_target() {
  local head="$1" base="$2" kind
  kind=$(gitflow_kind "$head")
  local default="${AP_DEFAULT_BRANCH:-main}"
  local has_develop="${AP_HAS_DEVELOP:-true}"
  local allowed=""
  case "$kind" in
    feature|bugfix|chore|docs|refactor|test|ci|perf)
      if [ "$has_develop" = "true" ]; then allowed="develop"; else allowed="$default"; fi ;;
    release|hotfix) allowed="$default|main|master|develop" ;;
    support) allowed="" ;;
    "")
      case "$head" in
        develop) allowed="$default|main|master" ;;
        *) allowed="" ;;
      esac ;;
  esac
  if [ -n "$allowed" ] && printf '%s' "$base" | grep -Eq "^(${allowed})$"; then return 0; fi
  echo "::error::'$head' may not merge into '$base' (allowed: ${allowed:-none}) — git-flow: feature/bugfix → develop, release/hotfix → main + develop" >&2
  return 1
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    branch)     gitflow_branch "$@" ;;
    commit-msg) gitflow_commit_msg "$@" ;;
    target)     gitflow_target "$@" ;;
    protect)    gitflow_protect "$@" ;;
    *) echo "usage: gitflow.sh branch|commit-msg|target|protect ..." >&2; exit 2 ;;
  esac
fi
