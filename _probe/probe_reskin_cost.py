# -*- coding: utf-8 -*-
"""Before wiring a reskin intent: what does it actually cost, and has anyone
ever shipped a loose file under the SPRITES storage point?"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os
import sys

ROOT = _HERE_PATH()
sys.path.insert(0, ROOT)
import aoe2mod.api as A
from aoe2mod.game import sprites as S
from aoe2mod.mod import emitter as E

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODS = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
REL = "resources/_common/drs/graphics"

print("=" * 72)
print("1  has any installed mod ever written under the SPRITES storage point?")
print("=" * 72)
hits = []
for base in (MODS,):
    for dp, dn, fn in os.walk(base):
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, base).replace(os.sep, "/")
            if "/resources/_common/drs/graphics/" in "/" + rel:
                hits.append((rel, f, os.path.getsize(p)))
print("  files under drs/graphics in installed mods: %d" % len(hits))
for r in sorted(hits)[:20]:
    print("    %s  %d B" % (r[0], r[2]))
byext = {}
for r in hits:
    byext[os.path.splitext(r[0])[1].lower()] = byext.get(
        os.path.splitext(r[0])[1].lower(), 0) + 1
print("  by extension: %s" % byext)

print()
print("=" * 72)
print("2  a whole-unit reskin, per civilization")
print("=" * 72)
tk = A.open_toolkit(game_root=GAME)
tk._ensure()
idx = S.art_index(GAME, tk._stats["graphics"])

def rec(uid, civ_index):
    for u in tk._civs[civ_index]["units"]:
        if u["id"] == uid:
            return u

TARGET, DONOR = 4, 8            # Archer <- Longbowman
total_files, total_bytes = set(), 0
per_civ = []
unmapped_any = {}
for ci, c in enumerate(tk._civs):
    t = rec(TARGET, ci)
    d = rec(DONOR, ci)
    if t is None or d is None:
        continue
    ta, da = idx.art(t), idx.art(d)
    if not ta or not da or ta.get("kind") != "loose" or da.get("kind") != "loose":
        per_civ.append((c["name"], None, None, None))
        continue
    try:
        pairs, unmapped, extra = S.plan_swap(ta, da)
    except S.SpriteError as exc:
        per_civ.append((c["name"], ta.get("stem"), None, str(exc)))
        continue
    per_civ.append((c["name"], ta.get("stem"), da.get("stem"), len(pairs)))
    for tn, dn in pairs:
        for suffix in ("_x1", "_x2"):
            tb = (tn[:-3] + suffix) if tn.endswith("_x1") else tn
            db = (dn[:-3] + suffix) if dn.endswith("_x1") else dn
            total_files.add(tb + ".sld")
            p = os.path.join(S.graphics_dir(GAME), db + ".sld")
            if os.path.exists(p):
                total_bytes += os.path.getsize(p)
    for tk_, tn in unmapped:
        unmapped_any.setdefault(tk_, 0)
        unmapped_any[tk_] += 1

resolved = [r for r in per_civ if r[3] is not None and not isinstance(r[3], str)]
print("  civs resolved          : %d of %d" % (len(resolved), len(tk._civs)))
print("  distinct target stems  : %d" % len({r[1] for r in resolved}))
for r in sorted(resolved)[:8]:
    print("    %-14s %-22s <- %-22s %d pairs" % r)
print("  ...")
print("  files a mod would carry: %d  (%.1f MB)"
      % (len(total_files), total_bytes / 1048576.0))
print("  unmapped animations    : %s" % (unmapped_any or "none"))

print()
print("=" * 72)
print("3  the same for a 1-animation target (a building) and a shared art")
print("=" * 72)
for T, D, note in ((12, 498, "Barracks: Dark <- Feudal (age variant)"),
                   (83, 4, "Villager <- Archer"),
                   (66, 102, "Gold Mine <- Stone Mine (SAME art)")):
    t = rec(T, 1)
    d = rec(D, 1)
    if t is None or d is None:
        print("  %-34s (missing record)" % note)
        continue
    ta, da = idx.art(t), idx.art(d)
    if not ta or not da or ta.get("kind") != "loose" or da.get("kind") != "loose":
        print("  %-34s (not loose: %s / %s)"
              % (note, ta and ta.get("kind"), da and da.get("kind")))
        continue
    try:
        pairs, unmapped, extra = S.plan_swap(ta, da)
    except S.SpriteError as exc:
        print("  %-34s REFUSED %s" % (note, exc))
        continue
    n, b = 0, 0
    for tn, dn in pairs:
        for suffix in ("_x1", "_x2"):
            tb = (tn[:-3] + suffix) if tn.endswith("_x1") else tn
            db = (dn[:-3] + suffix) if dn.endswith("_x1") else dn
            p = os.path.join(S.graphics_dir(GAME), db + ".sld")
            n += 1
            b += os.path.getsize(p) if os.path.exists(p) else 0
    identical = 0
    for tn, dn in pairs:
        for suffix in ("_x1", "_x2"):
            tb = (tn[:-3] + suffix) if tn.endswith("_x1") else tn
            db = (dn[:-3] + suffix) if dn.endswith("_x1") else dn
            tp = os.path.join(S.graphics_dir(GAME), tb + ".sld")
            dp = os.path.join(S.graphics_dir(GAME), db + ".sld")
            if os.path.exists(tp) and os.path.exists(dp):
                if open(tp, "rb").read() == open(dp, "rb").read():
                    identical += 1
    print("  %-34s %d pairs / %d files / %.1f MB / %d byte-identical"
          % (note, len(pairs), n, b / 1048576.0, identical))

print()
print("=" * 72)
print("4  what the emitter would report for such a mod")
print("=" * 72)
print("  json_files under DAT storage point? %s"
      % E.dat_storage_point_files({REL + "/x.sld": b"x"}))
print("  -> a sprites-only mod therefore needs NO carrier .dat")
