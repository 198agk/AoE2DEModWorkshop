# -*- coding: utf-8 -*-
"""Does the Displayed* -> raw mirror actually move both numbers?

Three things must hold:
  1. displayed_attack +N moves BOTH the panel value and the raw class 3/4 entry.
  2. displayed_melee_armour / displayed_pierce_armour likewise (armor side).
  3. A record whose two numbers deliberately differ keeps that difference --
     the mirror carries the DELTA, it must not copy the displayed value.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import sys, os, io, contextlib, zlib, struct
root = _HERE_PATH()
sys.path.insert(0, root)
from aoe2mod import api as A
from aoe2mod.intent import compiler as C
from aoe2mod.dat import parser as P, locate as L

tk = A.open_toolkit()
tk.version
data = tk._raw

def raw_lookup(units, uid):
    for u in units:
        if u["id"] == uid:
            return u
    return None

def show(tag, units, uid, label):
    u = raw_lookup(units, uid)
    if u is None:
        print("   %s: MISSING" % label)
        return
    t50 = u.get("type50") or {}
    atk = {c: a for c, a in ((x["class"], x["amount"]) for x in (t50.get("attacks") or []))}
    arm = {c: a for c, a in ((x["class"], x["amount"]) for x in (t50.get("armors") or []))}
    print("   %-22s id %-5d disp_atk=%-6s disp_melee=%-6s disp_pierce=%-6s | a3=%-6s a4=%-6s m3=%-6s m4=%-6s"
          % (label, uid,
             t50.get("displayed_attack"), t50.get("displayed_melee_armour"),
             u.get("displayed_pierce_armour"),
             atk.get(3), atk.get(4), arm.get(3), arm.get(4)))

def apply_edits(data, res):
    """Rebuild the patched stream from the result's Edit list."""
    buf = bytearray(data)
    for e in res["edits"]:
        if e.kind == "float":
            buf[e.off:e.off + 4] = struct.pack("<f", e.after)
        else:
            buf[e.off:e.off + e.width] = int(e.after).to_bytes(
                e.width, "little", signed=True)
    return bytes(buf)

def locate_stream(blob):
    p = P.Parser(blob)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, _, _, _ = L.locate(blob, parser=p)
    return civs

print("=" * 118)
print("CASE 1  archer (displayed == raw, class 3)")
print("=" * 118)
show(None, tk._civs[0]["units"], 4, "BEFORE")

pl = tk.plan({"intent": "unit.stat", "unit": "Archer", "stat": "displayed_attack", "delta": 6})
print("   plan: %s | edits %d" % (pl["description"], pl["edit_count"]))
r = C.compile_intent(tk.dat_path, {"intent": "unit.stat", "unit": "Archer",
                                   "stat": "displayed_attack", "delta": 6},
                     parsed=tk._parsed, stats=tk._stats)
print("   compile: edits %d | changed %s | verification ok %s"
      % (r["edit_count"], r["verification"].get("changed"),
         r["verification"].get("ok")))
show(None, locate_stream(apply_edits(data, r))[0]["units"], 4, "AFTER +6")

print()
print("=" * 118)
print("CASE 2  mirrored edit on the ARMOUR side (militia melee armour)")
print("=" * 118)
show(None, tk._civs[0]["units"], 74, "BEFORE")
r2 = C.compile_intent(tk.dat_path, {"intent": "unit.stat", "unit": "Militia",
                                    "stat": "displayed_melee_armour", "delta": 3},
                      parsed=tk._parsed, stats=tk._stats)
show(None, locate_stream(apply_edits(data, r2))[0]["units"], 74, "AFTER +3")

print()
print("=" * 118)
print("CASE 3  DIVERGENT record id 1113 (Projectile Heavy Scorpion: disp 8, raw class3 6)")
print("=" * 118)
show(None, tk._civs[0]["units"], 1113, "BEFORE")
try:
    r3 = C.compile_intent(tk.dat_path, {"intent": "unit.stat", "unit": 1113,
                                        "stat": "displayed_attack", "delta": 2},
                          parsed=tk._parsed, stats=tk._stats)
    show(None, locate_stream(apply_edits(data, r3))[0]["units"], 1113, "AFTER +2")
    print()
    print("   EXPECT: disp_atk 8 -> 10, a3 6 -> 8  (the +2 offset SURVIVES)")
except C.IntentError as e:
    print("   refused: %s" % e)

print()
print("=" * 118)
print("CASE 4  the reverse direction: unit.attack_class writes raw only")
print("=" * 118)
show(None, tk._civs[0]["units"], 4, "BEFORE")
r4 = C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": "Archer",
                                    "class_id": 3, "kind": "attack", "delta": 2},
                      parsed=tk._parsed, stats=tk._stats)
show(None, locate_stream(apply_edits(data, r4))[0]["units"], 4, "AFTER +2")
print("   NOTE: if disp_atk stays 4, this direction is still desynced.")
