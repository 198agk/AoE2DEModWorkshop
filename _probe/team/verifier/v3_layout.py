"""Independent structural check: are the 1701 changed .dat offsets unit 83's HitPoints?

DERIVED BY HAND from _probe/source/genieutils (NOT from aoe2mod):
  Unit.cpp:57..84 for GV_C32 (VER 8.9):
    uint8  Type
    serializeDebugString(Name)        <- DE branch (gv==GV_LatestDE2, not > LatestDE2)
    int16  ID
    int32  LanguageDLLName            <- gv>=GV_C15 && gv<=GV_LatestDE2
    int32  LanguageDLLCreation
    int16  Class
    pair<int16,int16> StandingGraphic (4 bytes)
    int16  DyingGraphic
    int16  UndeadGraphic
    uint8  UndeadMode
    int16  HitPoints      <=== target
    float  LineOfSight
    uint8  GarrisonCapacity
  => bytes from ID field start to HitPoints field start = 2+4+4+2+4+2+2+1 = 21
  => expected ID == 83 (0x0053) at (hitpoints_offset - 21)

This uses ONLY stdlib + the raw bytes. No aoe2mod.
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")


def rd(name):
    with open(os.path.join(RAW, name), "rb") as f:
        return f.read()


g = rd("dat_game.raw")
m = rd("dat_mod.raw")
assert len(g) == len(m)

with open(os.path.join(HERE, "v2_dat_rawdiff.json"), encoding="utf-8") as f:
    d = json.load(f)
runs = d["runs"]  # list of [start, end]
print("runs loaded:", len(runs))


def i16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u8(b, o):
    return b[o]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


HP = "HitPoints"
DC = 21  # ID -> HitPoints distance

stats = {
    "offsets": 0,
    "game_id_is_83": 0,
    "mod_id_is_83": 0,
    "id_unchanged": 0,
    "hp_before_game_25": 0,
    "hp_before_mod_25": 0,
    "hp_after_game_1000": 0,
    "hp_after_mod_1000": 0,
    "undeadmode_zero": 0,
    "los_is_float_plausible": 0,
    "garrison_zero": 0,
}
id_hist = {}
los_hist = {}
example = []

for _run in runs:
    st, en = _run["start"], _run["end"]
    stats["offsets"] += 1
    o = st
    gid = i16(g, o - DC)
    mid = i16(m, o - DC)
    id_hist[gid] = id_hist.get(gid, 0) + 1
    if gid == 83:
        stats["game_id_is_83"] += 1
    if mid == 83:
        stats["mod_id_is_83"] += 1
    if gid == mid:
        stats["id_unchanged"] += 1
    if i16(g, o) == 25:
        stats["hp_before_game_25"] += 1
    if i16(m, o) == 25:
        stats["hp_before_mod_25"] += 1
    if i16(g, o) == 1000:
        stats["hp_after_game_1000"] += 1
    if i16(m, o) == 1000:
        stats["hp_after_mod_1000"] += 1
    if u8(g, o - 1) == 0:
        stats["undeadmode_zero"] += 1
    los = f32(g, o + 2)
    los_hist[round(los, 3)] = los_hist.get(round(los, 3), 0) + 1
    if 0.0 < los < 100.0:
        stats["los_is_float_plausible"] += 1
    if u8(g, o + 6) == 0:
        stats["garrison_zero"] += 1
    if len(example) < 3:
        example.append((st, gid, mid, i16(g, o), i16(m, o), los,
                        u8(g, o - 1), u8(g, o + 6)))

print("\n== structural field-identity stats over %d changed offsets ==" % stats["offsets"])
for k, v in stats.items():
    print("  %-24s %d" % (k, v))
print("\n  ID value at (offset-21), game raw, histogram:")
for k in sorted(id_hist):
    print("    id %-6d x%d" % (k, id_hist[k]))
print("\n  LineOfSight float at (offset+2), game raw, histogram:")
for k in sorted(los_hist):
    print("    %-8s x%d" % (k, los_hist[k]))
print("\n  examples (offset, gameID, modID, gameHP, modHP, gameLoS, undeadMode, garrisonCap):")
for e in example:
    print("   ", e)

# --- raw hexdump around the first and last changed offset ---
for label, off in (("FIRST", runs[0]["start"]), ("LAST", runs[-1]["start"])):
    a = off - 32
    b = off + 32
    print("\n== %s changed offset %d, bytes [%d,%d) ==" % (label, off, a, b))
    for name, buf in (("game", g), ("mod ", m)):
        row = buf[a:b]
        hexs = " ".join("%02x" % c for c in row)
        print("  %s: %s" % (name, hexs))
        mark = " " * (3 * 32) + "^^"
        # position of the changed run inside this window
        p = off - a
        print("  %s  %s%s" % (" " * 4, " " * (3 * p), "^^ <- changed int16"))

# --- distance between consecutive changed offsets, as multiples of the 21-byte delta ---
deltas = [runs[i + 1]["start"] - runs[i]["start"] for i in range(len(runs) - 1)]
from collections import Counter
c = Counter(deltas)
print("\n== consecutive-offset deltas, top 20 ==")
for k, v in c.most_common(20):
    print("   delta %-8d x%d" % (k, v))

# how many distinct offsets
print("\ndistinct changed offsets:", len({r["start"] for r in runs}))
