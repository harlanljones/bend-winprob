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

# Box score (OBR 9.03(c))
# -----------------------
# HBal(e, h): the batting side's batters equal e runners in hand, plus the
# runners on base, plus its runs, outs and left on base. A slot takes a
# runner into the hand (from a base, or a new batter) and puts it down (on
# a base, home, or out), so every slot keeps HBal(0n, ..).

def sym(-A: Type, -a: A, -b: A, e: {a == b : A}) -> {b == a : A}:
  %e : {_ == a : A}
  {==}

def HBal(e: Nat, h: Game.Half) -> Type:
  match h:
    case Game.Half{+bs, +l, o}:
      {Game.line_bat(l) == Nat.add(e, Nat.add(Game.count(bs), Game.line_demand(l))) : Nat}

def OkM(e: Nat, m: Maybe<Game.Half>) -> Type:
  match m:
    case None{}:
      Unit
    case Some{h}:
      HBal(e, h)

def count_b2(b1: Bool, -b3: Bool) -> {Game.count(Game.Bases{b1, True{}, b3}) == 1n+Game.count(Game.Bases{b1, False{}, b3}) : Nat}:
  match b1:
    case True{}:
      {==}
    case False{}:
      {==}

def count_b3(b1: Bool, b2: Bool) -> {Game.count(Game.Bases{b1, b2, True{}}) == 1n+Game.count(Game.Bases{b1, b2, False{}}) : Nat}:
  match b1:
    case True{}:
      match b2:
        case True{}:
          {==}
        case False{}:
          {==}
    case False{}:
      match b2:
        case True{}:
          {==}
        case False{}:
          {==}

def take1_bal(h: Game.Half, w: HBal(0n, h)) -> OkM(1n, Game.take1(h)):
  match h:
    case Game.Half{bs, l, o}:
      match bs:
        case Game.Bases{b1, b2, b3}:
          match b1:
            case True{}:
              w
            case False{}:
              Unit{}

def take2_bal(h: Game.Half, w: HBal(0n, h)) -> OkM(1n, Game.take2(h)):
  match h:
    case Game.Half{bs, +l, o}:
      match bs:
        case Game.Bases{+b1, b2, +b3}:
          match b2:
            case True{}:
              %count_b2(b1, b3) : {Game.line_bat(l) == Nat.add(_, Game.line_demand(l)) : Nat}
              w
            case False{}:
              Unit{}

def take3_bal(h: Game.Half, w: HBal(0n, h)) -> OkM(1n, Game.take3(h)):
  match h:
    case Game.Half{bs, +l, o}:
      match bs:
        case Game.Bases{+b1, +b2, b3}:
          match b3:
            case True{}:
              %count_b3(b1, b2) : {Game.line_bat(l) == Nat.add(_, Game.line_demand(l)) : Nat}
              w
            case False{}:
              Unit{}

def take_bat_bal(h: Game.Half, w: HBal(0n, h)) -> HBal(1n, Game.take_bat(h)):
  match h:
    case Game.Half{+bs, l, o}:
      match l:
        case Game.Line{+bat, +runs, +lo, +lob}:
          %w : {1n+bat == 1n+_ : Nat}
          {==}

def put_bal(d: Game.Dest, h: Game.Half, w: HBal(1n, h)) -> OkM(0n, Game.put(d, h)):
  match d:
    case Game.Absent{}:
      Unit{}
    case Game.Out{}:
      match h:
        case Game.Half{+bs, l, o}:
          match l:
            case Game.Line{+bat, +runs, +lo, +lob}:
              %add_succ(runs, Nat.add(lo, lob)) : {bat == Nat.add(Game.count(bs), _) : Nat}
              %add_succ(Game.count(bs), Nat.add(runs, Nat.add(lo, lob))) : {bat == _ : Nat}
              w
    case Game.Run{}:
      match h:
        case Game.Half{+bs, l, o}:
          match l:
            case Game.Line{+bat, +runs, +lo, +lob}:
              %add_succ(Game.count(bs), Nat.add(runs, Nat.add(lo, lob))) : {bat == _ : Nat}
              w
    case Game.To1{}:
      match h:
        case Game.Half{bs, l, o}:
          match bs:
            case Game.Bases{b1, b2, b3}:
              match b1:
                case True{}:
                  Unit{}
                case False{}:
                  w
    case Game.To2{}:
      match h:
        case Game.Half{bs, +l, o}:
          match bs:
            case Game.Bases{+b1, b2, +b3}:
              match b2:
                case True{}:
                  Unit{}
                case False{}:
                  %sym(Nat, Game.count(Game.Bases{b1, True{}, b3}), 1n+Game.count(Game.Bases{b1, False{}, b3}), count_b2(b1, b3)) : {Game.line_bat(l) == Nat.add(_, Game.line_demand(l)) : Nat}
                  w
    case Game.To3{}:
      match h:
        case Game.Half{bs, +l, o}:
          match bs:
            case Game.Bases{+b1, +b2, b3}:
              match b3:
                case True{}:
                  Unit{}
                case False{}:
                  %sym(Nat, Game.count(Game.Bases{b1, b2, True{}}), 1n+Game.count(Game.Bases{b1, b2, False{}}), count_b3(b1, b2)) : {Game.line_bat(l) == Nat.add(_, Game.line_demand(l)) : Nat}
                  w

def putm_bal(m: Maybe<Game.Half>, d: Game.Dest, w: OkM(1n, m)) -> OkM(0n, Game.put_m(d, m)):
  match m:
    case None{}:
      Unit{}
    case Some{h}:
      put_bal(d, h, w)

def slot3_bal(d: Game.Dest, +h: Game.Half, w: HBal(0n, h)) -> OkM(0n, Game.slot3(d, h)):
  match d:
    case Game.Absent{}:
      w
    case Game.Out{}:
      putm_bal(Game.take3(h), Game.Out{}, take3_bal(h, w))
    case Game.Run{}:
      putm_bal(Game.take3(h), Game.Run{}, take3_bal(h, w))
    case Game.To1{}:
      putm_bal(Game.take3(h), Game.To1{}, take3_bal(h, w))
    case Game.To2{}:
      putm_bal(Game.take3(h), Game.To2{}, take3_bal(h, w))
    case Game.To3{}:
      putm_bal(Game.take3(h), Game.To3{}, take3_bal(h, w))

def slot2_bal(d: Game.Dest, +h: Game.Half, w: HBal(0n, h)) -> OkM(0n, Game.slot2(d, h)):
  match d:
    case Game.Absent{}:
      w
    case Game.Out{}:
      putm_bal(Game.take2(h), Game.Out{}, take2_bal(h, w))
    case Game.Run{}:
      putm_bal(Game.take2(h), Game.Run{}, take2_bal(h, w))
    case Game.To1{}:
      putm_bal(Game.take2(h), Game.To1{}, take2_bal(h, w))
    case Game.To2{}:
      putm_bal(Game.take2(h), Game.To2{}, take2_bal(h, w))
    case Game.To3{}:
      putm_bal(Game.take2(h), Game.To3{}, take2_bal(h, w))

def slot1_bal(d: Game.Dest, +h: Game.Half, w: HBal(0n, h)) -> OkM(0n, Game.slot1(d, h)):
  match d:
    case Game.Absent{}:
      w
    case Game.Out{}:
      putm_bal(Game.take1(h), Game.Out{}, take1_bal(h, w))
    case Game.Run{}:
      putm_bal(Game.take1(h), Game.Run{}, take1_bal(h, w))
    case Game.To1{}:
      putm_bal(Game.take1(h), Game.To1{}, take1_bal(h, w))
    case Game.To2{}:
      putm_bal(Game.take1(h), Game.To2{}, take1_bal(h, w))
    case Game.To3{}:
      putm_bal(Game.take1(h), Game.To3{}, take1_bal(h, w))

def slotb_bal(d: Game.Dest, +h: Game.Half, w: HBal(0n, h)) -> OkM(0n, Game.slotb(d, h)):
  match d:
    case Game.Absent{}:
      w
    case Game.Out{}:
      put_bal(Game.Out{}, Game.take_bat(h), take_bat_bal(h, w))
    case Game.Run{}:
      put_bal(Game.Run{}, Game.take_bat(h), take_bat_bal(h, w))
    case Game.To1{}:
      put_bal(Game.To1{}, Game.take_bat(h), take_bat_bal(h, w))
    case Game.To2{}:
      put_bal(Game.To2{}, Game.take_bat(h), take_bat_bal(h, w))
    case Game.To3{}:
      put_bal(Game.To3{}, Game.take_bat(h), take_bat_bal(h, w))

def chainb_bal(m: Maybe<Game.Half>, bd: Game.Dest, w: OkM(0n, m)) -> OkM(0n, Game.chain_b(m, bd)):
  match m:
    case None{}:
      Unit{}
    case Some{h}:
      slotb_bal(bd, h, w)

def chain1_bal(m: Maybe<Game.Half>, +r1: Game.Dest, bd: Game.Dest, w: OkM(0n, m)) -> OkM(0n, Game.chain_1(m, r1, bd)):
  match m:
    case None{}:
      Unit{}
    case Some{+h}:
      chainb_bal(Game.slot1(r1, h), bd, slot1_bal(r1, h, w))

def chain2_bal(m: Maybe<Game.Half>, +r2: Game.Dest, r1: Game.Dest, bd: Game.Dest, w: OkM(0n, m)) -> OkM(0n, Game.chain_2(m, r2, r1, bd)):
  match m:
    case None{}:
      Unit{}
    case Some{+h}:
      chain1_bal(Game.slot2(r2, h), r1, bd, slot2_bal(r2, h, w))

def slots_bal(p: Game.Play, +h: Game.Half, w: HBal(0n, h)) -> OkM(0n, Game.slots(p, h)):
  match p:
    case Game.Play{+r3, r2, r1, bd}:
      chain2_bal(Game.slot3(r3, h), r2, r1, bd, slot3_bal(r3, h, w))

# The whole state: both teams balance (the side in the field has no one on base).
def SBal(+s: Game.State) -> Type:
  {Game.away_supply(s) == Game.away_demand(s) : Nat} & {Game.home_supply(s) == Game.home_demand(s) : Nat}

# A half ends: its runners on base become left on base.
def lob_move(+c: Nat, l: Game.Line, w: {Game.line_bat(l) == Nat.add(c, Game.line_demand(l)) : Nat})
  -> {Game.line_bat(Game.add_lob(l, c)) == Game.line_demand(Game.add_lob(l, c)) : Nat}:
  match l:
    case Game.Line{+bat, +runs, +lo, +lob}:
      %add_swap(c, lo, lob) : {bat == Nat.add(runs, _) : Nat}
      %add_swap(c, runs, Nat.add(lo, lob)) : {bat == _ : Nat}
      w

def close_top(o: Nat, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat, +bs: Game.Bases, +l: Game.Line,
  wm: HBal(0n, Game.Half{bs, l, o}), wa: {Game.line_bat(away) == Nat.add(Game.count(sb), Game.line_demand(away)) : Nat}, wh: {Game.line_bat(home) == Game.line_demand(home) : Nat})
  -> SBal(Game.close(o, Game.State{inn, True{}, so, sb, away, home, rej}, bs, l)):
  match o:
    case 0n:
      (wm, wh)
    case 1n+o1:
      match o1:
        case 0n:
          (wm, wh)
        case 1n+o2:
          match o2:
            case 0n:
              (wm, wh)
            case 1n+o3:
              match o3:
                case 0n:
                  (lob_move(Game.count(bs), l, wm), wh)
                case 1n+o4:
                  (wa, wh)

def close_bot(o: Nat, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat, +bs: Game.Bases, +l: Game.Line,
  wm: HBal(0n, Game.Half{bs, l, o}), wa: {Game.line_bat(away) == Game.line_demand(away) : Nat}, wh: {Game.line_bat(home) == Nat.add(Game.count(sb), Game.line_demand(home)) : Nat})
  -> SBal(Game.close(o, Game.State{inn, False{}, so, sb, away, home, rej}, bs, l)):
  match o:
    case 0n:
      (wa, wm)
    case 1n+o1:
      match o1:
        case 0n:
          (wa, wm)
        case 1n+o2:
          match o2:
            case 0n:
              (wa, wm)
            case 1n+o3:
              match o3:
                case 0n:
                  (wa, lob_move(Game.count(bs), l, wm))
                case 1n+o4:
                  (wa, wh)

def after_top(m: Maybe<Game.Half>, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat,
  wm: OkM(0n, m), wa: {Game.line_bat(away) == Nat.add(Game.count(sb), Game.line_demand(away)) : Nat}, wh: {Game.line_bat(home) == Game.line_demand(home) : Nat})
  -> SBal(Game.after(Game.State{inn, True{}, so, sb, away, home, rej}, m)):
  match m:
    case None{}:
      (wa, wh)
    case Some{h}:
      match h:
        case Game.Half{bs, l, o}:
          close_top(o, inn, so, sb, away, home, rej, bs, l, wm, wa, wh)

def after_bot(m: Maybe<Game.Half>, -inn: Nat, -so: Nat, -sb: Game.Bases, -away: Game.Line, -home: Game.Line, -rej: Nat,
  wm: OkM(0n, m), wa: {Game.line_bat(away) == Game.line_demand(away) : Nat}, wh: {Game.line_bat(home) == Nat.add(Game.count(sb), Game.line_demand(home)) : Nat})
  -> SBal(Game.after(Game.State{inn, False{}, so, sb, away, home, rej}, m)):
  match m:
    case None{}:
      (wa, wh)
    case Some{h}:
      match h:
        case Game.Half{bs, l, o}:
          close_bot(o, inn, so, sb, away, home, rej, bs, l, wm, wa, wh)

def step_bal(s: Game.State, +p: Game.Play, w: SBal(s)) -> SBal(Game.step(s, p)):
  match s:
    case Game.State{+inn, top, +so, +sb, +away, +home, +rej}:
      match top:
        case True{}:
          (+wa, wh) = w
          after_top(Game.slots(p, Game.Half{sb, away, so}), inn, so, sb, away, home, rej,
            slots_bal(p, Game.Half{sb, away, so}, wa), wa, wh)
        case False{}:
          (wa, +wh) = w
          after_bot(Game.slots(p, Game.Half{sb, home, so}), inn, so, sb, away, home, rej,
            slots_bal(p, Game.Half{sb, home, so}, wh), wa, wh)

def run_bal(ps: List<&2, Game.Play>, +s: Game.State, w: SBal(s)) -> SBal(Game.run(ps, s)):
  match ps:
    case Nil{}:
      w
    case Con{+p, rest}:
      run_bal(rest, Game.step(s, p), step_bal(s, p, w))

def start_bal() -> SBal(Game.start()):
  ({==}, {==})

def bal_away(-s: Game.State, w: SBal(s)) -> {Game.away_supply(s) == Game.away_demand(s) : Nat}:
  (a, h) = w
  a

def bal_home(-s: Game.State, w: SBal(s)) -> {Game.home_supply(s) == Game.home_demand(s) : Nat}:
  (a, h) = w
  h

def Laws.box_balances_away(ps):
  bal_away(Game.run(ps, Game.start()), run_bal(ps, Game.start(), start_bal()))

def Laws.box_balances_home(ps):
  bal_home(Game.run(ps, Game.start()), run_bal(ps, Game.start(), start_bal()))
