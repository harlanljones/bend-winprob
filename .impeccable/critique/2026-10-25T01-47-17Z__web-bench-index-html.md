---
target: bench page readability
total_score: 23
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/home/harlan/dev/bend-winprob/web/bench/index.html"
target_fingerprint: "sha256:272ceac5db6f8ef603f00867c83a5983d93adb04036eda79c44d4007d9ef104c"
target_path: /home/harlan/dev/bend-winprob/web/bench/index.html
timestamp: 2026-10-25T01-47-17Z
slug: web-bench-index-html
---
Method: dual-agent (A: CritiqueBenchA · B: CritiqueBenchB). Focus: readability.

## Design Health Score (Read)
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 2 | Only verdicts say Loading…; current run marked only by bold link |
| 2 | Match System / Real World | 3 | "negative favors Bend" inverts higher-is-better; "Their Brier" vague |
| 3 | User Control and Freedom | 2 | No way back up; 2025 Method at y≈84,586 |
| 4 | Consistency and Standards | 3 | Scores Bend Brier 0.1651 vs Head to head 0.1640 unexplained; calibration MLB points filled vs open on main page |
| 5 | Error Prevention | 2 | Any ?run=NNNN accepted; missing year renders broken lede |
| 6 | Recognition Rather Than Recall | 2 | No sticky table headers; Δ sign rule only in captions; Δ off-screen on phone |
| 7 | Flexibility and Efficiency | 2 | No sort/filter; games not linked to ?pk= replay |
| 8 | Aesthetic and Minimalist Design | 3 | Verdict sentences duplicate the table; 16 identical chips; small tables stretched to 1196px |
| 9 | Error Recovery | 1 | ?run=2024 lede garbles ("…ended. Benchmark data unavailable. games drawn…"), no pointer to valid runs |
| 10 | Help and Documentation | 3 | Method thorough; "The model" is one 115-word paragraph of percentages |
| **Total** | | **23/40** | **Acceptable** |

## Design Specificity Verdict
LLM: authored skin, generic structure — six repeats of heading/caption/full-width table; the result is never stated as a standings line.
Deterministic: CLI 1 (cream-palette, false positive: pinned stock). Browser overlay 13 at 1440 / 6 at 390: cramped-padding 3 (section h2 3px), tiny-text (Pele 10px axis), line-length 8 (cal caption ~118 cpl, notes 89–95), straggler 1, cream-palette. Contrast: no failures; lowest 5.22 teal on tint. All six tables overflow at 390.

## Priority Issues
- [P1] On phone every comparison table hides Δ and Verdict off-screen (Head to head 1165px in 366px; chip at x=1078), no scroll cue, first-column names wrap 2–3 lines. Fix: ≤720px put Δ (CI) and Verdict after the name or stack rows; sticky first column; nowrap. Command: adapt.
- [P1] Verdict not findable at a glance: 11px outlined chip, "Clear win" looks like "No clear difference", chip wraps in table; lede states no result. Fix: lede-level result line from existing numbers; filled stamp for clear win/loss, 12–13px, nowrap; trim duplicate sentence numbers. Command: clarify, typeset.
- [P1] Every game swamps the page (2025: 85,727px tall, Method at 84,586px). Fix: summary first, rows in <details> (per month), sticky thead, hide all-zero Unscored. Command: distill, layout.
- [P2] Scores table appears to contradict Head to head (unpaired plays). Fix: caption opens "Not paired: each row covers different plays…". Command: clarify.
- [P2] Calibration figure 1196×320 flattens the diagonal; 10px ticks; Bend/MLB differ by hue only (2.29:1). Fix: near-square plot ~520px, MLB open points as on Figure 1, 12px ticks. Command: layout, typeset.

## Persona Red Flags
- Baseball-analytics reader: decodes "Bend lower in 54.1% of 10,000 resamples"; 0.1651 vs 0.1642 contradiction; "Where Bend wins" over 8 of 9 no-clear-difference rows; "-dirty" commit.
- Alex (power user): can't sort by Δ or jump to a game's replay; 82,000px to Method.
- Casey (phone): no result in first screen; tables swipe sideways with Δ never beside names.

## Minor Observations
Table captions ~100–171 cpl at 13px (cap at 90ch); h2 padding 3px; commit hash in Caveat; Run timestamp lacks timezone; nav "Verdict"/"Where" don't match headings; Δ-worse rows heavier (600) than better (400).

## Questions to Consider
- Why is the 100-game 2026 run the landing view when 2025 holds the one clear result?
- What if Head to head printed like a box-score result line?
- Is "Where Bend wins" honest beside "not a claim of superiority"?
