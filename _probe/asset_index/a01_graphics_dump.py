#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
a01_graphics_dump.py -- dump every dat Graphic record + inventory the .sld files on disk.

Purpose: establish empirically how a dat Graphic's identity (name / file / slp / id)
corresponds to an actual .sld filename in resources\\_common\\drs\\graphics\\.

Read-only on the game tree. Outputs JSON under _probe\\asset_index\\.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATPARSE = os.path.abspath(os.path.join(HERE, "..", "datparse"))
sys.path.insert(0, DATPARSE)

import parse_dat as P  # noqa: E402

DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat"
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
POMPEII = r"D:\Games\Steam\steamapps\common\AoE2DE\modes\Pompeii\resources\_common\drs\graphics"
SMALLTREES = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\small-trees"

OUT = HERE


def main():
    t0 = time.time()
    data, how = P.load_dat(DAT)
    print("dat %s  size=%d" % (how, len(data)))

    p = P.Parser(data)
    st = p.parse()
    print("parse done in %.1fs, leftover %d" % (time.time() - t0, len(data) - p.r.pos))

    # --- graphics -----------------------------------------------------------
    gfx = st["graphics"]
    ptrs = P.Parser  # unused
    print("graphics count field : %d" % st["graphic_count"])
    print("graphics nonzero ptr : %d" % st["graphic_pointers_nonzero"])
    print("graphics decoded     : %d" % len(gfx))

    # graphic index array index -> graphic body. The bodies are read in pointer
    # order, so body position i corresponds to the i-th NONZERO pointer.
    # Reconstruct that mapping here from the byte buffer so the index is exact.
    r = P.Reader(data)
    r.pos = 0x44DC0
    gcount = r.i16()
    ptrs = r.i32_array(gcount)
    body_index_of_slot = {}
    nz = 0
    for i, pt in enumerate(ptrs):
        if pt != 0:
            body_index_of_slot[i] = nz
            nz += 1
    print("pointer slots=%d nonzero=%d (body order matches decode order: %s)"
          % (gcount, nz, "YES" if nz == len(gfx) else "NO"))

    graph_out = []
    for slot, bi in body_index_of_slot.items():
        g = gfx[bi]
        graph_out.append({
            "slot": slot,
            "body_index": bi,
            "name": g["name"],
            "file": g["file"],
            "slp": g["slp"],
            "id": g["id"],
            "frame_count": g["frame_count"],
            "angle_count": g["angle_count"],
            "layer": g["layer"],
            "particle_effect": g["particle_effect"],
        })
    with open(os.path.join(OUT, "graphics_raw.json"), "w", encoding="utf-8") as fh:
        json.dump(graph_out, fh, ensure_ascii=False)
    print("wrote graphics_raw.json (%d)" % len(graph_out))

    # --- .sld inventory -----------------------------------------------------
    def list_sld(d):
        try:
            return sorted(f for f in os.listdir(d) if f.lower().endswith(".sld"))
        except FileNotFoundError:
            return []

    sld = list_sld(GFXDIR)
    print("drs\\graphics .sld : %d" % len(sld))
    sld_pomp = list_sld(POMPEII)
    sld_small = list_sld(SMALLTREES)
    print("pompeii .sld: %d   small-trees .sld: %d" % (len(sld_pomp), len(sld_small)))

    with open(os.path.join(OUT, "sld_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump({"graphics": sld, "pompeii": sld_pomp, "small_trees": sld_small},
                  fh, ensure_ascii=False)

    # --- first 40 graphics, look at the shape of name/file ------------------
    print("\nfirst 40 graphics (slot, name, file, slp):")
    for g in graph_out[:40]:
        print("  %5d  %-28s %-28s slp=%-7d id=%-6d fc=%-5d ac=%d"
              % (g["slot"], g["name"][:28], g["file"][:28], g["slp"], g["id"],
                 g["frame_count"] or 0, g["angle_count"] or 0))

    # --- how often is file == name ? ---------------------------------------
    same = sum(1 for g in graph_out if g["name"] == g["file"])
    print("\nname == file : %d / %d" % (same, len(graph_out)))

    # --- does the 'file' field ever look like a .sld basename? --------------
    sldset = set(sld)
    sld_stem = {}
    for f in sld:
        base = f[:-4]
        if base.endswith("_x1") or base.endswith("_x2"):
            base = base[:-3]
        sld_stem.setdefault(base.lower(), []).append(f)
    hits_name = sum(1 for g in graph_out if g["name"] and
                    g["name"].lower().replace(".sld", "") in sld_stem)
    hits_file = sum(1 for g in graph_out if g["file"] and
                    g["file"].lower().replace(".sld", "") in sld_stem)
    print("graphics whose NAME (minus .sld/_x?) is an .sld stem: %d" % hits_name)
    print("graphics whose FILE (minus .sld/_x?) is an .sld stem: %d" % hits_file)


if __name__ == "__main__":
    main()
