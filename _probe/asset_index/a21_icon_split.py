#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""a21_icon_split.py -- two-sided atlas discrimination + the 794/447 disk puzzle.

Fixes from the first run:
  * tokenizer did not split letter->digit boundaries, so 'Barracks1' != 'Barracks'
    and the plausibility score was undercounted.  Now splits [a-z]<->[0-9].
  * the disk comparison was case-sensitive on extension: the directory holds
    447 '.dds' + 347 '.DDS'.  Now compare case-insensitively.

Q1  Is the icon atlas chosen by unit Type (80 -> ingamebuildings, else ingameunits)?
Q1b Which buildings still fail name-plausibility, and why?
Q2  ingameunits claims 794 '<NNN>_50730.dds' but only 447 appeared to exist.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WID = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
J = json.load(open(os.path.join(WID, "materials.json"), encoding="utf-8"))
atl = {e.get("AtlasDef", e)["Name"]: e.get("AtlasDef", e) for e in J["AtlasTextures"]}
C = json.load(open(os.path.join(HERE, "units_raw.json"), encoding="utf-8"))
SEM = json.load(open(_HERE_PATH("_probe", "semantic", "unit_names.json"),
                     encoding="utf-8"))

def emb(a):
    out = {}
    for t in atl[a]["Textures"]:
        stem = t["FileName"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        h = stem.split("_")[0]
        if h.isdigit():
            out[int(h)] = t
    return out

U, T, B = emb("ingameunits"), emb("ingametechs"), emb("ingamebuildings")
STOP = {"age", "the", "and", "icon", "sld", "x1", "x2"}

def toks(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or "")          # CamelCase
    s = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s)             # letter->digit
    s = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s)             # digit->letter
    raw = re.split(r"[^A-Za-z0-9]+", s.lower())
    return set(x for x in raw if len(x) > 2 and not x.isdigit() and x not in STOP)

def plaus(entity, ref):
    r = re.sub(r"^(BuildingIcons|UnitIcons|TechIconsT?)", "", ref or "")
    r = re.sub(r"^[0-9]+", "", r)                              # drop leading number
    return len(toks(r) & toks(entity)) > 0

byid = {}
for ci, civ in enumerate(C):
    for u in civ["units"]:
        byid.setdefault(u["id"], {})[ci] = u

print("=== Q1 TWO-SIDED TEST: atlas selected by unit Type ===")
groups = collections.OrderedDict((("building (type 80)", []), ("other (type != 80)", [])))
for uid, per in sorted(byid.items()):
    u = per[sorted(per)[0]]
    if u.get("icon_id", -1) <= 0:
        continue
    en = (SEM.get(str(uid)) or {}).get("en") or u.get("name") or ""
    key = "building (type 80)" if u.get("type") == 80 else "other (type != 80)"
    groups[key].append((uid, en, u["icon_id"]))
for k, rows in groups.items():
    nb = sum(1 for r in rows if r[2] in B)
    nu = sum(1 for r in rows if r[2] in U)
    pb = sum(1 for r in rows if r[2] in B and plaus(r[1], B[r[2]]["RefName"]))
    pu = sum(1 for r in rows if r[2] in U and plaus(r[1], U[r[2]]["RefName"]))
    pt = sum(1 for r in rows if r[2] in T and plaus(r[1], T[r[2]]["RefName"]))
    print("\n %s : %d ids with IconID>0" % (k, len(rows)))
    print("   ingamebuildings: resolves %4d/%d  name-plausible %4d/%d (%.1f%%)"
          % (nb, len(rows), pb, nb, 100.0 * pb / max(1, nb)))
    print("   ingameunits    : resolves %4d/%d  name-plausible %4d/%d (%.1f%%)"
          % (nu, len(rows), pu, nu, 100.0 * pu / max(1, nu)))
    print("   ingametechs    : resolves %4d/%d  name-plausible %4d/%d (%.1f%%)"
          % (pt and sum(1 for r in rows if r[2] in T) or 0, len(rows), pt,
             max(1, sum(1 for r in rows if r[2] in T)),
             100.0 * pt / max(1, sum(1 for r in rows if r[2] in T))))
    if k.startswith("other"):
        print("   sample (en | icon | unit atlas | building atlas | tech atlas):")
        for uid, en, ic in rows[:10]:
            print("      %-5d %-22s %-4d U=%-22s B=%-30s T=%s"
                  % (uid, en[:22], ic,
                     U[ic]["RefName"] if ic in U else "--",
                     B[ic]["RefName"] if ic in B else "--",
                     T[ic]["RefName"] if ic in T else "--"))

print("\n=== Q1b buildings NOT name-plausible in ingamebuildings (after tokenizer fix) ===")
bad = [(uid, en, ic) for uid, en, ic in groups["building (type 80)"]
       if ic in B and not plaus(en, B[ic]["RefName"])]
print("count %d of %d ; first 20:" % (len(bad), len(groups["building (type 80)"])))
for uid, en, ic in bad[:20]:
    print("   id %-5d %-28s icon=%-4d -> %s" % (uid, en[:28], ic, B[ic]["RefName"]))
print("   ... plus ids with NO ingamebuildings entry at all: %s"
      % [uid for uid, en, ic in groups["building (type 80)"] if ic not in B][:20])

print("\n=== Q2: ingameunits .dds on disk vs claimed (CASE-INSENSITIVE) ===")
D = os.path.join(WID, "textures", "ingame", "units")
files = sorted(os.listdir(D))
print("directory holds %d files; extensions %s" % (len(files), collections.Counter(
    os.path.splitext(f)[1] for f in files)))
lo = {f.lower(): f for f in files}
claimed = {t["FileName"].rsplit("/", 1)[-1]: n for n, t in U.items()}
cl = {k.lower(): k for k in claimed}
print("claimed %d distinct names ; on disk %d ; exact case match %d"
      % (len(claimed), len(lo), len(set(claimed) & set(files))))
print("case-insensitive: claimed&disk %d ; claimed-but-missing %d ; disk-but-unclaimed %d"
      % (len(set(cl) & set(lo)), len(set(cl) - set(lo)), len(set(lo) - set(cl))))
print("first 10 claimed-but-missing: %s" % sorted(set(cl) - set(lo))[:10])
print("first 10 disk-but-unclaimed : %s" % sorted(set(lo) - set(cl))[:10])
for k in sorted(set(cl) - set(lo))[:5]:
    print("   claimed %s -> suggested existing: %s"
          % (claimed[cl[k]], [lo[x] for x in sorted(lo) if x.startswith(k[:12])][:4]))

src = {k: atl["ingameunits"].get(k) for k in
       ("SDSource", "HDSource", "UHDSource", "DefaultSource")}
print("\ningameunits atlas source packs: %s" % src)
for p in sorted(set(v for v in src.values() if v)):
    fp = os.path.join(WID, p.replace("/", os.sep))
    print("   %-42s exists=%s  size=%s" % (p, os.path.exists(fp),
                                           os.path.getsize(fp) if os.path.exists(fp) else "-"))
