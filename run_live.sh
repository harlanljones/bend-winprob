#!/usr/bin/env bash
# Restart a crashed publisher with bounded backoff. A clean Final/Ctrl-C
# exit (status 0) stops the supervisor instead of starting a new game loop.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.bend/bin:$PATH"
export PYTHONUNBUFFERED=1
umask 077
mkdir -p logs
LOG_FILE="logs/winprob-$(date +%Y-%m-%d).log"
# Keep the console stream and an append-only dated file. Every line gets a
# local timestamp; the per-play CSV remains the machine-readable result.
exec > >(awk '{ print strftime("%Y-%m-%dT%H:%M:%S%z"), $0; fflush(); }' | tee -a "$LOG_FILE") 2>&1
printf '=== supervisor start pid=%s commit=%s bend=%s args=%s ===\n' \
  "$$" "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
  "$(bend version 2>/dev/null || echo unknown)" "$*"

backoff=5
while true; do
  python3 live.py --publish "$@"
  rc=$?
  if [ "$rc" -eq 0 ]; then
    exit 0
  fi
  printf '%s live.py exited %s; restarting in %ss\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$rc" "$backoff" >&2
  sleep "$backoff"
  if [ "$backoff" -lt 60 ]; then
    backoff=$((backoff * 2))
    if [ "$backoff" -gt 60 ]; then backoff=60; fi
  fi
done
