# -*- coding: utf-8 -*-
"""Confirm the dat's unit attack/armor `Class` number indexes [AoE2DEArmorNames].

parse_dat.py's read_type50 (line 506) discards the armor/attack arrays.  We wrap
it and re-read them from the same byte stream.  Layout of read_type50:

  +0  i16  BaseArmor
  +2  i16  n_armor
  +4  n_armor x (i16 class, i16 amount)
  ..  i16  n_attack
  ..  n_attack x (i16 class, i16 amount)

Then we collect every observed Class number across all 136,861 unit records and
check it against the [AoE2DEArmorNames] table from AGE3NamesV0007.ini (0..36).
"""
import os
import _gamepaths as GP
import struct
import sys
import json
import collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "datparse"))
import parse_dat  # noqa: E402

DAT = (GP.DAT_DIR +
       r"\empires2_x2_p1.dat")
INI = (os.path.join(GP.GAME, "Tools_Builds") +
       r"\AGE3NamesV0007.ini")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- load [AoE2DEArmorNames] from the AGE ini --------------------------
armor_names = {}
section = None
with open(INI, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "AoE2DEArmorNames" and "=" in line:
            k, v = line.split("=", 1)
            if k.strip().lstrip("-").isdigit():
                armor_names[int(k)] = v.strip()
print("[AoE2DEArmorNames] entries: %d, range %d..%d"
      % (len(armor_names), min(armor_names), max(armor_names)))

_orig_read_type50 = parse_dat.read_type50
SAMPLES = []


def _wrap_type50(orig):
    def wrapper(r):
        start = r.pos
        orig(r)
        data = r.data
        try:
            base = struct.unpack_from("<h", data, start)[0]
            na = struct.unpack_from("<h", data, start + 2)[0]
            if not (0 <= na <= 40):
                return
            ar = []
            for i in range(na):
                c, a = struct.unpack_from("<hh", data, start + 4 + 4 * i)
                ar.append((c, a))
            off = start + 4 + 4 * na
            nt = struct.unpack_from("<h", data, off)[0]
            if not (0 <= nt <= 40):
                return
            at = []
            for i in range(nt):
                c, a = struct.unpack_from("<hh", data, off + 2 + 4 * i)
                at.append((c, a))
            SAMPLES.append((base, ar, at))
        except Exception:
            pass
    return wrapper


parse_dat.read_type50 = _wrap_type50(_orig_read_type50)

data, how = parse_dat.load_dat(DAT)
p = parse_dat.Parser(data)
st = p.parse()
print("parse ok: final %d / %d" % (p.r.pos, len(data)))
print("type50 records captured: %d" % len(SAMPLES))

arm_classes = collections.Counter()
atk_classes = collections.Counter()
for base, ar, at in SAMPLES:
    for c, a in ar:
        arm_classes[c] += 1
    for c, a in at:
        atk_classes[c] += 1

print()
print("distinct ARMOR class numbers : %d  range %d..%d"
      % (len(arm_classes), min(arm_classes), max(arm_classes)))
print("distinct ATTACK class numbers: %d  range %d..%d"
      % (len(atk_classes), min(atk_classes), max(atk_classes)))

print()
print("ARMOR classes -> [AoE2DEArmorNames] name (count):")
for c in sorted(arm_classes):
    nm = armor_names.get(c)
    flag = "" if nm is not None else "   <-- NOT IN INI"
    print("   %3d = %-38s x%-8d%s" % (c, nm, arm_classes[c], flag))

print()
print("ATTACK classes -> [AoE2DEArmorNames] name (count):")
for c in sorted(atk_classes):
    nm = armor_names.get(c)
    flag = "" if nm is not None else "   <-- NOT IN INI"
    print("   %3d = %-38s x%-8d%s" % (c, nm, atk_classes[c], flag))

unmapped = sorted(set(arm_classes) | set(atk_classes) - set(armor_names))
outside = sorted(c for c in (set(arm_classes) | set(atk_classes))
                 if c not in armor_names)
print()
print("class numbers observed but MISSING from the ini: %s" % (outside or "none"))

# a readable example
print()
print("example records (baseArmor, [(class,amount)...]):")
for base, ar, at in SAMPLES[:6]:
    print("   base=%d armor=%s attack=%s" % (base, ar[:6], at[:6]))

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_armor_classes.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump({
        "armor_class_counts": {str(k): v for k, v in sorted(arm_classes.items())},
        "attack_class_counts": {str(k): v for k, v in sorted(atk_classes.items())},
        "ini_armor_names": {str(k): v for k, v in sorted(armor_names.items())},
        "classes_missing_from_ini": outside,
    }, f, ensure_ascii=False, indent=1)
print("wrote _armor_classes.json")
