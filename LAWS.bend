# The laws. Each is a claim about the scorebook (game.bend) or the simulator
# (sim.bend) that must hold for every input; PROOF.bend proves them, and
# `bend PROOF.bend` must print ALL PROOFS CHECK before any commit.
import Base
import ./game.bend as Game
import ./sim.bend as Sim

# LAW: the parallel tree plays and counts exactly 2^d games, however the
# work splits across cores or GPU lanes.
law sims_all_counted:
  for +d: Nat
  for +i: U32
  for +c: Sim.Ctx
  {Sim.total(Sim.tree(d, i, c)) == Sim.pow2(d) : Nat}

# LAW: whatever the plays, the scorebook never shows three or more outs.
law outs_below_three:
  for ps: List<&2, Game.Play>
  {Nat.is_lt(Game.outs(Game.replay(Game.start(), ps)), 3n) == True{} : Bool}

# LAW (OBR 9.03(c), "How to Prove a Box Score"): for each team, the batters
# who completed a plate appearance equal its runs, plus the putouts by the
# defense, plus runners left on base, plus runners still on base.
law box_balances_away:
  for +ps: List<&2, Game.Play>
  {Game.away_supply(Game.replay(Game.start(), ps)) == Game.away_demand(Game.replay(Game.start(), ps)) : Nat}

law box_balances_home:
  for +ps: List<&2, Game.Play>
  {Game.home_supply(Game.replay(Game.start(), ps)) == Game.home_demand(Game.replay(Game.start(), ps)) : Nat}

# LAW: a play never takes a run off the board.
law runs_never_decrease_away:
  for +s: Game.State
  for +p: Game.Play
  {Nat.is_le(Game.away_runs(s), Game.away_runs(Game.step(s, p))) == True{} : Bool}

law runs_never_decrease_home:
  for +s: Game.State
  for +p: Game.Play
  {Nat.is_le(Game.home_runs(s), Game.home_runs(Game.step(s, p))) == True{} : Bool}
