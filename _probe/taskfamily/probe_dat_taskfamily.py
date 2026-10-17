# -*- coding: utf-8 -*-
"""Probe the .dat for the villager task-variant mechanism.

Question: what field, if any, in a unit record says "when I am tasked, swap me
onto another unit"?  Candidate found by reading the vendored genieutils source:
`unit::Bird::TaskSwapGroup` (uint8) -- AGE's tooltip says literally
"When tasking the unit, it will transform into another unit".

This script:
  1. walks every civ's unit records with the authoritative parser,
  2. records the Bird sub-struct (which intent_patch.walk_unit does NOT mark),
  3. reports the TaskSwapGroup distribution over the whole dat,
  4. reports a full table for the villager family ids,
  5. clusters units by an identical stat signature (the proposed data-driven
     heuristic) and checks whether 83 and 118 land in the same cluster.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import sys, os, struct, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DP = _HERE_PATH("_probe", "datparse")
sys.path.insert(0, DP)

import parse_dat as P
import intent_patch as IP

BASE = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
OUT = HERE

CANDIDATE_IDS = [83, 293, 1810, 56, 57, 118, 212, 120, 354, 122, 216, 123, 218,
                 124, 220, 579, 581, 259, 214, 592, 590, 156, 222, 2714, 2715]
LINKED_VILLAGERS = [56, 57, 83, 118, 120, 122, 123, 124, 156, 206, 212, 214,
                    216, 218, 220, 222, 259, 293, 354, 579, 581, 590, 592,
                    1810, 1891, 1892, 2333, 2334]

# ---------------------------------------------------------------------------
# Patch read_bird so the Bird sub-struct gets offsets AND the parsed values.
# intent_patch.walk_unit calls P.read_bird(r) directly, and read_bird in
# parse_dat discards everything -- so TaskSwapGroup has never been readable.
# ---------------------------------------------------------------------------
BIRD_BY_OFF = {}

class _PosProxy(object):
    """Wraps any reader object and adds an `at(key)` that returns the current
    byte offset.  The authoritative parse_dat.Reader has `pos` but no `at`;
    intent_patch.Orec has `at` but calls into the same `read_*` functions.
    Wrapping means ONE read_bird implementation serves both callers."""

    __slots__ = ("_r",)

    def __init__(self, r):
        object.__setattr__(self, "_r", r)

    def at(self, k):
        r = self._r
        off = r.pos if hasattr(r, "pos") else r.o
        m = getattr(r, "marks", None)
        if m is not None:
            m[k] = off          # so IP.Orec records the mark too
        return off

    def __getattr__(self, name):
        return getattr(self._r, name)

    def __setattr__(self, name, value):
        setattr(self._r, name, value)

def read_bird_marked(inner):
    r = _PosProxy(inner)
    start = r.at("bird_start")
    b = {}
    b["default_task_id"] = r.i16()
    b["search_radius"] = r.f32()
    b["work_rate"] = r.f32()
    n = r.i16()
    b["drop_sites"] = r.i16_array(n)
    r.at("task_swap_group")
    b["task_swap_group"] = r.u8()
    b["attack_sound"] = r.i16()
    b["move_sound"] = r.i16()
    r.u32(); r.u32()
    b["run_pattern"] = r.u8()
    tn = r.i16()
    b["task_count"] = tn
    for _ in range(tn):
        P.read_task(r)
    BIRD_BY_OFF[start] = b
    return b

P.read_bird = read_bird_marked

def bird_of(u):
    off = u["_offs"].get("bird_start")
    if off is None:
        return None
    return BIRD_BY_OFF.get(off)

def sig_stats(u, b):
    """Gameplay-stat signature.  Deliberately EXCLUDES identity (id, name,
    LanguageDLLName) and EXCLUDES the fields under test (task_swap_group,
    default_task_id, drop_sites) so the cluster result is not circular."""
    t50 = u.get("type50") or {}
    atk = tuple(sorted((a["class"], a["amount"]) for a in t50.get("attacks", [])))
    arm = tuple(sorted((a["class"], a["amount"]) for a in t50.get("armors", [])))
    costs = tuple(sorted((c["type"], c["amount"], c["flag"]) for c in u.get("costs", [])))
    tl = tuple(sorted((d["train_time"], d["unit_id"], d["button_id"])
                      for d in u.get("train_locations", [])))
    return (
        u["type"], u["class"], u["hit_points"], u["icon_id"],
        round(u["line_of_sight"], 6), u["garrison_capacity"], u["sort_number"],
        round(u.get("speed") or 0.0, 6),
        round(t50.get("max_range", 0.0), 6), round(t50.get("min_range", 0.0), 6),
        round(t50.get("reload_time", 0.0), 6), t50.get("accuracy"),
        t50.get("projectile_unit_id"), t50.get("frame_delay"),
        t50.get("displayed_attack"), t50.get("displayed_melee_armour"),
        round(t50.get("displayed_range", 0.0), 6),
        round(t50.get("displayed_reload_time", 0.0), 6),
        atk, arm, costs, tl,
        round(b.get("work_rate", 0.0), 6) if b else None,
        round(b.get("search_radius", 0.0), 6) if b else None,
    )

def main():
    data, how = P.load_dat(BASE)
    print("load_dat: %s  raw=%d" % (how, len(data)))
    civs, civs_start, gv, tail = IP.locate(data)
    print("gv=%s civs=%d civs_start=%d tail=%d" % (gv, len(civs), civs_start, tail))

    # ---- 1. census ------------------------------------------------------
    units = []           # one entry per PHYSICAL record
    distinct = {}        # id -> representative record
    for c in civs:
        for u in c["units"]:
            b = bird_of(u)
            rec = {
                "civ": c["index"], "civ_name": c["name"],
                "id": u["id"], "type": u["type"], "class": u["class"],
                "hp": u["hit_points"], "name": u["name"],
                "dll": u["_dll_name"], "icon": u["icon_id"],
                "speed": u.get("speed"), "los": u["line_of_sight"],
                "bird": b,
                "off_tsg": u["_offs"].get("task_swap_group"),
                "off_bird": u["_offs"].get("bird_start"),
                "off_hp": u["_offs"].get("hit_points"),
            }
            units.append(rec)
            if u["id"] not in distinct:
                distinct[u["id"]] = (u, b, rec)

    print("physical unit records: %d   distinct ids: %d" % (len(units), len(distinct)))

    # ---- 2. TaskSwapGroup census ---------------------------------------
    tsg = collections.Counter()
    for r in units:
        if r["bird"] is None:
            tsg[None] += 1
        else:
            tsg[r["bird"]["task_swap_group"]] += 1
    print("\n=== TaskSwapGroup census (physical records) ===")
    for k in sorted(tsg, key=lambda x: (-1 if x is None else x)):
        print("  tsg=%-6s : %d" % (k, tsg[k]))

    # distinct ids per tsg
    dtsg = collections.defaultdict(set)
    for uid, (u, b, rec) in distinct.items():
        dtsg[None if b is None else b["task_swap_group"]].add(uid)
    print("\n=== TaskSwapGroup -> distinct unit ids (nonzero groups only) ===")
    nonzero = {}
    for k in sorted([k for k in dtsg if k], key=lambda x: x):
        ids = sorted(dtsg[k])
        nonzero[k] = ids
        print("  tsg=%-4d  n=%-4d  ids=%s" % (k, len(ids), ids[:40]))
    with open(os.path.join(OUT, "task_swap_groups.json"), "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in nonzero.items()}, f, ensure_ascii=False, indent=1)

    # ---- 3. villager family table --------------------------------------
    print("\n=== villager family records (first civ that owns each id) ===")
    hdr = ("id", "type", "class", "hp", "name", "dll", "tsg", "deftask",
           "dropsites", "runpat", "workrate", "off_tsg")
    print("  " + " ".join("%-10s" % h for h in hdr))
    family_rows = []
    for uid in CANDIDATE_IDS + [206, 1891, 1892, 2333, 2334, 2714, 2715]:
        if uid not in distinct:
            print("  %-10s  -- ABSENT FROM DAT --" % uid)
            continue
        u, b, rec = distinct[uid]
        row = (uid, u["type"], u["class"], u["hit_points"], u["name"], u["_dll_name"],
               b["task_swap_group"] if b else None,
               b["default_task_id"] if b else None,
               b["drop_sites"] if b else None,
               b["run_pattern"] if b else None,
               b["work_rate"] if b else None,
               rec["off_tsg"])
        family_rows.append(row)
        print("  %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s %-10s" % row)
    with open(os.path.join(OUT, "villager_family.json"), "w", encoding="utf-8") as f:
        json.dump({"header": hdr, "rows": family_rows}, f, ensure_ascii=False, indent=1)

    # does linkedUnits.json's Villager roster match the dat's tsg groups?
    print("\n=== linkedUnits.json 'Villagers' roster vs dat ===")
    for uid in LINKED_VILLAGERS:
        if uid not in distinct:
            print("  %-6d ABSENT" % uid)
        else:
            u, b, rec = distinct[uid]
            print("  %-6d tsg=%-4s class=%-4s hp=%-6s name=%r" %
                  (uid, b["task_swap_group"] if b else "-", u["class"], u["hit_points"], u["name"]))

    # ---- 4. stat-signature clustering ----------------------------------
    print("\n=== stat-signature clustering ===")
    clusters = collections.defaultdict(list)
    for uid, (u, b, rec) in distinct.items():
        clusters[sig_stats(u, b)].append(uid)
    multi = {k: sorted(v) for k, v in clusters.items() if len(v) > 1}
    singleton = [v[0] for k, v in clusters.items() if len(v) == 1]
    print("  distinct ids           : %d" % len(distinct))
    print("  distinct signatures    : %d" % len(clusters))
    print("  multi-member clusters  : %d" % len(multi))
    print("  ids in multi clusters  : %d" % sum(len(v) for v in multi.values()))
    print("  singletons             : %d" % len(singleton))

    for uid in (83, 118, 293, 212):
        for k, v in multi.items():
            if uid in v:
                print("  id %-5d is in cluster of %d: %s" % (uid, len(v), v[:30]))
                break
        else:
            print("  id %-5d is a SINGLETON" % uid)

    # purity: for each multi-cluster, how many distinct tsg values?
    print("\n  === cluster purity vs TaskSwapGroup ===")
    pure = impure = 0
    impure_examples = []
    for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        g = set()
        for uid in v:
            b = distinct[uid][1]
            g.add(b["task_swap_group"] if b else None)
        if len(g) <= 1:
            pure += 1
        else:
            impure += 1
            if len(impure_examples) < 12:
                impure_examples.append((len(v), sorted(v)[:14], sorted(x for x in g if x is not None)))
    print("  pure clusters   : %d" % pure)
    print("  impure clusters : %d" % impure)
    for n, ids, g in impure_examples:
        print("    size=%-4d tsgs=%s ids=%s" % (n, g, ids))

    with open(os.path.join(OUT, "clusters.json"), "w", encoding="utf-8") as f:
        json.dump({"multi": {"|".join(map(str, k)): v for k, v in multi.items()},
                   "singletons": sorted(singleton)}, f, ensure_ascii=False, indent=1)

    # ---- 5. which ids share tsg with 83 ---------------------------------
    for probe in (83, 293, 118, 448, 4):
        if probe not in distinct:
            continue
        b = distinct[probe][1]
        if not b:
            print("\n  id %s has no Bird struct" % probe)
            continue
        g = b["task_swap_group"]
        print("\n  id %-5d tsg=%-4d -> group members: %s" % (probe, g, sorted(dtsg.get(g, []))))

    print("\nDONE")

if __name__ == "__main__":
    main()
