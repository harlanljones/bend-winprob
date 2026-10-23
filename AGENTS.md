When using Bend:
- run `bend guide` to learn it
- use `LAWS.bend` to keep important rules
- run `bend PROOF.bend` before committing
- parallelize the code whenever possible

Build: bend main.bend -o wp
Check before commit: bend PROOF.bend && python3 live.py --pk 849809 --replay
