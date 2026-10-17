# -*- coding: utf-8 -*-
"""Probe the global Techs block using the AUTHORITATIVE walker to advance, and
a second cursor to record field offsets.  Any layout mistake in our second
cursor is caught by asserting both cursors finish on the same offset.

Ground truth for AoE2 DE (well-known values, not read from the .dat):
    Loom 25 | Feudal Age 130 | Castle Age 160 | Imperial Age 190
"""
import contextlib
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aoe2mod.dat import parser as P
from aoe2mod.dat import locate as L

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
SUB = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed"
LEGACY = os.path.join(SUB, "297820_10 倍资源文明联盟3倍科技",
                      "resources", "_common", "dat", "empires2_x2_p1.dat")

GV_C31 = P.GV_C31
GV_MATT = P.GV_MATT
KNOWN = {"Loom": 25, "Feudal Age": 130, "Castle Age": 160, "Imperial Age": 190}


def hand_walk(r, gv):
    """Walk one tech recording offsets, returning (fields, end)."""
    t = {"start": r.o}
    r.i16_array(6)                             # RequiredTechs (12 B, NOT i32)
    for _ in range(3):
        P.read_research_resource_cost(r)
    r.i16()                                    # RequiredTechCount
    t["civ"] = r.i16()
    r.i16()                                    # FullTechMode
    t["_off_research_time_scalar"] = None
    if gv < GV_C31:
        t["_off_research_time_scalar"] = r.o
        t["research_time"] = r.i16()
    if gv >= GV_MATT:
        if P.GV_C18 <= gv <= P.GV_LatestDE2:
            r.i32(); r.i32()
        else:
            r.i16(); r.i16()
    t["effect_id"] = r.i16()
    t["type"] = r.i16()
    t["icon_id"] = r.i16()
    if gv < GV_C31:
        r.u8()
    r.i32(); r.i32()                           # LanguageDLLHelp / TechTree
    if gv < GV_C31:
        r.i32()                                # HotKey
    t["name"] = r.debug_string()[2]
    if P.GV_C15 <= gv <= P.GV_LatestDE2:
        r.u8()                                 # Repeatable
    locs = []
    t["_off_location_count"] = None
    if GV_C31 <= gv <= P.GV_LatestDE2:
        t["_off_location_count"] = r.o
        m = r.i16()
        for _ in range(m):
            off = r.o
            loc_id = r.i16()
            locs.append({"_off_research_time": off + 2,
                         "_off": off,
                         "location_id": loc_id,
                         "research_time": r.i16(),
                         "button_id": r.u8(),
                         "hotkey_id": r.i32()})
    t["locations"] = locs
    t["end"] = r.o
    return t


def report(tag, path):
    print("=" * 78)
    print(tag)
    data, how = P.load_dat(path)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, civs_start, gv, tail = L.locate(data, parser=p)
    n = struct.unpack_from("<h", data, tail)[0]
    print("  gv=%d  tail=0x%X  declared tech count=%d" % (gv, tail, n))

    auth = L.Orec(data, tail + 2, gv=gv)       # authoritative advance
    techs = []
    drift = 0
    for i in range(n):
        start = auth.o
        P.read_tech(auth)                       # authoritative end
        end_auth = auth.o
        sub = L.Orec(data, start, gv=gv)
        t = hand_walk(sub, gv)
        if sub.o != end_auth:
            drift += 1
            if drift <= 3:
                print("  DRIFT tech %d: hand %d vs authoritative %d (delta %d) name=%r"
                      % (i, sub.o, end_auth, end_auth - sub.o, t["name"]))
        t["index"] = i
        techs.append(t)
    print("  walked %d techs, end 0x%X (stream %d, leftover %d), drift=%d"
          % (len(techs), auth.o, len(data), len(data) - auth.o, drift))

    hist = {}
    for t in techs:
        hist[len(t["locations"])] = hist.get(len(t["locations"]), 0) + 1
    print("  locations-per-tech histogram: %s" % dict(sorted(hist.items())))
    disagree = [t["index"] for t in techs
                if len({l["research_time"] for l in t["locations"]}) > 1]
    print("  techs whose locations disagree on research_time: %d" % len(disagree))
    multi = [t for t in techs if len(t["locations"]) > 1]
    print("  techs with >1 location: %d" % len(multi))
    for t in multi[:3]:
        print("    id %-5d %-28r %s" % (t["index"], t["name"],
              [(l["location_id"], l["research_time"]) for l in t["locations"]]))

    print("  --- known-value cross-check ---")
    hits = 0
    for t in techs:
        nm = (t["name"] or "").strip()
        if nm in KNOWN:
            hits += 1
            if gv >= GV_C31:
                vals = [l["research_time"] for l in t["locations"]]
                ok = "OK" if vals and vals[0] == KNOWN[nm] else "CHECK"
                print("    id %-5d %-14s locs=%d times=%s expect %d  %s"
                      % (t["index"], nm, len(vals), vals, KNOWN[nm], ok))
            else:
                v = t["research_time"]
                print("    id %-5d %-14s scalar=%d expect %d  %s"
                      % (t["index"], nm, v, KNOWN[nm], "OK" if v == KNOWN[nm] else "CHECK"))
    if not hits:
        print("    (no known names matched; dumping first 5 names: %s)"
              % [t["name"] for t in techs[:5]])
    return techs, gv


for tag, path in (("BASE VER 8.9", BASE), ("LEGACY VER 7.8", LEGACY)):
    if not os.path.exists(path):
        print("MISSING", path)
        continue
    report(tag, path)
