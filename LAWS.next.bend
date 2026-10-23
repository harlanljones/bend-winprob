# Laws not yet proven. PROOF.bend does not import this file; a law moves to
# LAWS.bend, unchanged, once PROOF.bend proves it.
import Base
import ./game.bend as Game
import ./sim.bend as Sim

# LAW: a play never takes a run off the board.
law runs_never_decrease_away:
  for +s: Game.State
  for p: Game.Play
  {Nat.is_le(Game.away_runs(s), Game.away_runs(Game.step(s, p))) == True{} : Bool}

law runs_never_decrease_home:
  for +s: Game.State
  for p: Game.Play
  {Nat.is_le(Game.home_runs(s), Game.home_runs(Game.step(s, p))) == True{} : Bool}

# LAW (OBR 9.03(c), "How to Prove a Box Score"): for each team, the batters
# who completed a plate appearance equal its runs, plus the putouts by the
# defense, plus runners left on base, plus runners still on base.
law box_balances_away:
  for +ps: List<&2, Game.Play>
  {Game.away_supply(Game.replay(Game.start(), ps)) == Game.away_demand(Game.replay(Game.start(), ps)) : Nat}

law box_balances_home:
  for +ps: List<&2, Game.Play>
  {Game.home_supply(Game.replay(Game.start(), ps)) == Game.home_demand(Game.replay(Game.start(), ps)) : Nat}
