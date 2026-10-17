# -*- coding: utf-8 -*-
r"""What decides WHEN a "make avail" tech fires?

v5/v6 hung the `type 2` enable command for unit 2550 on `tech 263 'Longbow (make
avail)'`, and the button waited for a Castle.  The Incas get the same unit in the
Dark Age because their enable lives on `tech 1350 'Champi Scout (Make avail)'`,
whose research location is building 12 (Barracks).

Both techs are location-less in the sense that matters -- 263 has
`[(-1,0,0,-1)]` and 1350 has `[(12,0,6,18230)]`.  Only one fires early.  The
cheapest structural difference to test is `RequiredTechs`: a make-avail tech that
requires the Castle tech cannot fire before a Castle exists, no matter where its
own research location points.

`walk_tech` reads `RequiredTechs` and THROWS IT AWAY (`r.i16_array(6)` with no
store) -- the same class of hole that hid `EnablingResearch` for fifteen rounds.
This probe reads it back from the raw bytes and puts the known-good make-avail
techs (Hun Tarkan, Mayan Plumed Archer, Spanish Conquistador) next to the British
candidates, so "which anchor fires at game start" is answered by comparison
instead of by argument.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import aoe2mod.dat.parser as P                                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

# Known-good per-civ "make avail" techs, plus the British candidates.
WANT = {
    263: "British: Longbow (make avail)      <- where v5/v6 put the command",
    381: "British: C-Bonus, 1/2 TCs",
    382: "British: C-Bonus, +1 Archer range",
    383: "British: C-Bonus, +25% Shepherd",
    403: "British: C-Bonus, archer range +1",
    1350: "GLOBAL : Champi Scout (Make avail)  <- what actually works",
    1: "Huns   : Tarkan (make avail)",
    26: "Mayans : Plumed Archer (make avail)",
    58: "Spanish: Conquistador (make avail)",
    84: "Spanish: Missionary (avail)",
    151: "GLOBAL : Archer (make avail)",
    87: "GLOBAL : Spearman (make avail)",
    85: "GLOBAL : Hand Cannoneer",
}


def load(path):
    raw, _how = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    return raw, pr.stats


def tech_heads(raw, gv, techs):
    """Read RequiredTechs + costs straight off each tech record's head.

    ``walk_tech`` consumes the same bytes but keeps only the costs, so this
    re-walk assumes nothing it has not been told: the array is positional, every
    record begins with 6 i16 required techs then 3 x (i16 type, i16 amount,
    u8 flag).
    """
    # Reproduce walk_tech's opening exactly, using the offsets the parser
    # recorded, so this cannot silently read a different place.
    out = {}
    for i in WANT:
        if not (0 <= i < len(techs)):
            continue
        out[i] = None
    return out


def main():
    raw, st = load(DAT)
    techs = st["techs"]
    effects = st["effects"]

    # The tech section starts right after the tail the parser recorded.  Rather
    # than re-derive it, read each record's own raw head by re-walking from the
    # section start with the same Reader the product uses.
    from aoe2mod.dat import locate as L
    tail = None
    # api records the tail in its parsed tuple; recover it from stage offsets.
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        try:
            pr.parse()
        except SystemExit:
            pass
    tech_stage = [t for t in pr.stage_offsets if t[0].startswith("9 Techs")]
    if not tech_stage:
        print("no Techs stage recorded")
        return
    start = tech_stage[0][1]

    # Tech records are VARIABLE-LENGTH at this game version: `ResearchLocations`
    # is an explicit array (Research.cpp:96-118, gv >= GV_C31), so walking from
    # the count field by a fixed stride drifts after the first two records and
    # prints plausible-looking garbage.  Use the product's own walker and read
    # the head by rewinding over it.
    r = L.Orec(raw, start, gv=pr.r.gv)
    n = r.i16()
    heads = []
    for _ in range(n):
        head = r.o
        req = list(r.i16_array(6))
        costs = []
        for _k in range(3):
            costs.append((r.i16(), r.i16(), r.u8()))
        r.o = head
        L.walk_tech(r)
        heads.append((req, costs))

    print("techs=%d  heads read=%d" % (len(techs), len(heads)))
    print()
    hdr = "%-5s %-44s %-8s %-9s  %-22s %s"
    print(hdr % ("id", "why", "civ", "eff", "RequiredTechs", "costs"))
    print("-" * 120)
    for i in sorted(WANT):
        if i >= len(heads):
            continue
        t = techs[i]
        req, costs = heads[i]
        req_s = str([x for x in req if x != -1])
        cost_s = str([c for c in costs if c[0] != -1])
        print("%-5d %-44s %-8s %-9s  %-22s %s"
              % (i, WANT[i][:44], t.get("civ"), t.get("effect_id"),
                 req_s, cost_s))

    print()
    print("=" * 78)
    print("Which of these techs carry a type-2 (Enable/Disable Unit) command?")
    print("=" * 78)
    for i in sorted(WANT):
        if i >= len(techs):
            continue
        eid = techs[i].get("effect_id")
        cs = []
        if 0 <= eid < len(effects):
            for c in effects[eid].get("commands") or []:
                if isinstance(c, dict):
                    cs.append(c)
                else:
                    cs.append({"type": c[0], "a": c[1], "b": c[2],
                               "c": c[3], "d": c[4]})
        t2 = [c for c in cs if c["type"] == 2]
        print("  tech %-5d cmds=%-3d type2=%s" % (i, len(cs), t2 if t2 else "none"))

    print()
    print("=" * 78)
    print("Is each anchor tech's effect SHARED?  (appending a command to a shared")
    print("effect would enable the unit for whoever else points at it)")
    print("=" * 78)
    by_effect = {}
    for i, t in enumerate(techs):
        by_effect.setdefault(t.get("effect_id"), []).append(i)
    for i in sorted(WANT):
        if i >= len(techs):
            continue
        eid = techs[i].get("effect_id")
        sharers = [j for j in by_effect.get(eid, []) if j != i]
        print("  tech %-5d -> effect %-5s  shared with %d techs %s"
              % (i, eid, len(sharers), sharers[:8] if sharers else ""))


if __name__ == "__main__":
    main()
