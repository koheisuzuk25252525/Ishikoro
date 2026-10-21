#!/bin/bash
# Called by the user's LaunchAgent every minute; never discard local work.
set -eu
export GIT_TERMINAL_PROMPT=0
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
repo="${1:-$HOME/Developer/Ishikoro}"
lock="${2:-$HOME/Library/Application Support/IshikoroSync/update.lock}"
if ! mkdir "$lock" 2>/dev/null; then exit 0; fi
trap 'rmdir "$lock"' EXIT
log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
if [ ! -d "$repo/.git" ]; then log "Missing checkout: $repo"; exit 1; fi
cd "$repo"
if [ "$(git symbolic-ref --quiet --short HEAD || true)" != main ]; then
    log 'Skipped: current branch is not main.'; exit 0
fi
if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
    log 'Skipped: local changes exist. Nothing was overwritten.'; exit 0
fi
# Fetch only the application branch. An access failure is reported in the log.
git fetch --quiet origin refs/heads/main:refs/remotes/origin/main
before="$(git rev-parse HEAD)"
after="$(git rev-parse refs/remotes/origin/main)"
if [ "$before" = "$after" ]; then exit 0; fi
if ! git merge-base --is-ancestor "$before" "$after"; then
    log 'Skipped: local history has diverged. Nothing was overwritten.'; exit 0
fi
# merge also checks for edits made while fetch was running.
git merge --ff-only --no-edit refs/remotes/origin/main
log "Updated to $(git rev-parse --short HEAD). Run in Xcode to rebuild."
