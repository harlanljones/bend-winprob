# The proofs of LAWS.bend. A match is case analysis, a self-call is the
# induction hypothesis, and `%e : P` rewrites the goal with the equation e.
import Base
import ./game.bend as Game
import ./sim.bend as Sim
import ./LAWS.bend as Laws

# Addition (as in demos/proof_numerics)
# -------------------------------------

def add_succ(a: Nat, -b: Nat) -> {1n+Nat.add(a, b) == Nat.add(a, 1n+b) : Nat}:
  match a:
    case 0n:
      {==}
    case 1n+p:
      %add_succ(p, b) : {2n+Nat.add(p, b) == 1n+_ : Nat}
      {==}

# the first two terms of a triple sum swap
def add_swap(x: Nat, +y: Nat, +z: Nat) -> {Nat.add(x, Nat.add(y, z)) == Nat.add(y, Nat.add(x, z)) : Nat}:
  match x:
    case 0n:
      {==}
    case 1n+q:
      %add_succ(y, Nat.add(q, z)) : {1n+Nat.add(q, Nat.add(y, z)) == _ : Nat}
      %add_swap(q, y, z) : {1n+Nat.add(q, Nat.add(y, z)) == 1n+_ : Nat}
      {==}

# (a + b) + (c + d) == (a + c) + (b + d)
def swap4(a: Nat, +b: Nat, +c: Nat, +d: Nat) -> {Nat.add(Nat.add(a, b), Nat.add(c, d)) == Nat.add(Nat.add(a, c), Nat.add(b, d)) : Nat}:
  match a:
    case 0n:
      add_swap(b, c, d)
    case 1n+p:
      %swap4(p, b, c, d) : {1n+Nat.add(Nat.add(p, b), Nat.add(c, d)) == 1n+_ : Nat}
      {==}

# Simulation counts
# -----------------

def total_one(o: Sim.Outcome) -> {Sim.total(Sim.tally_of(o)) == 1n : Nat}:
  match o:
    case Sim.HomeWin{}:
      {==}
    case Sim.AwayWin{}:
      {==}
    case Sim.Unfinished{}:
      {==}

def total_add(a: Sim.Tally, b: Sim.Tally) -> {Nat.add(Sim.total(a), Sim.total(b)) == Sim.total(Sim.tally_add(a, b)) : Nat}:
  match a:
    case Sim.Tally{+h1, +a1, +u1}:
      match b:
        case Sim.Tally{+h2, +a2, +u2}:
          %swap4(a1, u1, a2, u2) : {Nat.add(Nat.add(h1, Nat.add(a1, u1)), Nat.add(h2, Nat.add(a2, u2))) == Nat.add(Nat.add(h1, h2), _) : Nat}
          swap4(h1, Nat.add(a1, u1), h2, Nat.add(a2, u2))

def Laws.sims_all_counted(d, i, c):
  match d:
    case 0n:
      total_one(Sim.one(i, c))
    case 1n++p:
      %total_add(Sim.tree(p, i, c), Sim.tree(p, U32.add(i, U32.from_nat(Sim.pow2(p))), c)) : {_ == Nat.add(Sim.pow2(p), Sim.pow2(p)) : Nat}
      %Laws.sims_all_counted(p, i, c) : {Nat.add(Sim.total(Sim.tree(p, i, c)), Sim.total(Sim.tree(p, U32.add(i, U32.from_nat(Sim.pow2(p))), c))) == Nat.add(_, Sim.pow2(p)) : Nat}
      %Laws.sims_all_counted(p, U32.add(i, U32.from_nat(Sim.pow2(p))), c) : {Nat.add(Sim.total(Sim.tree(p, i, c)), Sim.total(Sim.tree(p, U32.add(i, U32.from_nat(Sim.pow2(p))), c))) == Nat.add(Sim.total(Sim.tree(p, i, c)), _) : Nat}
      {==}

# Outs
# ----
# A half closes at three outs and a play past three is refused, so the
# outs a state shows are 0, 1, 2, or those it had.

def outs_close(o: Nat, top: Bool, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat, -bs: Game.Bases, -l: Game.Line, w: {Nat.is_lt(so, 3n) == True{} : Bool})
  -> {Nat.is_lt(Game.outs(Game.close(o, Game.State{inn, top, so, sb, away, home, rej}, bs, l)), 3n) == True{} : Bool}:
  match o:
    case 0n:
      match top:
        case True{}:
          {==}
        case False{}:
          {==}
    case 1n+o1:
      match o1:
        case 0n:
          match top:
            case True{}:
              {==}
            case False{}:
              {==}
        case 1n+o2:
          match o2:
            case 0n:
              match top:
                case True{}:
                  {==}
                case False{}:
                  {==}
            case 1n+o3:
              match o3:
                case 0n:
                  match top:
                    case True{}:
                      {==}
                    case False{}:
                      {==}
                case 1n+o4:
                  w

def outs_after(m: Maybe<Game.Half>, top: Bool, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat, w: {Nat.is_lt(so, 3n) == True{} : Bool})
  -> {Nat.is_lt(Game.outs(Game.after(Game.State{inn, top, so, sb, away, home, rej}, m)), 3n) == True{} : Bool}:
  match m:
    case None{}:
      w
    case Some{h}:
      match h:
        case Game.Half{bs, l, o}:
          outs_close(o, top, inn, so, sb, away, home, rej, bs, l, w)

def outs_step(s: Game.State, p: Game.Play, w: {Nat.is_lt(Game.outs(s), 3n) == True{} : Bool})
  -> {Nat.is_lt(Game.outs(Game.step(s, p)), 3n) == True{} : Bool}:
  match s:
    case Game.State{+inn, +top, +so, +sb, +away, +home, +rej}:
      outs_after(Game.slots(p, Game.half_of(Game.State{inn, top, so, sb, away, home, rej})), top, inn, so, sb, away, home, rej, w)

def outs_run(ps: List<&2, Game.Play>, +s: Game.State, w: {Nat.is_lt(Game.outs(s), 3n) == True{} : Bool})
  -> {Nat.is_lt(Game.outs(Game.run(ps, s)), 3n) == True{} : Bool}:
  match ps:
    case Nil{}:
      w
    case Con{+p, rest}:
      outs_run(rest, Game.step(s, p), outs_step(s, p, w))

def Laws.outs_below_three(ps):
  outs_run(ps, Game.start(), {==})
