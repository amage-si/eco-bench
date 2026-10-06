import Base
import ../../Runika/font.bend as F
import ../../Runika/bytes.bend as B

# One-off differential check, kept as evidence for Runika c2b4af9: the new
# cmap_scan, which stops at the first segment ending at or after the code,
# against the previous full scan, for every code point 0..65535 of
# Liberation Sans. Prints the number of code points whose results differ.

def old_scan(n: Nat, +v: B.View, +count: U32, +i: U32, +code: U32) -> Result<&2, &2, String, U32>:
  match n:
    case 0n:
      Done{0}
    case 1n+p:
      do Result<&2, &2, String, U32>:
        +end : U32 <- B.u16(v, (14 + (i * 2) : U32))
        +start : U32 <- B.u16(v, (16 + (count * 2) + (i * 2) : U32))
        delta : U32 <- B.u16(v, (16 + (count * 4) + (i * 2) : U32))
        +at : U32 = (16 + (count * 6) + (i * 2) : U32)
        range : U32 <- B.u16(v, at)
        ok : Unit <- B.require(U32.is_le(start, end), "invalid cmap segment range")
        tail : U32 <- old_scan(p, v, count, (i + 1 : U32), code)
        F.cmap_hit(Bool.and(U32.is_ge(code, start), U32.is_le(code, end)), v, code, start, delta, range, at, tail)

def same(a: Result<&2, &2, String, U32>, b: Result<&2, &2, String, U32>) -> Bool:
  match a b:
    case Done{x} Done{y}:
      U32.is_eq(x, y)
    case Fail{e} Fail{f}:
      True{}
    case _ _:
      False{}

def mapped(r: Result<&2, &2, String, U32>) -> U32:
  match r:
    case Done{g}:
      Bool.to_u32(U32.is_ne(g, 0))
    case Fail{e}:
      0

type Tally is Data:
  Tally{differ: U32, mapped: U32}

def check(n: Nat, +v: B.View, +segs: U32, +code: U32, t: Tally) -> Tally:
  match n:
    case 0n:
      t
    case 1n+p:
      Tally{+d, +m} = t
      +now = F.cmap_scan(U32.to_nat(segs), v, segs, 0, code)
      +ok = same(now, old_scan(U32.to_nat(segs), v, segs, 0, code))
      check(p, v, segs, (code + 1 : U32), Tally{(d + Bool.to_u32(Bool.not(ok)) : U32), (m + mapped(now) : U32)})

def segments(r: Result<&2, &2, String, U32>) -> U32:
  match r:
    case Done{x}:
      (x / 2 : U32)
    case Fail{e}:
      0

def report(t: Tally, +segs: U32) -> String:
  Tally{d, m} = t
  "cmap segments: " ++ U32.show(segs) ++ "; code points 0..65535 compared; mapped to a glyph: " ++ U32.show(m) ++
    "; differing results: " ++ U32.show(d)

def run(r: Result<&2, &2, String, F.Font>) -> IO(Unit):
  match r:
    case Fail{e}:
      IO.print("font failed: " ++ e)
    case Done{F.Font{upem, asc, desc, gap, count, metrics, long, +cmap, hmtx, loca, glyf}}:
      +segs = segments(B.u16(cmap, 6))
      IO.print(report(check(65536n, cmap, segs, 0, Tally{0, 0}), segs))

def main() -> IO(Unit):
  do IO<Unit>:
    r : Result<&2, &2, String, F.Font> <- F.load("/usr/share/fonts/liberation/LiberationSans-Regular.ttf")
    run(r)
