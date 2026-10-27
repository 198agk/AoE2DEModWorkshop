# -*- coding: utf-8 -*-
"""Map resource words to cost SLOTS by the slot's own `type`, not by position.

The defect this fixes: writing Loom's gold cost landed on slot 2 and produced
`(-1, 5, 0)` -- an empty slot carrying a non-zero amount, which is not a shape
the game ever writes. Loom's gold is in slot 0 as `type 3, amount 50`.

A tech's three cost slots are NOT a fixed food/wood/gold/stone order. Each slot
carries its own `type`, the slots come in whatever order the record chose, and an
unused slot is `type -1`. So the mapping has to be measured per tech: the offset
table carries each slot's TYPE beside its offset, and the writer finds the slot
whose type matches the resource the player named.

The resource type ids are the game's own: 0 food, 1 wood, 2 stone, 3 gold.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import aoe2mod.dat.locate as L          # noqa: E402
import aoe2mod.dat.parser as P          # noqa: E402

DAT = os.path.join(r"d:\games\steam\steamapps\common\AoE2DE",
                   "resources", "_common", "dat", "empires2_x2_p1.dat")
OUT = os.path.join(ROOT, "_golden", "tech_offsets.json")

RESOURCE_IDS = {"food": 0, "wood": 1, "stone": 2, "gold": 3}


def main():
    raw, _ = P.load_dat(DAT)
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    stage8 = next(t for t in p.stage_offsets if t[0].startswith("8 Civs"))
    techs = L.locate_techs(raw, stage8[2], 54)

    out = {"gv": 54, "resource_ids": RESOURCE_IDS, "techs": {}}
    n_rt = n_cost = n_slots = 0
    for idx, t in enumerate(techs):
        entry = {}
        rts = [d.get("_off_research_time")
               for d in (t.get("research_locations") or [])]
        rts = [o for o in rts if isinstance(o, int)]
        if not rts and isinstance(t.get("_off_research_time"), int):
            rts = [t["_off_research_time"]]
        if rts:
            entry["research_time"] = rts
            n_rt += 1
        slots = []
        for c in t.get("costs") or []:
            off = c.get("_off_amount")
            if isinstance(off, int):
                slots.append({"type": int(c.get("type", -1)), "offset": off})
        if slots:
            entry["cost_slots"] = slots
            n_cost += 1
            n_slots += len(slots)
        if entry:
            out["techs"][str(idx)] = entry

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, separators=(",", ":"))

    print("wrote %s (%.1f KB)" % (OUT, os.path.getsize(OUT) / 1024.0))
    print("techs: %d | research_time: %d | cost slots: %d entries / %d slots"
          % (len(out["techs"]), n_rt, n_cost, n_slots))
    for probe in ("22", "67"):
        print("  tech %-4s %s" % (probe, out["techs"].get(probe)))
    loom = out["techs"].get("22") or {}
    gold = [s for s in loom.get("cost_slots", []) if s["type"] == RESOURCE_IDS["gold"]]
    print("  Loom gold slot:", gold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
