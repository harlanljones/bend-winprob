# Baseball scorebook: the state of a game, and the one function that moves
# it, `step`, which applies one completed play. LAWS.bend states what must
# always hold about it (outs, runs, the box-score proof of OBR 9.03(c));
# PROOF.bend proves it. The simulator (sim.bend) drives the same `step`.
import Base

# Where one runner (or the batter) ended a play.
type Dest is Data:
  Absent{}
  Out{}
  Run{}
  To1{}
  To2{}
  To3{}

# One play, slot by slot, lead runner first: the runner who started on
# third, on second, on first, then the batter. `Absent` on a base slot is a
# runner who did not move (or no runner); on the batter slot, no batter
# was consumed (a caught stealing, a pickoff, a wild pitch).
type Play is Data:
  Play{r3: Dest, r2: Dest, r1: Dest, bat: Dest}

type Bases is Data:
  Bases{b1: Bool, b2: Bool, b3: Bool}

# One team's cumulative scorebook line: batters who completed a plate
# appearance, runs, outs made, runners left on base at a half's end.
type Line is Data:
  Line{bat: Nat, runs: Nat, outs: Nat, lob: Nat}

# The batting side's working state while a play is applied.
type Half is Data:
  Half{bases: Bases, line: Line, outs: Nat}

type State is Data:
  State{inning: Nat, top: Bool, outs: Nat, bases: Bases, away: Line, home: Line, rejected: Nat}

# Basics
# ------

def b2n(b: Bool) -> Nat:
  match b:
    case True{}:
      1n
    case False{}:
      0n

def count(b: Bases) -> Nat:
  match b:
    case Bases{b1, b2, b3}:
      Nat.add(b2n(b1), Nat.add(b2n(b2), b2n(b3)))

def empty() -> Bases:
  Bases{False{}, False{}, False{}}

def zero() -> Line:
  Line{0n, 0n, 0n, 0n}

def start() -> State:
  State{1n, True{}, 0n, empty(), zero(), zero(), 0n}

def is_moved(d: Dest) -> Bool:
  match d:
    case Absent{}:
      False{}
    case Out{}:
      True{}
    case Run{}:
      True{}
    case To1{}:
      True{}
    case To2{}:
      True{}
    case To3{}:
      True{}

# Landing: the runner in hand reaches `d`
# ---------------------------------------

def add_out(h: Half) -> Half:
  match h:
    case Half{bs, Line{bat, runs, lo, lob}, o}:
      Half{bs, Line{bat, runs, 1n+lo, lob}, 1n+o}

def add_run(h: Half) -> Half:
  match h:
    case Half{bs, Line{bat, runs, lo, lob}, o}:
      Half{bs, Line{bat, 1n+runs, lo, lob}, o}

def land1(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{False{}, b2, b3}, l, o}:
      Some{Half{Bases{True{}, b2, b3}, l, o}}
    case Half{Bases{True{}, b2, b3}, l, o}:
      None{}

def land2(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{b1, False{}, b3}, l, o}:
      Some{Half{Bases{b1, True{}, b3}, l, o}}
    case Half{Bases{b1, True{}, b3}, l, o}:
      None{}

def land3(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{b1, b2, False{}}, l, o}:
      Some{Half{Bases{b1, b2, True{}}, l, o}}
    case Half{Bases{b1, b2, True{}}, l, o}:
      None{}

def put(d: Dest, h: Half) -> Maybe<Half>:
  match d:
    case Absent{}:
      None{}
    case Out{}:
      Some{add_out(h)}
    case Run{}:
      Some{add_run(h)}
    case To1{}:
      land1(h)
    case To2{}:
      land2(h)
    case To3{}:
      land3(h)

def put_m(d: Dest, m: Maybe<Half>) -> Maybe<Half>:
  match m:
    case None{}:
      None{}
    case Some{h}:
      put(d, h)

# Taking: the runner leaves its origin
# ------------------------------------

def take3(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{b1, b2, True{}}, l, o}:
      Some{Half{Bases{b1, b2, False{}}, l, o}}
    case Half{Bases{b1, b2, False{}}, l, o}:
      None{}

def take2(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{b1, True{}, b3}, l, o}:
      Some{Half{Bases{b1, False{}, b3}, l, o}}
    case Half{Bases{b1, False{}, b3}, l, o}:
      None{}

def take1(h: Half) -> Maybe<Half>:
  match h:
    case Half{Bases{True{}, b2, b3}, l, o}:
      Some{Half{Bases{False{}, b2, b3}, l, o}}
    case Half{Bases{False{}, b2, b3}, l, o}:
      None{}

def take_bat(h: Half) -> Half:
  match h:
    case Half{bs, Line{bat, runs, lo, lob}, o}:
      Half{bs, Line{1n+bat, runs, lo, lob}, o}

# Slots
# -----

def slot3.go(m: Bool, d: Dest, h: Half) -> Maybe<Half>:
  match m:
    case False{}:
      Some{h}
    case True{}:
      put_m(d, take3(h))

def slot3(+d: Dest, h: Half) -> Maybe<Half>:
  slot3.go(is_moved(d), d, h)

def slot2.go(m: Bool, d: Dest, h: Half) -> Maybe<Half>:
  match m:
    case False{}:
      Some{h}
    case True{}:
      put_m(d, take2(h))

def slot2(+d: Dest, h: Half) -> Maybe<Half>:
  slot2.go(is_moved(d), d, h)

def slot1.go(m: Bool, d: Dest, h: Half) -> Maybe<Half>:
  match m:
    case False{}:
      Some{h}
    case True{}:
      put_m(d, take1(h))

def slot1(+d: Dest, h: Half) -> Maybe<Half>:
  slot1.go(is_moved(d), d, h)

def slotb.go(m: Bool, d: Dest, h: Half) -> Maybe<Half>:
  match m:
    case False{}:
      Some{h}
    case True{}:
      put(d, take_bat(h))

def slotb(+d: Dest, h: Half) -> Maybe<Half>:
  slotb.go(is_moved(d), d, h)

def chain_b(m: Maybe<Half>, bd: Dest) -> Maybe<Half>:
  match m:
    case None{}:
      None{}
    case Some{h}:
      slotb(bd, h)

def chain_1(m: Maybe<Half>, r1: Dest, bd: Dest) -> Maybe<Half>:
  match m:
    case None{}:
      None{}
    case Some{h}:
      chain_b(slot1(r1, h), bd)

def chain_2(m: Maybe<Half>, r2: Dest, r1: Dest, bd: Dest) -> Maybe<Half>:
  match m:
    case None{}:
      None{}
    case Some{h}:
      chain_1(slot2(r2, h), r1, bd)

def slots(p: Play, h: Half) -> Maybe<Half>:
  match p:
    case Play{r3, r2, r1, bd}:
      chain_2(slot3(r3, h), r2, r1, bd)

# Step
# ----

def half_pick(top: Bool, bs: Bases, away: Line, home: Line, o: Nat) -> Half:
  match top:
    case True{}:
      Half{bs, away, o}
    case False{}:
      Half{bs, home, o}

def half_of(s: State) -> Half:
  match s:
    case State{inn, top, o, bs, away, home, rej}:
      half_pick(top, bs, away, home, o)

def reject(s: State) -> State:
  match s:
    case State{inn, top, o, bs, away, home, rej}:
      State{inn, top, o, bs, away, home, 1n+rej}

def store.go(top: Bool, inn: Nat, o: Nat, bs: Bases, l: Line, away: Line, home: Line, rej: Nat) -> State:
  match top:
    case True{}:
      State{inn, True{}, o, bs, l, home, rej}
    case False{}:
      State{inn, False{}, o, bs, away, l, rej}

def store(s: State, bs: Bases, l: Line, o: Nat) -> State:
  match s:
    case State{inn, top, _, _, away, home, rej}:
      store.go(top, inn, o, bs, l, away, home, rej)

def add_lob(l: Line, k: Nat) -> Line:
  match l:
    case Line{bat, runs, lo, lob}:
      Line{bat, runs, lo, Nat.add(k, lob)}

def end_half.go(top: Bool, inn: Nat, l: Line, away: Line, home: Line, rej: Nat) -> State:
  match top:
    case True{}:
      State{inn, False{}, 0n, empty(), l, home, rej}
    case False{}:
      State{1n+inn, True{}, 0n, empty(), away, l, rej}

def end_half(s: State, bs: Bases, l: Line) -> State:
  match s:
    case State{inn, top, _, _, away, home, rej}:
      end_half.go(top, inn, add_lob(l, count(bs)), away, home, rej)

# `o` is the half's outs after the play: under three the play is stored,
# at three the half ends, past three the play is refused.
def close(o: Nat, s: State, bs: Bases, l: Line) -> State:
  match o:
    case 0n:
      store(s, bs, l, 0n)
    case 1n+o1:
      match o1:
        case 0n:
          store(s, bs, l, 1n)
        case 1n+o2:
          match o2:
            case 0n:
              store(s, bs, l, 2n)
            case 1n+o3:
              match o3:
                case 0n:
                  end_half(s, bs, l)
                case 1n+o4:
                  reject(s)

def commit(s: State, h: Half) -> State:
  match h:
    case Half{bs, l, o}:
      close(o, s, bs, l)

def after(s: State, m: Maybe<Half>) -> State:
  match m:
    case None{}:
      reject(s)
    case Some{h}:
      commit(s, h)

def step(+s: State, p: Play) -> State:
  after(s, slots(p, half_of(s)))

# The worker takes the list first: termination wants the shrinking argument
# in the first column. `replay` is the API.
def run(ps: List<&2, Play>, s: State) -> State:
  match ps:
    case Nil{}:
      s
    case p <> rest:
      run(rest, step(s, p))

def replay(s: State, ps: List<&2, Play>) -> State:
  run(ps, s)

# Readers
# -------

def inning(s: State) -> Nat:
  match s:
    case State{inn, _, _, _, _, _, _}:
      inn

def is_top(s: State) -> Bool:
  match s:
    case State{_, top, _, _, _, _, _}:
      top

def outs(s: State) -> Nat:
  match s:
    case State{_, _, o, _, _, _, _}:
      o

def bases(s: State) -> Bases:
  match s:
    case State{_, _, _, bs, _, _, _}:
      bs

def rejected(s: State) -> Nat:
  match s:
    case State{_, _, _, _, _, _, rej}:
      rej

def away_line(s: State) -> Line:
  match s:
    case State{_, _, _, _, away, _, _}:
      away

def home_line(s: State) -> Line:
  match s:
    case State{_, _, _, _, _, home, _}:
      home

def line_bat(l: Line) -> Nat:
  match l:
    case Line{bat, _, _, _}:
      bat

def line_runs(l: Line) -> Nat:
  match l:
    case Line{_, runs, _, _}:
      runs

def line_outs(l: Line) -> Nat:
  match l:
    case Line{_, _, lo, _}:
      lo

def line_lob(l: Line) -> Nat:
  match l:
    case Line{_, _, _, lob}:
      lob

def away_runs(s: State) -> Nat:
  line_runs(away_line(s))

def home_runs(s: State) -> Nat:
  line_runs(home_line(s))

def on_base.go(top: Bool, bs: Bases, want_top: Bool) -> Nat:
  match top want_top:
    case True{} True{}:
      count(bs)
    case False{} False{}:
      count(bs)
    case _ _:
      0n

# Runners now on base for the away (top) or home (bottom) side.
def on_base_away(s: State) -> Nat:
  match s:
    case State{_, top, _, bs, _, _, _}:
      on_base.go(top, bs, True{})

def on_base_home(s: State) -> Nat:
  match s:
    case State{_, top, _, bs, _, _, _}:
      on_base.go(top, bs, False{})

# OBR 9.03(c), one team: batters who completed a plate appearance, against
# runs + putouts by the defense + left on base + still on base.
def line_demand(l: Line) -> Nat:
  match l:
    case Line{_, runs, lo, lob}:
      Nat.add(runs, Nat.add(lo, lob))

def away_supply(s: State) -> Nat:
  line_bat(away_line(s))

def away_demand(+s: State) -> Nat:
  Nat.add(on_base_away(s), line_demand(away_line(s)))

def home_supply(s: State) -> Nat:
  line_bat(home_line(s))

def home_demand(+s: State) -> Nat:
  Nat.add(on_base_home(s), line_demand(home_line(s)))
