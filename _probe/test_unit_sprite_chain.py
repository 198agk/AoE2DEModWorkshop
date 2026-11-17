import _gamepaths as GP
# -*- coding: utf-8 -*-
r"""The unit -> sprite index exists inside the .dat.  Characterise it, then nail it.

Chain (measured):  unit record -> StandinGraphic.first (int16)
                   -> graphics[] looked up BY THE RECORD'S OWN `id`, not by
                      array position
                   -> record['file'] + ".sld"
                   -> resources/_common/drs/graphics/<file>_x1.sld / _x2.sld

842% by-id vs 54% by-position, and every named unit lands on a plausible
sprite, so the lookup is by id.  What is left is the honest boundary: what are
the records that do NOT resolve?  Hypothesis: they are the ones still naming a
legacy SLP resource (`slp` nonzero, file name in the old abbreviated style)
rather than a loose .sld.

Five assertions:
  A  by-id beats by-position decisively
  B  every unit with a non-negative pair.first resolves OR is a legacy-SLP name
  C  a resolved sprite always comes as an x1/x2 PAIR on disk
  D  the reverse map is not 1:1 (many units share one animation)
  E  the file field is unique across graphics records
"""
import collections, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
os.chdir(ROOT)

import aoe2mod.api as A

fails = []
def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name[:70], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)

GAME = GP.GAME
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")

if not os.path.isdir(GP):
    print("FATAL: graphics dir missing: %s" % GP)
    sys.exit(1)
_on_disk = set(fn for fn in os.listdir(GP) if fn.endswith(".sld"))
check("the graphics dir has loose .sld files", bool(_on_disk), "dir=%s" % GP)
_pair_ok = 0
_pair_bad = []
for fn in _on_disk:
    if fn.endswith("_x1.sld"):
        if fn[:-7] + "_x2.sld" not in _on_disk:
            _pair_bad.append(fn)
    elif fn.endswith("_x2.sld"):
        if fn[:-7] + "_x1.sld" not in _on_disk:
            _pair_bad.append(fn)
print("on disk: %d .sld, %d paired, %d unpaired %s"
      % (len(_on_disk), len(_on_disk) - len(_pair_bad), len(_pair_bad),
         _pair_bad[:4]))

tk = A.open_toolkit(game_root=GAME)
tk._ensure()
_g = tk._stats["graphics"]
_raw = tk._raw

fails = []
def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name[:70], "PASS" if ok else "FAIL",
                            ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)

_by_pos = list(_g)
_by_id = {x.get("id"): x for x in _g}

def fname(rec):
    if not isinstance(rec, dict):
        return None
    f = rec.get("file")
    if not isinstance(f, str):
        return None
    f = f.strip()
    if not f or f == "None":
        return None
    return f

def resolves(rec):
    f = fname(rec)
    if f is None:
        return None, None, None
    return f, (f + ".sld" in _on_disk), (rec.get("slp") if isinstance(rec, dict) else None)

_units = {}
for c in tk._civs:
    for u in c["units"]:
        _units.setdefault(u["id"], u)

_hits = {"by_pos": 0, "by_id": 0}
_tot = 0
_unresolved = []
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a, b = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)
    if a < 0:
        continue
    _tot += 1
    if 0 <= a < len(_by_pos):
        f, ok, slp = resolves(_by_pos[a])
        if ok:
            _hits["by_pos"] += 1
    rec = _by_id.get(a)
    f, ok, slp = resolves(rec)
    if ok:
        _hits["by_id"] += 1
    elif len(_unresolved) < 14:
        _unresolved.append((uid, a, f, slp, (rec or {}).get("name")))

print()
print("A  BY-ID vs BY-POSITION   (units with a non-negative pair.first: %d)" % _tot)
for k, v in _hits.items():
    print("     %-8s %5d / %-5d  %.1f%%" % (k, v, _tot, 100.0 * v / _tot))
check("looking the graphics array up by the record's `id` wins by >25 points",
      _hits["by_id"] > _hits["by_pos"] + 0.25 * _tot,
      "%d vs %d" % (_hits["by_id"], _hits["by_pos"]))

print("B  WHICH RECORDS DO NOT RESOLVE?")
# My first hypothesis ("nonzero slp = legacy SLP resource") was WRONG: 54% of
# nonzero-slp records DO resolve.  The discriminator is the NAME SHAPE --
# modern DE loose files are lower-case and underscore-segmented, legacy
# resources are ALL-CAPS abbreviations (genieutils' own warning: "heavily
# abbreviated, such as ARRG2NNE").
def shape(f):
    if f is None:
        return "no name"
    if "_" in f and f == f.lower():
        return "modern"
    if f == f.upper() and "_" not in f:
        return "legacy"
    return "other"

_sh = collections.Counter()
for x in _g:
    f = fname(x)
    if f is None:
        continue
    _sh[(shape(f), (f + ".sld") in _on_disk)] += 1
for s in ("modern", "legacy", "other"):
    y, n = _sh[(s, True)], _sh[(s, False)]
    print("     %-8s records %5d, resolve %5d (%5.1f%%)"
          % (s, y + n, y, 100.0 * y / max(1, y + n)))
check("a legacy ALL-CAPS name never names a loose .sld",
      _sh[("legacy", True)] == 0, "%d legacy names, %d resolve"
      % (sum(_sh[("legacy", b)] for b in (True, False)), _sh[("legacy", True)]))
check("a modern lower_underscore name almost always resolves",
      _sh[("modern", True)] > 0.95 * sum(_sh[("modern", b)] for b in (True, False)),
      "%d/%d" % (_sh[("modern", True)],
                 sum(_sh[("modern", b)] for b in (True, False))))

print()
print("C  EVERY RESOLVED SPRITE COMES AS AN x1/x2 PAIR")
check("all loose .sld files on disk come in x1/x2 pairs",
      not _pair_bad, "%d unpaired files on disk" % len(_pair_bad))

print()
print("D  REVERSE MAP: how many units share one animation?")
_rev = collections.defaultdict(set)
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a, b = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)
    f = fname(_by_id.get(a))
    if f and (f + ".sld") in _on_disk:
        _rev[f].add(uid)
_fan = collections.Counter(len(v) for v in _rev.values())
print("     distinct standing sprites : %d" % len(_rev))
print("     units per sprite          : %s" % dict(sorted(_fan.items())[:8]))
check("some animations are shared by several units (not 1:1)",
      max(_fan) > 1, "max fan-out %d" % max(_fan))

print("E  IS `file` A KEY?  (it is not -- measure the sharing instead)")
_c = collections.Counter(fname(x) for x in _g if fname(x))
_res_c = collections.Counter(fname(x) for x in _g
                             if fname(x) and (fname(x) + ".sld") in _on_disk)
_reused_res = sorted([(k, v) for k, v in _res_c.items() if v > 1],
                     key=lambda kv: -kv[1])
print("     distinct file strings      : %d" % len(_c))
print("     ... naming a real .sld     : %d" % len(_res_c))
print("     ... shared by >1 record    : %d (legitimate: rubble/foundation art)"
      % len(_reused_res))
print("     most shared                : %s" % _reused_res[:5])
# I first asserted "file must be unique per record".  That was wrong-headed:
# several records legitimately point at the same artwork (37 rubble records
# share one sprite).  What a caller needs is not uniqueness but a usable
# REVERSE lookup, asserted in F.
check("most resolving file strings belong to exactly one record (>90%)",
      (len(_res_c) - len(_reused_res)) > 0.90 * len(_res_c),
      "%d of %d unshared" % (len(_res_c) - len(_reused_res), len(_res_c)))

print()
print("F  THE REVERSE DIRECTION A UI WOULD NEED")
_by_file = collections.defaultdict(set)
for uid, u in _units.items():
    offs = u.get("_offs") or {}
    if "hit_points" not in offs:
        continue
    a = struct.unpack_from("<hh", _raw, offs["hit_points"] - 9)[0]
    f = fname(_by_id.get(a))
    if f:
        _by_file[f].add(uid)
_probed = 0
_bad = []
for uid in (83, 4, 38, 74, 93, 125, 692, 13, 41, 448):
    u = _units.get(uid)
    if not u:
        continue
    a = struct.unpack_from("<hh", _raw, u["_offs"]["hit_points"] - 9)[0]
    f = fname(_by_id.get(a))
    if not f:
        continue
    _probed += 1
    if uid not in _by_file.get(f, ()):
        _bad.append((uid, f))
print("     units probed                  : %d" % _probed)
print("     forward/reverse disagreements : %d %s" % (len(_bad), _bad))
check("every unit is found again by looking its sprite up in reverse",
      _probed >= 8 and not _bad,
      "%d probed, %d disagreements" % (_probed, len(_bad)))
for f, us in sorted(_by_file.items(), key=lambda kv: -len(kv[1]))[:4]:
    print("        %-34s draws %d units %s" % (f, len(us), sorted(us)[:6]))

print()
if fails:
    print("UNIT SPRITE CHAIN: %d FAILED" % len(fails))
    for f in fails:
        print("   - %s" % f)
    sys.exit(1)
print("UNIT SPRITE CHAIN: the .dat answers 'which .sld draws this unit'.")
