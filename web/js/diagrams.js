// The printed diagrams on the back of the card (Figures 2–4), as Mermaid source for Pele.
export const DIAGRAMS = {
  tree: `flowchart TB
  accTitle: The fork tree at depth 3
  d3["tree d=3<br/>i = 0…7 · Tally: 8 games"] --> a["d=2<br/>0…3"] & b["d=2<br/>4…7"]
  a --> a1["d=1<br/>0,1"] & a2["d=1<br/>2,3"]
  b --> b1["d=1<br/>4,5"] & b2["d=1<br/>6,7"]
  a1 --> g0["one(0)"] & g1["one(1)"]
  a2 --> g2["one(2)"] & g3["one(3)"]
  b1 --> g4["one(4)"] & g5["one(5)"]
  b2 --> g6["one(6)"] & g7["one(7)"]
  classDef pencil fill:#efe6d2,stroke:#1d1d1b,color:#1d1d1b,stroke-width:1.6px
  class g0,g1,g2,g3,g4,g5,g6,g7 pencil`,
  gate: `flowchart LR
  accTitle: The commit gate
  laws[LAWS.bend<br/>what must hold] --> proof[PROOF.bend<br/>induction, case analysis]
  proof --> run{{"bend PROOF.bend"}}
  run --> ok["ALL PROOFS CHECK"] --> commit[commit · bench.py · this page]
  run --> other["anything else"] --> stop[nothing ships]
  classDef pencil fill:#efe6d2,stroke:#1d1d1b,color:#1d1d1b,stroke-width:1.6px
  class ok,commit pencil`,
  pipeline: `flowchart LR
  accTitle: One play's path from the MLB feed to this card
  api[MLB Stats API<br/>play · scoring · official WP · rates to date] --> live[live.py]
  mk[Kalshi · Polymarket · Polymarket US<br/>markets.py] --> live
  live --> enc["7 thresholds / 10,000<br/>play as r3 r2 r1 batter"] --> wp[wp<br/>step → tree 2^d]
  wp --> csv[("runs/&lt;gamePk&gt;.csv")]
  csv -->|POST| worker[Worker + Durable Object]
  worker -->|GET every 5 s| page[this card]
  classDef pencil fill:#efe6d2,stroke:#1d1d1b,color:#1d1d1b,stroke-width:1.6px
  class wp pencil`,
};
