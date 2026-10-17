#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a19_failtax.py -- precise failure taxonomy.

Classes:
  F1 all graphic fields are -1
  F2 FileName == 'None'
  F3 FileName is a short non-DE token (X/W/E/M/R/...) => sub-part, not a file
  F4 FileName is a legacy debug token (CRCH3N0I, DMGA3_NN...)
  F5 FileName looks DE-style and anim-tagged, but the stem is not on disk
  F6 FileName is empty on the graphic
  F7 other
"""
import json, os, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
GFXDIR = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics"
G = json.load(open(os.path.join(HERE, "graphics_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(r"D:\Software\DeepSeek Harness\工作区2\_probe\semantic\unit_names.json",
                     encoding="utf-8"))

disk = set(f.lower()[:-4] for f in os.listdir(GFXDIR) if f.lower().endswith(".sld"))
slot2g = {g["slot"]: g for g in G}
FIELDS = ["standing_1", "standing_2", "dying", "undead", "attack_graphic",
          "attack_graphic2", "garrison_graphic", "spawning_graphic", "upgrade_graphic",
          "hero_glow_graphic", "idle_attack_graphic", "special_graphic",
          "construction_graphic", "snow_graphic", "destruction_graphic",
          "destruction_rubble_graphic", "researching_graphic",
          "research_completed_graphic"]
DE = re.compile(r"^[bunasp]_")

byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

tax = collections.Counter()
detail = collections.defaultdict(list)
for uid, per in sorted(byid.items()):
    u = per[sorted(per)[0]]
    files, negs, empties, others = [], 0, 0, 0
    for f in FIELDS:
        v = u.get(f)
        if not isinstance(v, int):
            continue
        if v < 0:
            negs += 1
            continue
        g = slot2g.get(v)
        if g is None:
            others += 1
            continue
        nm = (g["file"] or "").strip()
        if not nm:
            empties += 1
            continue
        files.append((f, nm))
    if not files:
        if negs and not empties and not others:
            tax["F1 all graphic fields -1"] += 1
            detail["F1"].append((uid, u["name"], u["type"], u["class"]))
        elif empties and not others:
            tax["F6 graphic exists, FileName empty"] += 1
            detail["F6"].append((uid, u["name"], u["type"], u["class"]))
        else:
            tax["F7 mixed -1/empty"] += 1
            detail["F7"].append((uid, u["name"], u["type"], u["class"], negs, empties, others))
        continue
    # does ANY resolve?
    mapped = False
    for f, nm in files:
        n = nm.lower()
        s = n
        if s.endswith("_x1") or s.endswith("_x2"):
            s = s[:-3]
        if n in disk or s in disk or any(("%s_%s" % (s, a)) in disk
                                        for a in ["idlea", "walka", "attacka", "deatha", "decaya"]):
            mapped = True
            break
    if mapped:
        continue
    # classify the non-resolving files
    kinds = set()
    for f, nm in files:
        n = nm.lower()
        if n == "none":
            kinds.add("F2")
        elif len(n) <= 3 and "_" not in n:
            kinds.add("F3")
        elif DE.match(n):
            kinds.add("F5")
        elif re.match(r"^[A-Z0-9_]+$", nm):
            kinds.add("F4")
        else:
            kinds.add("F7")
    if kinds == {"F2"}:
        tax["F2 FileName == 'None'"] += 1
        detail["F2"].append((uid, u["name"], u["type"], u["class"], [x[1] for x in files]))
    elif kinds <= {"F2", "F3"}:
        tax["F3 short non-de-style token"] += 1
        detail["F3"].append((uid, u["name"], u["type"], u["class"], [x[1] for x in files]))
    elif "F5" in kinds:
        tax["F5 DE-style but stem missing on disk"] += 1
        detail["F5"].append((uid, u["name"], u["type"], u["class"], [x[1] for x in files]))
    elif kinds == {"F4"}:
        tax["F4 legacy debug token"] += 1
        detail["F4"].append((uid, u["name"], u["type"], u["class"], [x[1] for x in files]))
    else:
        tax["F7 other: %s" % ",".join(sorted(kinds))] += 1
        detail["F7"].append((uid, u["name"], u["type"], u["class"], [x[1] for x in files]))

print("=== FAILURE TAXONOMY over 2693 unit ids ===")
tot = 0
for k, v in tax.most_common():
    print("   %-40s %5d" % (k, v))
    tot += v
print("   %-40s %5d" % ("TOTAL unmapped", tot))

for k in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]:
    if k in detail:
        print("\n--- %s  (%d) first 12 ---" % (k, len(detail[k])))
        for d in detail[k][:12]:
            en = SEM.get(str(d[0]), {}).get("en")
            print("   id %-5d %-18s type=%-4s class=%-4s %s"
                  % (d[0], str(d[1])[:18], d[2], d[3], (d[4] if len(d) > 4 else "")))
            if en:
                print("          en=%s" % en)

json.dump({k: [list(x) for x in v] for k, v in detail.items()},
          open(os.path.join(HERE, "failtax_detail.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote failtax_detail.json")
