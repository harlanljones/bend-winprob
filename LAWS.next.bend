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
