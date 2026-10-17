# -*- coding: utf-8 -*-
"""Why are there two panel files?  Test the `era` selector hypothesis.

The panel layer is a PAIR:
  futuravailableunits.json          58 civs (56 main-only + 2 shared)
  paphosfutureavailableunits.json   12 civs (10 paphos-only + 2 shared)
and the paphos file supplies exactly the six Chronicles civs the main file
lacks.  For the engine to pick between them per civilization it must hold a
mapping, and the obvious carrier is `civilizations.json`, which ships an `era`
field per civ (Britons era='base').

If every main-panel key belongs to a civ whose era is NOT the paphos era, and
every paphos-only key belongs to one whose era IS, then:
  * the panel pair is selected by a field the engine reads, so the panel layer
    is engine input (not a build-time log);
  * and the mapping is derivable, which means a mod that adds a civ or moves one
    between eras has a KNOWN second file to update.

If the hypothesis fails, the panel choice comes from somewhere else and the
pairing is a packaging convention -- which is also worth knowing, because then
adding a panel entry for a Chronicles civ means editing the paphos file by
hand with nothing in the data to derive it from.
"""
import json
import os
import sys

sys.path.insert(0, r"D:\Software\DeepSeek Harness\工作区2")

import aoe2mod.api as A                        # noqa: E402
from aoe2mod.game import buildpanel as BP      # noqa: E402
from aoe2mod.game import civtechtrees as CT    # noqa: E402

tk = A.open_toolkit()
GAME = tk.game_root
tk._ensure()

main_p, paphos_p = BP.panel_paths(GAME)


def civ_keys(path):
    _t, obj = BP.load_panel(path)
    return set(k for k, v in obj.items()
               if isinstance(v, dict) and BP.BUILDINGS_KEY in v)


km, kp = civ_keys(main_p), civ_keys(paphos_p)

civ_json = os.path.join(GAME, "resources", "_common", "dat", "civilizations.json")
with open(civ_json, "r", encoding="utf-8") as fh:
    entries = json.load(fh)["civilization_list"]

data, civs, civs_start, gv, tail, how = tk._parsed
dat_names = [c.get("name") for c in civs]
print("dat civs %d   civilizations.json entries %d" % (len(dat_names), len(entries)))

# position-wise join (the only join that works -- names disagree by design)
print()
print("--- era values, and which panel file carries that civ --------------")
by_era = {}
rows = []
for i, (nm, e) in enumerate(zip(dat_names, entries)):
    stem = CT.civ_file_stem(nm)
    era = e.get("era")
    panel = ("main" if nm in km or stem in km or stem.title() in km or
             nm.title() in km else
             ("paphos" if nm in kp or stem in kp or stem.title() in kp or
              nm.title() in kp else "NONE"))
    by_era.setdefault(era, {}).setdefault(panel, 0)
    by_era[era][panel] += 1
    rows.append((i, nm, era, panel, e.get("data_name")))

for era in sorted(by_era, key=lambda x: (x is None, x)):
    print("    era=%-12s %s" % (era, dict(sorted(by_era[era].items()))))

print()
print("--- the paphos-only panel keys, and their era ----------------------")
paphos_only = sorted(kp - km)
found = 0
for key in paphos_only:
    hit = None
    for i, nm, era, panel, dn in rows:
        stem = CT.civ_file_stem(nm)
        if key in (nm, stem, stem.title(), nm.title(), stem.capitalize()):
            hit = (nm, era, dn)
            break
    if hit:
        found += 1
    print("    %-16s -> %s" % (key, hit))
print("    resolved %d of %d" % (found, len(paphos_only)))

print()
print("--- main-panel keys whose civ has the paphos era (would break it) ---")
bad = []
for i, nm, era, panel, dn in rows:
    stem = CT.civ_file_stem(nm)
    in_main = nm in km or stem in km or stem.title() in km or nm.title() in km
    if in_main and era and era != "base":
        bad.append((nm, era))
print("    %s" % (bad or "none"))

eras = sorted({r[2] for r in rows if r[2]})
print()
print("distinct era values across the 63 .dat civs: %s" % eras)

print()
print("=" * 78)
# Only 2 era values exist.  The paphos-only keys split into real civilizations
# (all era=antiquity) and four placeholder keys (Paphos6..9) that are not
# civilizations at all -- they never appear in the 63-civ list.  So the honest
# test is over the keys that name a real civ.
real_paphos_only = [k for k in paphos_only
                    if any(k in (nm, CT.civ_file_stem(nm),
                                 CT.civ_file_stem(nm).title(), nm.title(),
                                 CT.civ_file_stem(nm).capitalize())
                           for nm in dat_names)]
print("paphos-only keys naming a real civ : %d  %s"
      % (len(real_paphos_only), sorted(real_paphos_only)))
print("paphos-only keys that are placeholders: %s"
      % sorted(set(paphos_only) - set(real_paphos_only)))
antiquity_civs = [r[1] for r in rows if r[2] == "antiquity"]
print("civs whose era is 'antiquity'        : %d  %s"
      % (len(antiquity_civs), antiquity_civs))
if (len(real_paphos_only) == len(antiquity_civs) == 6 and not bad):
    print()
    print("ERA HYPOTHESIS: HOLDS.  The two panel files partition the 63 civs by")
    print("the `era` field in civilizations.json -- 57 base civs in the main")
    print("file, 6 antiquity civs in the paphos file, and no overlap in the")
    print("wrong direction.  So the file to edit is DERIVABLE, and the engine")
    print("holds a per-civ selector it must read from civilizations.json.")
else:
    print()
    print("ERA HYPOTHESIS: NOT ESTABLISHED in the strict form.")
    print("real paphos-only %d vs antiquity civs %d, non-base main keys %d"
          % (len(real_paphos_only), len(antiquity_civs), len(bad)))
    print("So the pairing would be at most a packaging convention; do not")
    print("claim the engine derives it from `era`.")
print("=" * 78)
print("NOT PROVEN: that the engine consults these files at all.  A derivable")
print("selector is a necessary condition for that, not sufficient.")

assert len(rows) == len(entries), "position join must cover every civ"
assert paphos_only, "the paphos file must contribute keys the main one lacks"
assert len(real_paphos_only) == len(antiquity_civs) == 6, (
    "every antiquity civ must be carried by the paphos panel and no other")
assert not bad, "no base-era civ may sit in the paphos file's set"
print()
print("PANEL ERA PIN: PASSED")
