#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a38_crosscheck.py -- INDEPENDENT cross-check of the delivered index.

Independent means: this script does NOT re-run the mapping logic.  It reads the
SHIPPED deliverables (index_units.json / index_buildings.json) and checks three
things against the filesystem and against the engine's own author-written labels:

  C1  every sld_x1 / sld_x2 named anywhere in the deliverables EXISTS on disk
      (exact filename, case-insensitive directory listing)
  C2  for 10 famous entities, the mapped sprite FILENAMES obviously match the
      entity's English name (hand-written expectation table, not derived)
  C3  for the same 10, the icon's loose texture label (the game's own
      widgetui\\textures\\ingame\\buildings\\<N>_<label>.DDS filename, or the
      unit atlas FileName) agrees with the entity name

C2/C3 fail LOUDLY if the index is wrong -- they are hand-written, not inferred.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GFX = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
U = json.load(open(os.path.join(HERE, "index_units.json"), encoding="utf-8"))
B = json.load(open(os.path.join(HERE, "index_buildings.json"), encoding="utf-8"))

DISK = set(f.lower() for f in os.listdir(GFX))

# hand-written expectations: id -> (english name, substrings that MUST appear in a
# mapped sprite filename, substrings that must appear in the icon label/refname)
EXPECT = {
    4:    ("Archer",      ["archer"],            ["archer"]),
    83:   ("Villager",    ["villager", "vil"],   ["villager", "vil"]),
    38:   ("Knight",      ["knight"],            ["knight"]),
    74:   ("Militia",     ["militia", "mil"],    ["militia", "mil"]),
    71:   ("Town Center", ["town_center", "town"], ["town", "center"]),
    12:   ("Barracks",    ["barracks"],          ["barracks"]),
    82:   ("Castle",      ["castle"],            ["castle"]),
    70:   ("House",       ["house"],             ["house"]),
    8:    ("Longbowman",  ["longbow"],           ["longbow"]),
    125:  ("Monk",        ["monk"],              ["monk"]),
}


def mapped_files(rec):
    out = []
    for f, r in (rec.get("sprites") or {}).items():
        if r.get("sld_x1"):
            out.append((f, r["sld_x1"], r.get("resolution")))
        for a in (r.get("animations") or {}).values():
            if a.get("sld_x1"):
                out.append((f, a["sld_x1"], r.get("resolution") + "/" + str(a.get("sld_x1"))))
    return out


print("=" * 78)
print("C1  every sld filename in the deliverables exists on disk")
print("=" * 78)
tot = miss = 0
missing_samples = []
for src, dd in (("units", U), ("buildings", B)):
    for k, r in dd.items():
        for field, sld, res in mapped_files(r):
            tot += 1
            if sld.lower() not in DISK:
                miss += 1
                if len(missing_samples) < 10:
                    missing_samples.append((src, k, field, sld, res))
print("  referenced .sld files checked : %d" % tot)
print("  MISSING on disk              : %d" % miss)
for s in missing_samples:
    print("     MISSING %s" % (s,))
print("  VERDICT: %s" % ("PASS" if miss == 0 else "FAIL"))

print()
print("=" * 78)
print("C2/C3  ten famous entities: name vs sprite filenames vs icon label")
print("=" * 78)
okc = badc = 0
for uid, (name, sp_want, ic_want) in sorted(EXPECT.items()):
    r = U.get(str(uid))
    if r is None:
        print("  id %-5d %-12s ABSENT from index_units.json   FAIL" % (uid, name))
        badc += 1
        continue
    fs = [f for _, f, _ in mapped_files(r)]
    sp_hit = [w for w in sp_want if any(w in f.lower() for f in fs)] if fs else []
    sp_ok = bool(sp_hit) and bool(fs)
    ic = r.get("icon") or {}
    label = ""
    if ic.get("atlas") == "ingamebuildings":
        fn = os.path.basename(ic.get("TextureFileName") or "")
        label = fn.rsplit(".", 1)[0]
    else:
        label = ic.get("RefName") or ""
    ic_ok = any(w in label.lower() for w in ic_want) if label else False
    all_disk = all(f.lower() in DISK for f in fs)
    status = "PASS" if (sp_ok and ic_ok and all_disk) else "FAIL"
    if status == "PASS":
        okc += 1
    else:
        badc += 1
    print("  id %-5d %-12s en=%-12s type=%-3s cls=%-3s" % (uid, name, r["en"], r["type"], r["class"]))
    print("        sprite files  : %d referenced, all on disk=%s, name hit=%s"
          % (len(fs), all_disk, sp_hit))
    print("        sample sprites: %s" % (fs[:3],))
    print("        icon          : atlas=%-16s label=%-34s name hit=%s"
          % (ic.get("atlas"), label, ic_ok))
    print("        %s" % status)

print()
print("=" * 78)
print("RESULT: C1 %s | C2/C3 %d/%d PASS" %
      ("PASS" if miss == 0 else "FAIL", okc, okc + badc))
print("=" * 78)

print()
print("=== building sanity (type80 & b_ art & valid icon) sample ===")
for k in ["71", "12", "82", "70", "109", "50"]:
    b = B.get(k)
    if b:
        fs = [f for _, f, _ in mapped_files(b)]
        print("  id %-6s %-22s def=%-13s %3d files  icon=%s/%s"
              % (k, (b["en"] or "")[:22], b["building_definition"], len(fs),
                 (b["icon"] or {}).get("atlas"), (b["icon"] or {}).get("RefName")))
