#!/usr/bin/env bash
# Thin wrapper around `hugo server` that ensures a recent Go is on PATH.
#
# Hextra ships as a Hugo Module. Its go.mod sets `go 1.24.2`, which older
# system Go binaries (e.g. /usr/local/go pinned at 1.19) reject as invalid:
#   invalid go version '1.24.2': must match format 1.23
# Brew Go is recent. This wrapper prepends brew's bin dir so it wins.
#
# If your modern Go isn't at /usr/local/bin (Apple Silicon brew is at
# /opt/homebrew/bin, linuxbrew is at /home/linuxbrew/.linuxbrew/bin, asdf
# shims live elsewhere again), edit BREW_BIN below.
set -euo pipefail
BREW_BIN="/usr/local/bin"
[[ -x "$BREW_BIN/go" ]] && export PATH="$BREW_BIN:$PATH"
exec hugo server "$@"
