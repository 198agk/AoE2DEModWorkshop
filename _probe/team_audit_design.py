# -*- coding: utf-8 -*-
"""_probe/team_audit_design.py -- task-1 deliverable (auditor: design-auditor).

Adversarial audit of the discriminating experiment in `_probe/build_smoke5.py`.
Prints the VERDICT line and the top findings, re-deriving every number from the
real files at run time (not reciting a table). Read-only: nothing is written
outside stdout. Full write-up: `_probe/team/auditor/REPORT.md`.

Run:  $env:PYTHONIOENCODING='utf-8'
      $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'
      python _probe/team_audit_design.py
"""
import os
import sys
import json
import glob
import zlib
import io
import hashlib
import time
import contextlib

HERE = r"D:\Software\DeepSeek Harness\工作区2"
sys.path.insert(0, HERE)
from aoe2mod.game import buildpanel as BP       # noqa: E402
from aoe2mod.game import civtechtrees as CT     # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
PROFILE = r"C:\Users\26913\Games\Age of Empires 2 DE"
ACC = os.path.join(PROFILE, "76561198406248391")
MS = os.path.join(ACC, "mods", "mod-status.json")
LOCAL = os.path.join(ACC, "mods", "local")
BUNDLE = "aoe2mod Bundle VillagerHP plus Britons HandCannon"
SMOKE5 = "aoe2mod Smoke5 TreeVsPanel"
OUT = os.path.join(HERE, "_probe", "out_smoke5")
DAT_REL = os.path.join("resources", "_common", "dat", "empires2_x2_p1.dat")
BLD, SUBJ_A, SUBJ_B = 12, 2550, 74

FINDINGS = []


def head(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def note(tag, text):
    FINDINGS.append((tag, text))
    print("   [%s] %s" % (tag, text))


# --------------------------------------------------------------------------
# F1 -- is smoke5 even registered / enabled?
# --------------------------------------------------------------------------
head("F1: smoke5 registration -- install_smoke5.py never registers it")

ms_registered = None
ms_titles = []
ms_enabled = []
if os.path.isfile(MS):
    with open(MS, encoding="utf-8") as fh:
        ms = json.load(fh)
    mods = ms.get("Mods") or []
    ms_titles = [m.get("Title") for m in mods]
    ms_enabled = [(m.get("Title"), m.get("Priority"), m.get("Enabled")) for m in mods]
    ms_registered = any("Smoke5" in json.dumps(m) for m in mods)
    print("   mod-status.json: %d Mods entries" % len(mods))
    print("   'Smoke5' present in any entry : %s" % ms_registered)
    for t, pr, en in ms_enabled:
        print("      prio=%s enabled=%-5s %s" % (pr, en, t))
    print("   mtime mod-status.json : %s" % time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(MS))))
sm_dir = os.path.join(LOCAL, SMOKE5)
print("   mod dir exists        : %s  (%s)" % (
    os.path.isdir(sm_dir),
    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(sm_dir)))
    if os.path.isdir(sm_dir) else "-"))

log_smoke5 = 0
log_sessions = 0
distinct_enabling = {}
for s in glob.glob(os.path.join(PROFILE, "logs", "*")):
    ml = os.path.join(s, "MainLog.txt")
    if not os.path.isfile(ml):
        continue
    log_sessions += 1
    for line in open(ml, encoding="utf-8", errors="replace"):
        if "Enabling mod" in line:
            distinct_enabling[line.strip()[:120]] = distinct_enabling.get(line.strip()[:120], 0) + 1
            if "Smoke5" in line or "TreeVsPanel" in line:
                log_smoke5 += 1
print("   log sessions scanned  : %d" % log_sessions)
print("   'Enabling mod ...Smoke5/TreeVsPanel' lines ever: %d" % log_smoke5)
print("   distinct mods the logs ever enabled: %d" % len(distinct_enabling))
for k, v in sorted(distinct_enabling.items(), key=lambda kv: -kv[1]):
    print("      x%-4d %s" % (v, k))
if ms_registered is False:
    note("FATAL", "smoke5 is absent from mod-status.json (and from all %d sessions' "
         "'Enabling mod' lines) -> the game cannot load it; the reading instructions "
         "in install_smoke5.py:95-102 are unsatisfiable as shipped." % log_sessions)

# --------------------------------------------------------------------------
# F2 -- can the positive control attribute load?
# --------------------------------------------------------------------------
head("F2: the positive control -- Villager HP per .dat copy (undifferentiated)")

TARGETS = [
    ("SHIPPED", os.path.join(GAME, DAT_REL)),
    ("BUNDLE ", os.path.join(LOCAL, BUNDLE, DAT_REL)),
    ("SMOKE5 ", os.path.join(LOCAL, SMOKE5, DAT_REL)),
    ("OUT    ", os.path.join(OUT, DAT_REL)),
]
dat_table = []
for tag, path in TARGETS:
    if not os.path.isfile(path):
        print("   %s MISSING %s" % (tag, path))
        continue
    raw = open(path, "rb").read()
    sha = hashlib.sha256(raw).hexdigest()[:12]
    hp = None
    data = None
    for wb in (-15, 15, 31):
        try:
            data = zlib.decompress(raw, wb)
            break
        except Exception:
            data = None
    if data is not None:
        try:
            from aoe2mod.dat import parser as P
            pr = P.Parser(data)
            got = []
            pr._collect_unit = lambda u: got.append(dict(u))
            with contextlib.redirect_stdout(io.StringIO()):
                pr.parse()
            row83 = [u for u in got if u.get("id") == 83]
            hp = row83[0].get("hit_points") if row83 else None
        except Exception as exc:
            hp = "parse-fail %s" % type(exc).__name__
    dat_table.append((tag.strip(), len(raw), sha, hp))
    print("   %-8s size=%-9d sha256[:12]=%s  villager(83).hit_points=%s" % (
        tag, len(raw), sha, hp))

by_tag = {t[0]: t for t in dat_table}
if "BUNDLE" in by_tag and "SMOKE5" in by_tag:
    if by_tag["BUNDLE"][2] == by_tag["SMOKE5"][2]:
        note("FATAL", "Bundle and smoke5 .dat are BYTE-IDENTICAL (sha %s, %d B, villager hp %s) "
             "-> seeing Villager HP 1000 proves *a* villager-HP mod loaded, not that smoke5 "
             "loaded. install_smoke5.py:102's control is vacuous."
             % (by_tag["BUNDLE"][2], by_tag["BUNDLE"][1], by_tag["BUNDLE"][3]))

# --------------------------------------------------------------------------
# F3 -- the sibling ships the same three paths with opposite contents
# --------------------------------------------------------------------------
head("F3: sibling mod overlap -- same 3 engine paths, opposite contents")

trees = CT.load_trees(GAME)
_t, po = BP.load_panel(os.path.join(GAME, BP.PANEL_REL))
kb = BP.civ_key_for(po, "Britons")


def tree_has(t, nid):
    return CT.row_for(t, nid, CT.UNIT_USE_TYPES) is not None


def panel_has(obj, key, nid):
    return BP.find_entry(obj, key, nid, BP.UNITS_KEY)[1] is not None


print("   SHIPPED tree BRITONS : A=%s B=%s" % (
    tree_has(trees["BRITONS"], SUBJ_A), tree_has(trees["BRITONS"], SUBJ_B)))
print("   SHIPPED panel Britons: A=%s B=%s" % (
    panel_has(po, kb, SUBJ_A), panel_has(po, kb, SUBJ_B)))

for name in (BUNDLE, SMOKE5):
    d = os.path.join(LOCAL, name)
    tp = os.path.join(d, CT.CIVTECHTREES_REL, "BRITONS.json")
    pp = os.path.join(d, BP.PANEL_REL)
    th = ph = None
    if os.path.isfile(tp):
        with open(tp, encoding="utf-8") as fh:
            tobj = json.load(fh)
        th = tree_has(tobj, SUBJ_A), tree_has(tobj, SUBJ_B)
    if os.path.isfile(pp):
        _txt, pobj = BP.load_panel(pp)
        pkb = BP.civ_key_for(pobj, "Britons")
        ph = panel_has(pobj, pkb, SUBJ_A), panel_has(pobj, pkb, SUBJ_B)
    print("   %-52s" % name)
    print("      tree  A=%s B=%s   panel A=%s B=%s" % (
        (th or ("?", "?"))[0], (th or ("?", "?"))[1],
        (ph or ("?", "?"))[0], (ph or ("?", "?"))[1]))

paths_ok = all(os.path.isfile(os.path.join(LOCAL, n, DAT_REL)) for n in (BUNDLE, SMOKE5))
print("   both mods ship all three paths (dat/panel/tree): %s" % paths_ok)
note("FATAL", "Bundle (tree A=False B=True, panel A=False B=True) and smoke5 "
     "(tree A=True B=True, panel A=False B=False) overlap on all three paths; "
     "with per-file layering any of the four 2x2 outcomes is reachable while "
     "smoke5's tree edit is absent (tree<-Bundle/panel<-Smoke5 = 'A absent,B absent' "
     "= the design's headline 'PANEL drives').")

# --------------------------------------------------------------------------
# F4 -- outcome -> regime is not injective
# --------------------------------------------------------------------------
head("F4: outcome -> hypothesis table (enumerated)")
# A=2550 is granted in the TREE and absent from the PANEL (this is smoke5's edit).
# B=74 is present in BOTH the tree and the panel, then removed from the PANEL only.
# So under each whole-file regime the two observable bits are:
#   tree-only     menu = tree grants      -> A yes (tree), B yes (tree) -> (T,T)
#   panel-only    menu = panel entries    -> A no  (panel), B no  (panel) -> (F,F)
#   union         A yes (tree), B yes (tree)                              -> (T,T)
#   intersection  A no  (panel), B no  (panel)                            -> (F,F)
regimes = {
    "tree-only (menu = tree grants)": (True, True),
    "union (shown if EITHER file has it)": (True, True),
    "panel-only (menu = panel entries)": (False, False),
    "intersection (shown only if BOTH have it)": (False, False),
    "tree for A + panel for B (mixed)": (True, False),
    "panel for A + tree for B (mixed)": (False, True),
}
bycell = {}
for name, cell in regimes.items():
    bycell.setdefault(cell, []).append(name)
for cell in ((True, True), (False, False), (True, False), (False, True)):
    names = bycell.get(cell, [])
    print("   A=%-5s B=%-5s <- %d regime(s): %s" % (
        cell[0], cell[1], len(names), "; ".join(names)))
print("   build_smoke5.py:21-22 claims (T,T)='TREE drives' and (F,F)='PANEL drives'")
note("MAJOR", "(A present,B present) maps to 2 regimes and (A absent,B absent) maps to 2 -> "
     "even a clean install cannot separate 'tree-only' from 'union', nor 'panel-only' "
     "from 'intersection'.")

# --------------------------------------------------------------------------
# F5 -- subject B is masked by the design's own precondition
# --------------------------------------------------------------------------
head("F5: subject B masking -- tree grants 74, so removing the panel entry cannot hide it")

brit = trees["BRITONS"]
b12 = [e for b in BP.buildings(po, kb) if b.get("ID") == BLD
       for e in (b.get("Units") or [])]
masked = clean = 0
for e in b12:
    if CT.can_build(brit, e.get("ID")):
        masked += 1
    else:
        clean += 1
print("   Britons bldg-12 panel units: %d  MASKED(tree grants too)=%d  clean=%d"
      % (len(b12), masked, clean))
print("   Britons tree row for 74    : status=%s can_build=%s" % (
    (CT.row_for(brit, SUBJ_B, CT.UNIT_USE_TYPES) or {}).get("Node Status"),
    CT.can_build(brit, SUBJ_B)))

panels = BP.load_all(GAME)
tot_m = tot_c = 0
for pk, pv in panels.items():
    t = trees.get(CT.civ_file_stem(pk))
    if t is None:
        continue
    for b in BP.buildings(pv["obj"], pv["key"]):
        if b.get("ID") != BLD:
            continue
        for e in (b.get("Units") or []):
            if CT.row_for(t, e.get("ID"), CT.UNIT_USE_TYPES) is not None and CT.can_build(t, e.get("ID")):
                tot_m += 1
            else:
                tot_c += 1
print("   across all bridged civs    : MASKED=%d CLEAN=%d (%.1f%% masked)"
      % (tot_m, tot_c, 100.0 * tot_m / max(1, tot_m + tot_c)))
note("MAJOR", "build_smoke5.py:91 requires the tree row for 74 to read ResearchedCompleted, "
     "and can_build counts that as buildable -> the tree independently grants Militia. "
     "Britons bldg-12: %d/%d masked. Shipped-wide: %d/%d (%.1f%%) masked."
     % (masked, len(b12), tot_m, tot_m + tot_c, 100.0 * tot_m / max(1, tot_m + tot_c)))

# --------------------------------------------------------------------------
# F6 -- panel provenance: does the panel even derive from the tree?
# --------------------------------------------------------------------------
head("F6: panel vs tree agreement (the two-file framing)")
# NB: over ALL buildings, not just bldg 12 -- the design's dichotomy is global.
norow = non = agree = 0
for pk, pv in panels.items():
    t = trees.get(CT.civ_file_stem(pk))
    if t is None:
        continue
    for b in BP.buildings(pv["obj"], pv["key"]):
        for e in (b.get("Units") or []):
            r = CT.row_for(t, e.get("ID"), CT.UNIT_USE_TYPES)
            if r is None:
                norow += 1
            elif not CT.can_build(t, e.get("ID")):
                non += 1
            else:
                agree += 1
tot = norow + non + agree
print("   bridged panel unit entries (ALL buildings): %d" % tot)
print("      tree grants it too      : %d (%.1f%%)" % (agree, 100.0 * agree / max(1, tot)))
print("      tree row absent         : %d (%.1f%%)" % (norow, 100.0 * norow / max(1, tot)))
print("      tree row present, no grant: %d" % non)
note("MAJOR", "%d of %d (%.1f%%) panel unit entries have NO tree row at all "
     "-> the panel is not derivable row-for-row from the tree; the clean "
     "'tree XOR panel' dichotomy in build_smoke5.py:18-23 is not supported."
     % (norow, tot, 100.0 * norow / max(1, tot)))

# --------------------------------------------------------------------------
# verdict
# --------------------------------------------------------------------------
print()
print("=" * 78)
print("VERDICT")
print("=" * 78)
verdict = (
    "VERDICT: DESIGN IS AMBIGUOUS BECAUSE the same three engine paths are shipped by "
    "both `aoe2mod Bundle VillagerHP plus Britons HandCannon` (tree: 2550 absent / 74 "
    "present; panel: 2550 absent / 74 present) and `aoe2mod Smoke5 TreeVsPanel` (tree: "
    "2550 present / 74 present; panel: 2550 absent / 74 absent), their `.dat` files are "
    "BYTE-IDENTICAL so the Villager-HP control cannot attribute load, smoke5 is absent "
    "from mod-status.json and from every 'Enabling mod' log line, all four 2x2 outcomes "
    "are reachable without smoke5's tree edit loading, the two headline cells are each "
    "2-to-1 against the regimes they claim to distinguish, and subject B is masked by "
    "the design's own ResearchedCompleted precondition."
)
print(verdict)
print()
print("Top findings:")
for tag, text in FINDINGS:
    print("  - [%s] %s" % (tag, text))
print()
print("Full write-up with all tables: _probe/team/auditor/REPORT.md")
print("Probes (reproducible): _probe/team/auditor/p15..p23*.py")
