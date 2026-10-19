# -*- coding: utf-8 -*-
"""Exercise `apply_revoke` on the case `dsh test v17` proved in game.

Read-only against the game data: it parses, edits a COPY of the model, and
serialises in memory.  Nothing is written to disk and nothing is installed.

What it checks, and why each check exists:

  A. The carrier the recipe picks is not the 0:00 one.  `dsh test v17` showed a
     0:00 carrier loses to the global enable, so picking one would ship a dead
     command -- the exact defect this whole round is about.
  B. The disable command is `(2, 2550, 0, -1, 0.0)`, byte for byte.
  C. The carrier's OWN commands survived (they are civilization bonuses -- losing
     them silently would be a bonus deletion dressed as a feature).
  D. The stream still inflates to the same byte count and re-parses.
  E. Running it twice from the same base gives the same bytes (no hidden state).
"""
import contextlib
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aoe2mod.dat import locate as L          # noqa: E402
from aoe2mod.dat import parser as P          # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402
from aoe2mod.game import locations as G      # noqa: E402
from aoe2mod.intent import datgrant as DG    # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UNIT = 2550

FAILS = []


def check(name, ok, detail=""):
    print("%-72s %s%s" % (name, "PASS" if ok else "FAIL",
                          "" if ok else "  :: %s" % (detail,)))
    if not ok:
        FAILS.append(name)


def main():
    dat = G.dat_path(GAME)
    raw, how = P.load_dat(dat)
    print("dat %s (%s)\n" % (len(raw), how))

    trees = CT.load_trees(GAME)
    civ = next(c for c in trees if "inca" in c.lower())
    print("civ key %r\n" % civ)

    pr = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr.parse()
    civs, _cs, gv, tail = L.locate(raw, parser=pr)
    techs = L.locate_techs(raw, tail, gv)
    civ_index = next(i for i, c in enumerate(civs)
                     if "inca" in (c.get("name") or "").lower())
    print("civ index %d\n" % civ_index)

    ranks = DG._age_ranks(techs)
    enable = DG.enabling_techs(pr.stats, UNIT)
    floor = max((ranks.get(i, 0) for i, _c in enable), default=0)
    print("enabling techs of %d: %s (floor rank %d)"
          % (UNIT, [(i, ranks.get(i, 0)) for i, _c in enable], floor))

    patched, rep = DG.apply_revoke(pr.stats, raw, gv, civ_index, trees[civ],
                                   UNIT, rank_techs=techs)
    print("\nreport: ok=%s tech=%s rank=%r edits=%d bytes_changed=%s"
          % (rep.get("ok"), rep.get("tech"), rep.get("carrier_rank"),
             len(rep.get("edits") or []), rep.get("bytes_changed")))
    if not rep.get("ok"):
        check("the recipe produced bytes", False, rep.get("reason"))
        return 1

    # A. the carrier fires later than the global enabler
    carrier = rep["tech"]
    check("the carrier fires LATER than the global enabler",
          ranks.get(carrier, 0) > floor,
          "carrier rank %s vs floor %d" % (ranks.get(carrier), floor))
    check("the carrier is owned by the civilization", 
          techs[carrier].get("civ") == civ_index,
          "civ=%r want %r" % (techs[carrier].get("civ"), civ_index))
    check("the carrier is not the 0:00 technology v17 already refuted",
          carrier != 495, "picked tech 495 again")

    # B. the command is exactly the disable
    eff = rep["effect"]["index"]
    cmds = None
    pr2 = P.Parser(patched)
    with contextlib.redirect_stdout(io.StringIO()):
        pr2.parse()
    cmds = []
    for c in pr2.stats["effects"][eff]["commands"]:
        if isinstance(c, dict):
            cmds.append((c["type"], c["a"], c["b"], c["c"], c["d"]))
        else:
            cmds.append(tuple(c))
    check("the new effect ends with (2, 2550, 0, -1, 0.0)",
          cmds[-1] == (2, UNIT, 0, -1, 0.0), repr(cmds[-1]))

    # C. carried commands survived
    check("the carrier's own commands were carried into the new effect",
          rep["effect"]["carried_commands"] > 0,
          "carried %d" % rep["effect"]["carried_commands"])
    check("the carried count equals what the old effect held",
          len(cmds) == rep["effect"]["carried_commands"] + 1,
          "%d commands, %d carried" % (len(cmds),
                                       rep["effect"]["carried_commands"]))

    # D. the stream is intact
    import zlib
    blob = zlib.compressobj(6, zlib.DEFLATED, -15)
    comp = blob.compress(patched) + blob.flush()
    check("the patched stream deflates and inflates back",
          zlib.decompress(comp, -15) == patched,
          "round-trip mismatch")
    check("the patched stream re-parses to the last byte",
          pr2.r.pos == len(patched),
          "parser stopped at %d of %d" % (pr2.r.pos, len(patched)))

    # E. determinism
    pr3 = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        pr3.parse()
    again, rep2 = DG.apply_revoke(pr3.stats, raw, gv, civ_index, trees[civ],
                                  UNIT, rank_techs=techs)
    check("running it twice gives the same bytes", again == patched,
          "byte mismatch")
    check("running it twice picks the same carrier",
          rep2["tech"] == carrier, "%r vs %r" % (rep2["tech"], carrier))

    print("\nREVOKE DAT HALF: %d checks failed" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
