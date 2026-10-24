When using Bend:
- run `bend guide` to learn it
- use `LAWS.bend` to keep important rules
- run `bend PROOF.bend` before committing
- parallelize the code whenever possible

Build: bend main.bend -o wp
Check before commit: bend PROOF.bend && python3 live.py --pk 849805 --replay && python3 -m unittest discover -s tests -v
Offline replay/demo: python3 sim_engine.py --pk 849805 [--fetch] [--delay 1] [--serve] [--publish]
Deploy hosted page: cd cloudflare && npx wrangler@4 deploy   (https://bend-winprob.harlanljones.workers.dev)
Publish to it: python3 live.py --publish   (WP_PUSH_URL, WP_PUSH_TOKEN in .env; PUSH_TOKEN is the Worker secret)
Supervised live: bash run_live.sh   (restarts crashes with 5–60 s backoff; exits on clean Final/Ctrl-C)
Evidence: timestamped stdout/stderr in logs/winprob-YYYY-MM-DD.log; per-play results in runs/<gamePk>.csv. Logs include commit and Bend version, never .env values.
