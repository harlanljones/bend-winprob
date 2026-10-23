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
