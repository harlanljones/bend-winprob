# The program live.py calls once per play. One argument (the last on the
# command line):
#   depth|seed|awayCum|homeCum|plays|mode
# depth: 2^depth simulated games; seed: U32; awayCum/homeCum: 7 cumulative
# thresholds out of 10000 (K,O,W,S,D,T,H; last 10000) for each side at bat;
# plays: ';'-separated 4-char codes, slots r3 r2 r1 batter, chars - X R 1 2 3;
# mode: cpu or gpu. Prints STATE, LINE and SIM lines, or one ERROR line.
import Base
import ./game.bend as Game
import ./sim.bend as Sim

type Input is Data:
  Input{depth: Nat, seed: U32, away: Sim.Rates, home: Sim.Rates, plays: List<&2, Game.Play>, gpu: Bool}

# Parsing
# -------

def req(-A: Data, m: Maybe<&2, A>, msg: String) -> Result<&2, &2, String, A>:
  match m:
    case None{}:
      Fail{msg}
    case Some{x}:
      Done{x}

def dest(c: Char) -> Maybe<&2, Game.Dest>:
  match c:
    case '-':
      Some{Game.Absent{}}
    case 'X':
      Some{Game.Out{}}
    case 'R':
      Some{Game.Run{}}
    case '1':
      Some{Game.To1{}}
    case '2':
      Some{Game.To2{}}
    case '3':
      Some{Game.To3{}}
    case _:
      None{}

def play4(m3: Maybe<&2, Game.Dest>, m2: Maybe<&2, Game.Dest>, m1: Maybe<&2, Game.Dest>, mb: Maybe<&2, Game.Dest>) -> Maybe<&2, Game.Play>:
  do Maybe<&2, Game.Play>:
    a : Game.Dest <- m3
    b : Game.Dest <- m2
    c : Game.Dest <- m1
    d : Game.Dest <- mb
    return Game.Play{a, b, c, d}

def play_chars(cs: List<&2, Char>, msg: String) -> Result<&2, &2, String, Game.Play>:
  match cs:
    case Con{c3, Con{c2, Con{c1, Con{cb, Nil{}}}}}:
      req(Game.Play, play4(dest(c3), dest(c2), dest(c1), dest(cb)), msg)
    case _:
      Fail{msg}

def play_of(+s: String, +i: Nat) -> Result<&2, &2, String, Game.Play>:
  play_chars(String.to_list(s), "play " ++ Nat.show(i) ++ ": bad code " ++ s)

def plays_cons(r: Result<&2, &2, String, Game.Play>, rest: Result<&2, &2, String, List<&2, Game.Play>>) -> Result<&2, &2, String, List<&2, Game.Play>>:
  do Result<&2, &2, String, List<&2, Game.Play>>:
    p : Game.Play <- r
    ps : List<&2, Game.Play> <- rest
    return p <> ps

def play_item(s: String, +i: Nat, rest: Result<&2, &2, String, List<&2, Game.Play>>) -> Result<&2, &2, String, List<&2, Game.Play>>:
  match s:
    case SNil{}:
      rest
    case SCon{c, t}:
      plays_cons(play_of(SCon{c, t}, i), rest)

def plays(xs: List<&2, String>, +i: Nat) -> Result<&2, &2, String, List<&2, Game.Play>>:
  match xs:
    case Nil{}:
      Done{Nil{}}
    case Con{h, t}:
      play_item(h, i, plays(t, 1n+i))

def u32(s: String, msg: String) -> Result<&2, &2, String, U32>:
  req(U32, U32.read(String.trim(s)), msg)

def rates7(xs: List<&2, String>, +what: String) -> Result<&2, &2, String, Sim.Rates>:
  match xs:
    case Con{k, Con{o, Con{w, Con{s, Con{d, Con{t, Con{h, Nil{}}}}}}}}:
      do Result<&2, &2, String, Sim.Rates>:
        k2 : U32 <- u32(k, what ++ ": bad K")
        o2 : U32 <- u32(o, what ++ ": bad O")
        w2 : U32 <- u32(w, what ++ ": bad W")
        s2 : U32 <- u32(s, what ++ ": bad S")
        d2 : U32 <- u32(d, what ++ ": bad D")
        t2 : U32 <- u32(t, what ++ ": bad T")
        h2 : U32 <- u32(h, what ++ ": bad H")
        return Sim.Rates{k2, o2, w2, s2, d2, t2, h2}
    case _:
      Fail{what ++ ": need 7 thresholds"}

def rates_ok(r: Sim.Rates) -> Bool:
  match r:
    case Sim.Rates{+k, +o, +w, +s, +d, +t, +h}:
      U32.is_eq(h, 10000) && U32.is_le(k, o) && U32.is_le(o, w)
        && U32.is_le(w, s) && U32.is_le(s, d) && U32.is_le(d, t) && U32.is_le(t, h)

def rates_top.go(ok: Bool, r: Sim.Rates, what: String) -> Result<&2, &2, String, Sim.Rates>:
  match ok:
    case True{}:
      Done{r}
    case False{}:
      Fail{what ++ ": thresholds must be nondecreasing and end at 10000"}

def rates_top(+r: Sim.Rates, +what: String) -> Result<&2, &2, String, Sim.Rates>:
  rates_top.go(rates_ok(r), r, what)

def rates(s: String, +what: String) -> Result<&2, &2, String, Sim.Rates>:
  do Result<&2, &2, String, Sim.Rates>:
    r : Sim.Rates <- rates7(String.split(s, ','), what)
    t : Sim.Rates <- rates_top(r, what)
    return t

def mode(s: String) -> Result<&2, &2, String, Bool>:
  match s:
    case "gpu":
      Done{True{}}
    case "cpu":
      Done{False{}}
    case _:
      Fail{"mode must be cpu or gpu"}

def sections(xs: List<&2, String>) -> Result<&2, &2, String, Input>:
  match xs:
    case Con{sd, Con{ss, Con{sa, Con{sh, Con{sp, Con{sm, Nil{}}}}}}}:
      do Result<&2, &2, String, Input>:
        d : Nat <- req(Nat, Nat.read(sd), "bad depth")
        seed : U32 <- u32(ss, "bad seed")
        a : Sim.Rates <- rates(sa, "awayCum")
        h : Sim.Rates <- rates(sh, "homeCum")
        ps : List<&2, Game.Play> <- plays(String.split(sp, ';'), 1n)
        g : Bool <- mode(String.trim(sm))
        return Input{d, seed, a, h, ps, g}
    case _:
      Fail{"need 6 '|'-separated sections"}

def parse(arg: String) -> Result<&2, &2, String, Input>:
  sections(String.split(arg, '|'))

# Output
# ------

def mark(b: Bool, c: String) -> String:
  match b:
    case True{}:
      c
    case False{}:
      "-"

def bases_str(b: Game.Bases) -> String:
  match b:
    case Game.Bases{b1, b2, b3}:
      mark(b1, "1") ++ mark(b2, "2") ++ mark(b3, "3")

def half_str(top: Bool) -> String:
  match top:
    case True{}:
      "T"
    case False{}:
      "B"

def state_line(+s: Game.State) -> String:
  "STATE " ++ Nat.show(Game.inning(s)) ++ " " ++ half_str(Game.is_top(s)) ++ " "
    ++ Nat.show(Game.outs(s)) ++ " " ++ bases_str(Game.bases(s)) ++ " "
    ++ Nat.show(Game.away_runs(s)) ++ " " ++ Nat.show(Game.home_runs(s)) ++ " "
    ++ Nat.show(Game.rejected(s))

def line_str(+l: Game.Line) -> String:
  Nat.show(Game.line_bat(l)) ++ " " ++ Nat.show(Game.line_runs(l)) ++ " "
    ++ Nat.show(Game.line_outs(l)) ++ " " ++ Nat.show(Game.line_lob(l))

def line_line(+s: Game.State) -> String:
  "LINE " ++ line_str(Game.away_line(s)) ++ " " ++ line_str(Game.home_line(s))

def sim_line(t: Sim.Tally) -> String:
  match t:
    case Sim.Tally{h, a, u}:
      "SIM " ++ Nat.show(h) ++ " " ++ Nat.show(a) ++ " " ++ Nat.show(u)

# The simulations: on the GPU (`!`) or across the CPU threads.
def tally(gpu: Bool, d: Nat, c: Sim.Ctx) -> Sim.Tally:
  match gpu:
    case True{}:
      Sim.tree!(d, 0, c)
    case False{}:
      Sim.tree(d, 0, c)

def run(inp: Input) -> String:
  match inp:
    case Input{d, seed, away, home, ps, gpu}:
      +st = Game.replay(Game.start(), ps)
      state_line(st) ++ "\n" ++ line_line(st) ++ "\n"
        ++ sim_line(tally(gpu, d, Sim.Ctx{st, away, home, seed}))

def report(r: Result<&2, &2, String, Input>) -> String:
  match r:
    case Fail{e}:
      "ERROR " ++ e
    case Done{inp}:
      run(inp)

def main() -> IO(Unit):
  do IO<Unit>:
    args : List<String> <- IO.args()
    IO.print(report(parse(Maybe.default(&1, String, List.last(&1, String, args), ""))))
