# -*- coding: utf-8 -*-
"""Who covers the civilizations the main panel file does not?

Why this can decide something
-----------------------------
`futuravailableunits.json` covers 58 civs; the tree covers 62 (every playable
civ except Gaia).  If a civilization had NO panel entry and the menu were fed by
the panel file, that civilization would have no build menu at all -- which is
observably false for a released DLC.  So either

  (a) the second panel file (`paphosfutureavailableunits.json`) covers the gap,
      in which case the "panel layer" is a PAIR, scoped per expansion, and the
      earlier finding that the main file is a shipped artifact applies to the
      pair; or
  (b) some playable civilization is in NO panel file, in which case the menu
      cannot come solely from panel files and must consult the tree --
      a decisive structural argument that needs no game run.

Both outcomes are useful, so measure rather than guess.  The earlier rounds
treated `futuravailableunits.json` as "the panel"; that was never checked.

Also cross-checks the two panel files against each other where both cover a civ.
"""
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
print("game root     : %s" % GAME)
print("main panel    : %s" % (os.path.basename(main_p) if main_p else None))
print("paphos panel  : %s" % (os.path.basename(paphos_p) if paphos_p else None))


def civ_keys(path):
    if not path:
        return set()
    _text, obj = BP.load_panel(path)
    # the file is {civ_display_name: {"Buildings": [...]}, ...}
    return set(k for k, v in obj.items()
               if isinstance(v, dict) and BP.BUILDINGS_KEY in v)


km = civ_keys(main_p)
kp = civ_keys(paphos_p)
print()
print("main civs     : %d" % len(km))
print("paphos civs   : %d" % len(kp))
print("both          : %d" % len(km & kp))
print("paphos only   : %d  %s" % (len(kp - km), sorted(kp - km)))
print("main only     : %d  %s" % (len(km - kp), sorted(km - kp)))
print("union         : %d" % len(km | kp))

# ---- the tree side ---------------------------------------------------------
trees = tk._trees()
tree_stems = set(trees)
print()
print("tree stems    : %d" % len(tree_stems))

# map stems back to the .dat civ names so the comparison is in one namespace
data, civs, civs_start, gv, tail, how = tk._parsed
dat_names = [c.get("name") for c in civs]
stem_to_dat = {CT.civ_file_stem(n): n for n in dat_names if n}

print()
print("--- every .dat civilization, and where it can be described ---------")
uncov = []
for n in dat_names:
    stem = CT.civ_file_stem(n)
    in_tree = stem in trees
    # the panel keys use display names; the bridge is the file stem for trees,
    # so go through the stem->name map and try a few spellings
    cands = {n, stem, stem.capitalize(), stem.title()}
    in_main = bool(cands & km)
    in_pap = bool(cands & kp)
    where = "main" if in_main else ("paphos" if in_pap else "NONE")
    if in_tree and where == "NONE":
        uncov.append(n)
    print("    %-14s stem=%-14s tree=%-5s panel=%-7s"
          % (n, stem, in_tree, where))

print()
print("civs with a tree but NO panel coverage: %d  %s" % (len(uncov), uncov))

# ---- do the two panel files agree where both cover? -----------------------
print()
print("--- where both panel files cover a civ, do they agree? -------------")
shared = sorted(km & kp)
_text_a, obj_a = BP.load_panel(main_p)
_text_p, obj_p = BP.load_panel(paphos_p)


def pairs(obj, key):
    out = set()
    for b in (obj.get(key) or {}).get(BP.BUILDINGS_KEY, []):
        for u in (b.get("Units") or []):
            out.add((b.get("ID"), u.get("ID")))
    return out


agree = differ = 0
examples = []
for k in shared:
    a, p = pairs(obj_a, k), pairs(obj_p, k)
    if a == p:
        agree += 1
    else:
        differ += 1
        if len(examples) < 6:
            examples.append((k, len(a - p), len(p - a), sorted(a - p)[:3],
                             sorted(p - a)[:3]))
print("    shared civs %d -> identical %d / different %d"
      % (len(shared), agree, differ))
for k, only_a, only_p, ea, ep in examples:
    print("        %-12s only-main %-4d only-paphos %-4d  e.g. main-only %s"
          % (k, only_a, only_p, ea))

print()
print("=" * 78)
if uncov:
    print("DECISIVE: %d playable civilization(s) have a tree and NO panel"
          % len(uncov))
    print("coverage at all (%s).  The build panel cannot be fed solely by" % uncov)
    print("panel files -- for those civs the menu must consult the tree.")
else:
    print("The panel files together cover every civilization that has a tree.")
    print("So the panel layer is COMPLETE, and 'the menu might read the other")
    print("file' remains live for every civ -- no structural argument against")
    print("it.  What this does establish: the panel is a PAIR scoped per")
    print("expansion, so any experiment must edit BOTH names, and the earlier")
    print("mtime result applies to the pair.")
print("=" * 78)
print("NOT PROVEN: which file the running game consults.  Coverage bounds")
print("what COULD be consulted; it does not show what IS.")

if differ:
    print()
    print("NOTE: the two panel files disagree on %d civs they share, so they"
          % differ)
    print("are not interchangeable copies of one dataset.")

# ---- assertions -------------------------------------------------------------
assert main_p and paphos_p, "both panel files must exist"
assert len(km) > 50, "the main panel must cover most civs"
assert kp - km, ("the paphos panel must contribute civs the main file lacks; "
                 "if it did not there would be no reason for two files")
assert not uncov, ("every civ with a tree must be covered by SOME panel file; "
                   "otherwise the menu provably cannot come from panels alone")
print()
print("PANEL COVERAGE PIN: PASSED")
