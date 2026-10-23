#!/usr/bin/env bash
# Restart a crashed publisher with bounded backoff. A clean Final/Ctrl-C
# exit (status 0) stops the supervisor instead of starting a new game loop.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.bend/bin:$PATH"
export PYTHONUNBUFFERED=1

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
