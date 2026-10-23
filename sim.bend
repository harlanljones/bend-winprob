# Monte Carlo: 2^d games played out from one scorebook state, each by the
# proven Game.step, split across cores (or the GPU) by a balanced fork tree.
import Base
import ./game.bend as Game

# Cumulative plate-appearance thresholds out of 10000, in the order
# strikeout, other out, walk/HBP, single, double, triple, home run (h == 10000).
type Rates is Data:
  Rates{k: U32, o: U32, w: U32, s: U32, d: U32, t: U32, h: U32}

type Ctx is Data:
  Ctx{start: Game.State, away: Rates, home: Rates, seed: U32}

type Outcome is Data:
  HomeWin{}
  AwayWin{}
  Unfinished{}

type Tally is Data:
  Tally{home: Nat, away: Nat, unfinished: Nat}

type Ev is Data:
  EvK{}
  EvO{}
  EvW{}
  EvS{}
  EvD{}
  EvT{}
  EvH{}

type Phase is Data:
  Going{}
  Ended{result: Outcome}

# Random numbers
# --------------

# A U32 hash (the mixer of demos/app_slash_boss_3d Synth.noise, no float).
def mix(+i: U32) -> U32:
  +a = (U32.xor(i, (i >> 16n : U32)) * 2146121005 : U32)
  +b = (U32.xor(a, (a >> 15n : U32)) * 2221713035 : U32)
  U32.xor(b, (b >> 16n : U32))

def nz.go(z: Bool, x: U32) -> U32:
  match z:
    case True{}:
      2654435769
    case False{}:
      x

# xorshift32 sticks at 0: never start it there.
def nz(+x: U32) -> U32:
  nz.go(U32.is_eq(x, 0), x)

def next(+x: U32) -> U32:
  +a = U32.xor(x, (x << 13n : U32))
  +b = U32.xor(a, (a >> 17n : U32))
  U32.xor(b, (b << 5n : U32))

# Plate appearances
# -----------------

def sel(c: Bool, a: Ev, b: Ev) -> Ev:
  match c:
    case True{}:
      a
    case False{}:
      b

def ev_of(+u: U32, r: Rates) -> Ev:
  match r:
    case Rates{k, o, w, s, d, t, h}:
      sel((u < k : U32), EvK{},
        sel((u < o : U32), EvO{},
          sel((u < w : U32), EvW{},
            sel((u < s : U32), EvS{},
              sel((u < d : U32), EvD{},
                sel((u < t : U32), EvT{}, EvH{}))))))

def occ(b: Bool, d: Game.Dest) -> Game.Dest:
  match b:
    case True{}:
      d
    case False{}:
      Game.Absent{}

# The play an outcome makes from the bases and outs it meets. An out in play
# scores the runner from third with fewer than two outs (a sacrifice fly);
# a walk moves forced runners only; hits move every runner that many bases.
def play_for(bs: Game.Bases, e: Ev, +o: Nat) -> Game.Play:
  match bs:
    case Game.Bases{+b1, +b2, +b3}:
      match e:
        case EvK{}:
          Game.Play{Game.Absent{}, Game.Absent{}, Game.Absent{}, Game.Out{}}
        case EvO{}:
          Game.Play{occ(Bool.and(b3, Nat.is_lt(o, 2n)), Game.Run{}), Game.Absent{}, Game.Absent{}, Game.Out{}}
        case EvW{}:
          Game.Play{occ(Bool.and(b1, Bool.and(b2, b3)), Game.Run{}), occ(Bool.and(b1, b2), Game.To3{}), occ(b1, Game.To2{}), Game.To1{}}
        case EvS{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.To2{}), Game.To1{}}
        case EvD{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.To3{}), Game.To2{}}
        case EvT{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.Run{}), Game.To3{}}
        case EvH{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.Run{}), Game.Run{}}

def rates_for(top: Bool, c: Ctx) -> Rates:
  match top:
    case True{}:
      match c:
        case Ctx{_, away, _, _}:
          away
    case False{}:
      match c:
        case Ctx{_, _, home, _}:
          home

def ctx_start(c: Ctx) -> Game.State:
  match c:
    case Ctx{s, _, _, _}:
      s

def ctx_seed(c: Ctx) -> U32:
  match c:
    case Ctx{_, _, _, seed}:
      seed

# The game ends
# -------------

# Home leads in the bottom of the ninth or later: the half is skipped, or a
# walk-off ended it.
def walkoff(+s: Game.State) -> Bool:
  Bool.and(Bool.not(Game.is_top(s)),
    Bool.and(Nat.is_le(9n, Game.inning(s)),
      Nat.is_lt(Game.away_runs(s), Game.home_runs(s))))

def lead.go(away_ahead: Bool, home_ahead: Bool) -> Phase:
  match away_ahead:
    case True{}:
      Ended{AwayWin{}}
    case False{}:
      match home_ahead:
        case True{}:
          Ended{HomeWin{}}
        case False{}:
          Going{}

def lead(+s: Game.State) -> Phase:
  lead.go(Nat.is_lt(Game.home_runs(s), Game.away_runs(s)),
    Nat.is_lt(Game.away_runs(s), Game.home_runs(s)))

def phase.go(w: Bool, inning_over: Bool, +s: Game.State) -> Phase:
  match w:
    case True{}:
      Ended{HomeWin{}}
    case False{}:
      match inning_over:
        case True{}:
          lead(s)
        case False{}:
          Going{}

# `prev` stepped to `s`: a bottom half that ended in the tenth inning or
# later (the ninth's bottom ending opens the tenth) decides a game not tied.
def phase(+prev: Game.State, +s: Game.State) -> Phase:
  phase.go(walkoff(s),
    Bool.and(Bool.not(Game.is_top(prev)),
      Bool.and(Game.is_top(s), Nat.is_le(10n, Game.inning(s)))),
    s)

# One game, at most `fuel` plate appearances.
def play_game(fuel: Nat, ph: Phase, +s: Game.State, +x: U32, +c: Ctx) -> Outcome:
  match fuel:
    case 0n:
      Unfinished{}
    case 1n+f:
      match ph:
        case Ended{r}:
          r
        case Going{}:
          +y = next(x)
          +ev = ev_of((y % 10000 : U32), rates_for(Game.is_top(s), c))
          +s2 = Game.step(s, play_for(Game.bases(s), ev, Game.outs(s)))
          play_game(f, phase(s, s2), s2, y, c)

def one(+i: U32, +c: Ctx) -> Outcome:
  +s = ctx_start(c)
  play_game(400n, phase(s, s), s, nz(mix(U32.xor(ctx_seed(c), i))), c)

# Tallies
# -------

def tally_of(o: Outcome) -> Tally:
  match o:
    case HomeWin{}:
      Tally{1n, 0n, 0n}
    case AwayWin{}:
      Tally{0n, 1n, 0n}
    case Unfinished{}:
      Tally{0n, 0n, 1n}

def tally_add(a: Tally, b: Tally) -> Tally:
  match a:
    case Tally{h1, a1, u1}:
      match b:
        case Tally{h2, a2, u2}:
          Tally{Nat.add(h1, h2), Nat.add(a1, a2), Nat.add(u1, u2)}

def total(t: Tally) -> Nat:
  match t:
    case Tally{h, a, u}:
      Nat.add(h, Nat.add(a, u))

def pow2(d: Nat) -> Nat:
  match d:
    case 0n:
      1n
    case 1n+p:
      +h = pow2(p)
      Nat.add(h, h)

# 2^d games, numbered i .. i + 2^d - 1, as a balanced fork tree.
def tree(d: Nat, +i: U32, +c: Ctx) -> Tally:
  match d:
    case 0n:
      tally_of(one(i, c))
    case 1n++p:
      a b = tree(p, i, c) tree(p, (i + U32.from_nat(pow2(p)) : U32), c)
      tally_add(a, b)
