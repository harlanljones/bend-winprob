# Monte Carlo: 2^d games played out from one scorebook state, each by the
# proven Game.step, split across cores (or the GPU) by a balanced fork tree.
import Base
import ./game.bend as Game

# Cumulative plate-appearance thresholds out of 10000, in the order
# strikeout, other out, walk/HBP, single, double, triple, home run (h == 10000).
type Rates is Data:
  Rates{k: U32, o: U32, w: U32, s: U32, d: U32, t: U32, h: U32}

# `ghost`: the regular-season rule that every half from the tenth inning on
# starts with a runner on second.
type Ctx is Data:
  Ctx{start: Game.State, away: Rates, home: Rates, seed: U32, ghost: Bool}

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

def pick(c: Bool, a: Game.Dest, b: Game.Dest) -> Game.Dest:
  match c:
    case True{}:
      a
    case False{}:
      b

# Runner advancement, chances out of 10000, measured on the play-by-play of
# the development games (tune.py advancement); tune.py's exact model of this
# simulator uses the same numbers.
def adv_dp() -> U32:
  2101

def adv_o3() -> U32:
  6108

def adv_o2() -> U32:
  4913

def adv_o1() -> U32:
  2082

def adv_s2() -> U32:
  6117

def adv_s13() -> U32:
  3541

def adv_d1() -> U32:
  3805

def chance(+u: U32, t: U32) -> Bool:
  ((u % 10000 : U32) < t : U32)

# An out in play with a runner on first and fewer than two outs is a double
# play (batter and that runner) with chance dp; with nobody out the runners
# ahead move up a base. Otherwise, with fewer than two outs, the runner on
# third scores, on second takes third, on first takes second, each with its
# own chance and only into a free base.
def out_play.go(dp: Bool, +b1: Bool, +b2: Bool, +b3: Bool, +o: Nat, +u2: U32, +u3: U32, +u4: U32) -> Game.Play:
  match dp:
    case True{}:
      +go = Nat.is_lt(o, 1n)
      Game.Play{occ(Bool.and(b3, go), Game.Run{}), occ(Bool.and(b2, go), Game.To3{}), Game.Out{}, Game.Out{}}
    case False{}:
      +two = Nat.is_lt(o, 2n)
      +s3 = Bool.and(two, Bool.and(b3, chance(u2, adv_o3())))
      +m2 = Bool.and(two, Bool.and(b2, Bool.and(chance(u3, adv_o2()), Bool.not(Bool.and(b3, Bool.not(s3))))))
      +m1 = Bool.and(two, Bool.and(b1, Bool.and(chance(u4, adv_o1()), Bool.not(Bool.and(b2, Bool.not(m2))))))
      Game.Play{occ(s3, Game.Run{}), occ(m2, Game.To3{}), occ(m1, Game.To2{}), Game.Out{}}

def out_play(+b1: Bool, +b2: Bool, +b3: Bool, +o: Nat, +u1: U32, +u2: U32, +u3: U32, +u4: U32) -> Game.Play:
  out_play.go(Bool.and(b1, Bool.and(Nat.is_lt(o, 2n), chance(u1, adv_dp()))), b1, b2, b3, o, u2, u3, u4)

# The play an outcome makes from the bases and outs it meets. A walk moves
# forced runners only; on a single the runner from second scores with chance
# s2 and the runner from first takes a free third with chance s13; on a
# double the runner from first scores with chance d1; triples and home runs
# clear the bases.
def play_for(bs: Game.Bases, e: Ev, +o: Nat, +u1: U32, +u2: U32, +u3: U32, +u4: U32) -> Game.Play:
  match bs:
    case Game.Bases{+b1, +b2, +b3}:
      match e:
        case EvK{}:
          Game.Play{Game.Absent{}, Game.Absent{}, Game.Absent{}, Game.Out{}}
        case EvO{}:
          out_play(b1, b2, b3, o, u1, u2, u3, u4)
        case EvW{}:
          Game.Play{occ(Bool.and(b1, Bool.and(b2, b3)), Game.Run{}), occ(Bool.and(b1, b2), Game.To3{}), occ(b1, Game.To2{}), Game.To1{}}
        case EvS{}:
          +sc2 = chance(u1, adv_s2())
          +go3 = Bool.and(chance(u2, adv_s13()), Bool.not(Bool.and(b2, Bool.not(sc2))))
          Game.Play{occ(b3, Game.Run{}), occ(b2, pick(sc2, Game.Run{}, Game.To3{})), occ(b1, pick(go3, Game.To3{}, Game.To2{})), Game.To1{}}
        case EvD{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, pick(chance(u1, adv_d1()), Game.Run{}, Game.To3{})), Game.To2{}}
        case EvT{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.Run{}), Game.To3{}}
        case EvH{}:
          Game.Play{occ(b3, Game.Run{}), occ(b2, Game.Run{}), occ(b1, Game.Run{}), Game.Run{}}

def rates_for(top: Bool, c: Ctx) -> Rates:
  match top:
    case True{}:
      match c:
        case Ctx{_, away, _, _, _}:
          away
    case False{}:
      match c:
        case Ctx{_, _, home, _, _}:
          home

def ctx_start(c: Ctx) -> Game.State:
  match c:
    case Ctx{s, _, _, _, _}:
      s

def ctx_seed(c: Ctx) -> U32:
  match c:
    case Ctx{_, _, _, seed, _}:
      seed

def ctx_ghost(c: Ctx) -> Bool:
  match c:
    case Ctx{_, _, _, _, g}:
      g

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

# The automatic runner: when `prev` stepped to `s` and the game goes on into
# a new half of the tenth inning or later, a runner is placed on second (a
# play whose batter goes to second, so the scorebook's box still balances).
def flipped(a: Bool, b: Bool) -> Bool:
  match a:
    case True{}:
      Bool.not(b)
    case False{}:
      b

def ghost_play() -> Game.Play:
  Game.Play{Game.Absent{}, Game.Absent{}, Game.Absent{}, Game.To2{}}

def placed.go(new_half: Bool, +s: Game.State) -> Game.State:
  match new_half:
    case True{}:
      Game.step(s, ghost_play())
    case False{}:
      s

def placed(g: Bool, ph: Phase, +prev: Game.State, +s: Game.State) -> Game.State:
  match ph:
    case Ended{_}:
      s
    case Going{}:
      placed.go(Bool.and(g, Bool.and(flipped(Game.is_top(prev), Game.is_top(s)), Nat.is_le(10n, Game.inning(s)))), s)

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
          +y2 = next(y)
          +y3 = next(y2)
          +y4 = next(y3)
          +y5 = next(y4)
          +s2 = Game.step(s, play_for(Game.bases(s), ev, Game.outs(s), y2, y3, y4, y5))
          +ph2 = phase(s, s2)
          play_game(f, ph2, placed(ctx_ghost(c), ph2, s, s2), y5, c)

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
