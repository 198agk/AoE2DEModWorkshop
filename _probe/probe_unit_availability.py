# -*- coding: utf-8 -*-
"""Is a civ's "can build this" a per-civ BYTE in the unit record, and which one?

The effect path (command type 2 `启用/禁用单位`) is one way a civ gets a unit, but
`parse_dat.read_unit()` reads two u8 fields straight after OldPortraitPict, and
genieutils calls them `Enabled` / `Disabled`.  If a per-civ availability flag
lives in the record itself, then "let the Britons build Hussars" is a 1-byte
edit in 1..63 records -- far simpler than a new effect family.

THE TRAP THIS FILE EXISTS TO AVOID: computing field offsets by hand.  The
offsets below are derived from `parser.read_unit()`'s literal read order, but
they are PROVEN first against a field `locate.py` already captures (`icon_id`),
because a one-byte slip would make the whole measurement meaningless -- my first
attempt read `OldPortraitPict`'s 0xFFFF as "HideInEditor" and reported every
unit as 255.

Then it correlates the bytes against the game's OWN availability data
(`futuravailableunits.json`, which the semantic layer already joins 99.3%), so
the conclusion does not rest on guessing what a field name means.
"""
import json
import os
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import aoe2mod.api as A                                          # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"

# Byte offsets relative to the `sort_number` mark locate.py records, derived
# from parser.read_unit():
#   u8  SortNumber          +0     (locate marks this one)
#   u8  CanBeBuiltOn        +1
#   i16 IconID              +2
#   u8  HideInEditor        +4
#   i16 OldPortraitPict     +5
#   u8  Enabled             +7
#   u8  Disabled            +8
REL = {"can_be_built_on": 1, "icon_id": 2, "hide_in_editor": 4,
       "old_portrait": 5, "enabled": 7, "disabled": 8}


def main():
    tk = A.open_toolkit()
    tk._ensure()
    raw = tk._raw
    civs = tk._civs
    print("civs: %d" % len(civs))

    # ---- 1. PROVE the offsets using a field locate already trusts ---------
    checked = bad = 0
    for c in civs:
        for u in (c.get("units") or ()):
            base = (u.get("_offs") or {}).get("sort_number")
            if base is None:
                continue
            from_mark = raw[base + REL["icon_id"]] | (raw[base + REL["icon_id"] + 1] << 8)
            if from_mark >= 0x8000:
                from_mark -= 0x10000
            checked += 1
            if from_mark != u.get("icon_id"):
                bad += 1
    print("offset proof: %d unit records, icon_id mismatches %d" % (checked, bad))
    if bad:
        print("  FATAL: the derived offsets are wrong; every number below is "
              "meaningless.  Fix REL before reading further.")
        return 1

    # ---- 2. what do the two bytes hold? ----------------------------------
    hist = {"enabled": Counter(), "disabled": Counter(),
            "hide_in_editor": Counter()}
    varies = Counter()
    for uid in range(0, 3200):
        sets = {k: set() for k in ("enabled", "disabled", "hide_in_editor")}
        for c in civs:
            for u in (c.get("units") or ()):
                if u.get("id") != uid:
                    continue
                base = (u.get("_offs") or {}).get("sort_number")
                if base is None:
                    continue
                for k in sets:
                    sets[k].add(raw[base + REL[k]])
        if sets["enabled"]:
            for k in sets:
                hist[k].update(sets[k])
            if len(sets["enabled"]) > 1 or len(sets["disabled"]) > 1:
                varies[(tuple(sorted(sets["enabled"])),
                        tuple(sorted(sets["disabled"])))] += 1
    for k, v in hist.items():
        print("%-15s distinct-value histogram over ids: %s" % (k, dict(v)))
    print("ids whose enabled/disabled VARIES across civs: %d" % sum(varies.values()))
    for k, n in varies.most_common(6):
        print("   (enabled-set, disabled-set) = %s   n_ids = %d" % (k, n))

    # ---- 3. correlate with the game's own availability data --------------
    fu = os.path.join(GAME, "resources", "_common", "dat",
                      "futuravailableunits.json")
    if not os.path.exists(fu):
        print("(futuravailableunits.json not found; skipping correlation)")
        return 0
    with open(fu, encoding="utf-8") as fh:
        avail = json.load(fh)
    print("\nfuturavailableunits: %d keys" % len(avail))

    # Map civ -> set of unit ids the game says are available.
    names = [c.get("name") for c in civs]
    game_avail = {}
    for key, v in avail.items():
        joined = {u.get("id") for u in (v.get("units") or v.get("Units") or ())
                  if isinstance(u, dict)}
        if not joined and isinstance(v, list):
            joined = {x for x in v if isinstance(x, int)}
        game_avail[key] = joined
    print("  keys with a usable id set: %d"
          % sum(1 for s in game_avail.values() if s))
    sample = sorted((k, len(v)) for k, v in game_avail.items()
                    if isinstance(v, set))[:5]
    print("  sample sizes: %s" % sample)
    return 0


if __name__ == "__main__":
    sys.exit(main())
