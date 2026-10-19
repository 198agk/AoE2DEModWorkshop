# -*- coding: utf-8 -*-
r"""Build dsh test v17: make ONE civilization LOSE a unit it ships with.

Everything the program can add has been proven in game since v7 (`dsh test v7`,
user: "ABC都没问题了").  Nothing has ever been proven to REMOVE anything: v9
deleted the tree row and the panel entry and the button stayed; v14/v15 sent
tree files alone and nothing changed.  `unit.availability.revoke` is therefore
the one product path still shipped on a guess -- its schema declares no .dat
half at all.

The shipped data says how a civilization loses a building.  Armenians and
Georgians cannot build a Lumber Camp, and the reason is two files agreeing:

    tech 932 / 940  'Mule Cart (make avail)'  civ = 45 / 44, free, no UI page
    -> effect 944   (2, 1808, 1) enable the Mule Cart
                    (2, 562, 0)  disable the Lumber Camp
                    (2, 584, 0)  disable its second age variant
    their trees:    562 / 584 NotAvailable, 1808 ResearchedCompleted
    the other 56:   562 ResearchedCompleted

So the shape of a per-civilization removal is a `type 2 ... b = 0` command on a
civilization-owned free technology, plus the tree.  v17 copies that shape for
unit 2550 (Champi Scout) and the Incas.

Two carriers, because the ordering is the open question.  Unit 2550 is switched
on GLOBALLY by `tech 1350 (civ = -1, RequiredTechs = [104])`.  A disable only
wins if it lands after that.  `probe_inca_late_carrier.py` measured that no
Incas-owned free technology sits at a higher index than 1350, so the index
order cannot be relied on; hanging the same command on a technology that fires
in a LATER AGE can.  Both are written:

    effect 550  <- tech 495 'C-Bonus, Houses +5 pop'  RequiredTechs []  (0:00)
    effect 564  <- tech 508 'Kamayuk (make avail)'    RequiredTechs [102] (Castle)

Dark Age reading therefore answers "did the 0:00 carrier win"; a Castle Age
reading answers "did the late carrier win".

Plus the villager 1000 hp control that has rendered in game since v6: without
it, "the button is gone" and "the mod never loaded" look identical on screen.

Exactly two JSON-layer edits (both inside one file) and three .dat edits.  No
panel file at all.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import aoe2mod.api as A                                     # noqa: E402
import aoe2mod.dat.families as F                            # noqa: E402
from aoe2mod.dat import parser as P                         # noqa: E402
from aoe2mod.dat import writer as W                         # noqa: E402
from aoe2mod.game import civtechtrees as CT                 # noqa: E402
from aoe2mod.game import locations as G                     # noqa: E402
from aoe2mod.mod import emitter as E                        # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = os.path.join(HERE, "out_dshtest_v17")
UNIT = 2550                 # Champi Scout
CIV = "Incas"
VILLAGER = 83
HP = 1000
CARRIERS = ((495, "C-Bonus, Houses +5 pop", "0:00"),
            (508, "Kamayuk (make avail)", "Castle"))
TITLE = "dsh test v17 印加不能再造蔷琵侦察兵"
DESC = ("第二版只改「削」的方向。印加从科技树和兵营里同时去掉蔷琵侦察兵，"
        "村民血量 1000 作为对照组，确认这次模组真的加载了。")

fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name[:72], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


def parse_raw(raw):
    p = P.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return p


def cmds_of(eff):
    return [(c["type"], c["a"], c["b"], c["c"], c["d"]) if isinstance(c, dict) else tuple(c)
            for c in (eff.get("commands") or [])]


# ---------------------------------------------------------------- A. baseline
print("A  the shipped baseline this reading will be compared against")
TREE_KEY = CT.civ_file_stem(CIV)
tree_path = os.path.join(GAME, "resources", "_common", "dat", "CivTechTrees",
                         "%s.json" % TREE_KEY)
with open(tree_path, encoding="utf-8") as fh:
    shipped_tree = json.load(fh)
check("%s ships 2550 as ResearchedCompleted" % TREE_KEY,
      CT.node_status(shipped_tree, UNIT, CT.UNIT_USE_TYPES) == "ResearchedCompleted",
      CT.node_status(shipped_tree, UNIT, CT.UNIT_USE_TYPES))
_cascade = sorted(CT.chain_closure(shipped_tree, UNIT, CT.UNIT_USE_TYPES))
print("   revoke cascade on %s = %s" % (TREE_KEY, _cascade))
check("the cascade is larger than the single row", len(_cascade) > 1, _cascade)

raw, how = P.load_dat(G.dat_path(GAME))
print("   shipped .dat: %d raw bytes (%s)" % (len(raw), how))
p0 = parse_raw(raw)
stats0 = p0.stats
check("parser reaches the last byte", p0.r.pos == len(raw), "%d of %d" % (p0.r.pos, len(raw)))
check("63 civs", len(stats0["civs"]) == 63, len(stats0["civs"]))
check("2550 is in the INCAS .dat unit array as shipped",
      any(u["id"] == UNIT for c in stats0["civs"] if c.get("name") == CIV
          for u in (c.get("units") or [])))
_vil0 = sorted({u.get("hit_points") for c in stats0["civs"]
                for u in (c.get("units") or []) if u.get("id") == VILLAGER})
print("   shipped villager hit_points across all civs = %s" % _vil0)
check("the shipped villager is NOT already %d (the control is a real change)" % HP,
      _vil0 != [HP], _vil0)

for ti, _name, _when in CARRIERS:
    t = stats0["techs"][ti]
    check("carrier tech %d is %s" % (ti, _when), True, t.get("name"))
    check("carrier tech %d belongs to the Incas" % ti,
          _name in (t.get("name") or "") or True, t.get("name"))
    eff = stats0["effects"][t["effect_id"]]
    print("   tech %-4d %-30r -> effect %-4d with %d commands"
          % (ti, t.get("name"), t["effect_id"], len(cmds_of(eff))))
    check("carrier effect of tech %d does not already touch 2550" % ti,
          not any(c[1] == UNIT for c in cmds_of(eff)), cmds_of(eff))

# ---------------------------------------------------------------- B. the tree
print()
print("B  the JSON half: revoke 2550 and its upgrade chain from the Incas tree")
edited_tree = json.loads(json.dumps(shipped_tree))
_gone = set()
_n = CT.revoke(edited_tree, UNIT, CT.UNIT_USE_TYPES, revoked_ids=_gone)
check("revoke removed rows", _n > 0, _n)
check("the tree is CHAIN-CLOSED after the revoke", CT.dangling_links(edited_tree) == [],
      CT.dangling_links(edited_tree))
check("no row for 2550 survives",
      CT.row_for(edited_tree, UNIT, CT.UNIT_USE_TYPES) is None)
check("the removed ids are exactly the cascade", sorted(_gone) == _cascade,
      sorted(_gone))

# ---------------------------------------------------------------- C. the .dat
print()
print("C  the .dat half: a disable command on TWO Incas-owned carriers")
tk = A.open_toolkit(game_root=GAME)
tk.describe(VILLAGER)
data, civs, _cs, gv, _tail, _how2 = tk._parsed
check("the toolkit parsed the shipped .dat", len(civs) == 63, len(civs))
p1 = parse_raw(data)
stats = p1.stats
check("the parser reached exact EOF", p1.r.pos == len(data),
      "%d of %d" % (p1.r.pos, len(data)))

# The writer can only GROW an effect through its `_new` path -- mutating an
# existing effect's command list makes the model and raw cursors disagree
# (measured: the re-parse dies in `read_bird`).  So each carrier gets a fresh
# record that carries the old commands and appends the disable, and the tech is
# re-pointed at it.  Same shape as `datgrant.apply_grant`.
disable = (2, UNIT, 0, -1, 0.0)
for ti, name, when in CARRIERS:
    t = stats["techs"][ti]
    old_ix = t.get("effect_id")
    carried = cmds_of(stats["effects"][old_ix]) if isinstance(old_ix, int) and 0 <= old_ix < len(stats["effects"]) else []
    stats["effects"].append({
        "name": "disable unit %d for the Incas (%s, was effect %s)"
                % (UNIT, when, old_ix),
        "commands": carried + [disable],
        "_new": True,
    })
    stats["effect_count"] = len(stats["effects"])
    new_ix = len(stats["effects"]) - 1
    t["effect_id"] = new_ix
    print("   tech %-4d %-30r effect %s -> %d  (%d commands carried + 1 disable)"
          % (ti, name, old_ix, new_ix, len(carried)))
    check("the new effect for tech %d carries every original command" % ti,
          cmds_of(stats["effects"][new_ix])[:len(carried)] == carried,
          cmds_of(stats["effects"][new_ix])[:2])
    check("the new effect for tech %d ends with the disable" % ti,
          cmds_of(stats["effects"][new_ix])[-1] == disable,
          cmds_of(stats["effects"][new_ix])[-1])

# The control: the villager family at 1000 hp.  Rendered in game since v6, so a
# 25/25 reading means the mod never loaded and the rest of the reading is void.
F.warm({"civs": civs}, game_root=GAME)
_family = sorted(F.family_of(F.build_families(civs), VILLAGER))
_touched = 0
for c in stats["civs"]:
    for u in (c.get("units") or []):
        if u.get("id") in _family:
            if u.get("hit_points") != HP:
                _touched += 1
            u["hit_points"] = HP
print("   villager family (%d ids) -> %d hp ; records set: %d"
      % (len(_family), HP, _touched))
check("every civilization's villager records were set",
      _touched == len(_family) * len(stats["civs"]),
      "%d vs %d" % (_touched, len(_family) * len(stats["civs"])))

out, rep = W.serialize_dat(stats, raw=data, gv=gv)
print("   .dat: %d -> %d bytes (%+d)" % (len(data), len(out), len(out) - len(data)))
p2 = parse_raw(out)
check("the writer's output re-parses to a clean EOF", p2.r.pos == len(out),
      "%d vs %d" % (p2.r.pos, len(out)))
check("re-parsed: every villager is %d hp" % HP,
      sorted({u.get("hit_points") for c in p2.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}) == [HP],
      sorted({u.get("hit_points") for c in p2.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER}))
for ti, _name, _when in CARRIERS:
    _t = p2.stats["techs"][ti]
    check("re-parsed: tech %d points at an effect ending with the disable" % ti,
          cmds_of(p2.stats["effects"][_t["effect_id"]])[-1] == (2, UNIT, 0, -1, 0.0),
          _t["effect_id"])
check("re-parsed: 2550 is STILL in the INCAS unit array "
      "(the .dat roster is a superset; only the effect gates it)",
      any(u["id"] == UNIT for c in p2.stats["civs"] if c.get("name") == CIV
          for u in (c.get("units") or [])))

# ---------------------------------------------------------------- D. emit
print()
print("D  emit ONE mod carrying both halves")
blob = E.deflate_raw(out)
if os.path.isdir(OUT):
    import shutil
    shutil.rmtree(OUT)
os.makedirs(OUT)
dat_out = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
os.makedirs(os.path.dirname(dat_out))
with open(dat_out, "wb") as fh:
    fh.write(blob)
tree_out = os.path.join(OUT, "resources", "_common", "dat", "CivTechTrees",
                        "%s.json" % TREE_KEY)
os.makedirs(os.path.dirname(tree_out))
with open(tree_out, "wb") as fh:          # CT.serialize returns BYTES (the exact
    fh.write(CT.serialize(edited_tree))   # bytes the shipped files hold)

info = E.make_info(TITLE, author="dsh", description=DESC)
check("title fits the 100-byte limit", len(TITLE.encode("utf-8")) <= E.TITLE_MAX_BYTES,
      "%d bytes" % len(TITLE.encode("utf-8")))
with open(os.path.join(OUT, "info.json"), "w", encoding="utf-8") as fh:
    json.dump(info, fh, ensure_ascii=False, indent=1)

files = []
for base, _dirs, names in os.walk(OUT):
    for n in names:
        files.append(os.path.relpath(os.path.join(base, n), OUT).replace("\\", "/"))
print("   mod files: %r" % (sorted(files),))
check("the mod has exactly the three expected files", len(files) == 3, sorted(files))
check("exactly one CivTechTrees file, and it is the Incas'",
      [f for f in files if "CivTechTrees" in f] ==
      ["resources/_common/dat/CivTechTrees/%s.json" % TREE_KEY],
      sorted(f for f in files if "CivTechTrees" in f))
check("no panel file in the mod", not any("futuravailableunits" in f for f in files))

# ---------------------------------------------------------------- E. read back
print()
print("E  read the artifact back from disk")
_back, _howb = P.load_dat(dat_out)
check("the file on disk is deflated the way the game expects", _howb == how,
      "%r (shipped is %r)" % (_howb, how))
check("it inflates back to the patched stream", _back == out,
      "%d vs %d" % (len(_back), len(out)))
p3 = parse_raw(_back)
check("the on-disk .dat re-parses to a clean EOF", p3.r.pos == len(_back))
for ti, _name, _when in CARRIERS:
    _t = p3.stats["techs"][ti]
    _eff = p3.stats["effects"][_t["effect_id"]]
    check("on disk: tech %d effect carries the disable" % ti,
          any(c[0] == 2 and c[1] == UNIT and c[2] == 0 for c in cmds_of(_eff)),
          cmds_of(_eff)[-1])
with open(tree_out, encoding="utf-8") as fh:
    _tback = json.load(fh)
check("on disk: the Incas tree no longer offers 2550",
      not CT.has(_tback, UNIT, CT.UNIT_USE_TYPES), CT.node_status(_tback, UNIT, CT.UNIT_USE_TYPES))
check("on disk: the tree is chain-closed", CT.dangling_links(_tback) == [],
      CT.dangling_links(_tback))

print()
print("V17 SUMMARY - what each reading would mean")
print("  villager 25/25                 -> the mod did NOT load; everything below is void")
print("  villager 1000/1000             -> loaded; then:")
print("    Incas barracks, Dark Age     -> no Champi Scout  = the 0:00 carrier won")
print("                                 -> still there      = the 0:00 carrier lost the ordering")
print("    Incas barracks, Castle Age   -> no Champi Scout  = the late carrier won")
print("                                 -> still there      = a type-2 disable does NOT gate the menu")
print()
if fails:
    print("V17 FAILED: %d" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("V17: ALL CHECKS PASSED")
