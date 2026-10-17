# -*- coding: utf-8 -*-
"""Reverse mirror routing on the ARMOUR side.

Two raw armour classes map to two different panel numbers:
  raw class 4  -> displayed_melee_armour
  raw class 3  -> displayed_pierce_armour
so a raw edit must find the RIGHT displayed field, not just any.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import sys, io, contextlib, struct
root = _HERE_PATH()
sys.path.insert(0, root)
from aoe2mod import api as A
from aoe2mod.intent import compiler as C
from aoe2mod.dat import parser as P, locate as L

tk = A.open_toolkit()
tk.version
data = tk._raw
bindings = C.load_schema()[1]

def apply_edits(res):
    buf = bytearray(data)
    for e in res["edits"]:
        if e.kind == "float":
            buf[e.off:e.off + 4] = struct.pack("<f", e.after)
        else:
            buf[e.off:e.off + e.width] = int(e.after).to_bytes(
                e.width, "little", signed=True)
    return bytes(buf)

def stream(blob):
    p = P.Parser(blob)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    return L.locate(blob, parser=p)[0]

def units_of(blob):
    return stream(blob)[0]["units"]

def fresh(uid):
    for u in tk._civs[0]["units"]:
        if u["id"] == uid:
            return u
    raise SystemExit("no unit %d" % uid)

def show(units, uid, tag):
    u = None
    for x in units:
        if x["id"] == uid:
            u = x
            break
    t50 = u.get("type50") or {}
    arm = {e["class"]: e["amount"] for e in (t50.get("armors") or [])}
    atk = {e["class"]: e["amount"] for e in (t50.get("attacks") or [])}
    print("   %-14s disp_melee=%-6s disp_pierce=%-6s disp_atk=%-6s | a3=%-5s a4=%-5s m3=%-5s m4=%-5s"
          % (tag, t50.get("displayed_melee_armour"), u.get("displayed_pierce_armour"),
             t50.get("displayed_attack"), atk.get(3), atk.get(4), arm.get(3), arm.get(4)))

print("=" * 112)
print("ARMOUR class 4 edit must move displayed_melee_armour ONLY")
print("=" * 112)
u = fresh(74)
print("   militia armors:", [(e["class"], e["amount"]) for e in (u["type50"]["armors"] or [])])
show(tk._civs[0]["units"], 74, "BEFORE")
r = C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": "Militia",
                                   "class_id": 4, "kind": "armour", "delta": 3},
                     parsed=tk._parsed, stats=tk._stats)
show(stream(apply_edits(r)), 74, "AFTER cls4+3")
print("   edits:", r["edit_count"])

print()
print("=" * 112)
print("ARMOUR class 3 edit must move displayed_pierce_armour ONLY")
print("=" * 112)
show(tk._civs[0]["units"], 74, "BEFORE")
r2 = C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": "Militia",
                                    "class_id": 3, "kind": "armour", "delta": 2},
                      parsed=tk._parsed, stats=tk._stats)
show(stream(apply_edits(r2)), 74, "AFTER cls3+2")
print("   edits:", r2["edit_count"])

print()
print("=" * 112)
print("plan() must match build on the armour reverse direction")
print("=" * 112)
for cls, delta in ((4, 3), (3, 2)):
    pl = tk.plan({"intent": "unit.attack_class", "unit": "Militia",
                  "class_id": cls, "kind": "armour", "delta": delta})
    bx = C.compile_intent(tk.dat_path, {"intent": "unit.attack_class", "unit": "Militia",
                                        "class_id": cls, "kind": "armour", "delta": delta},
                          parsed=tk._parsed, stats=tk._stats)
    ok = "AGREE" if pl["edit_count"] == bx["edit_count"] else "MISMATCH"
    print("   class %d delta %+d : plan %-4d build %-4d  %s"
          % (cls, delta, pl["edit_count"], bx["edit_count"], ok))

print()
print("=" * 112)
print("forward+reverse agree: displayed_attack edit and class-3 edit land twice")
print("=" * 112)
fwd = tk.plan({"intent": "unit.stat", "unit": "Archer", "stat": "displayed_attack", "delta": 6})
rev = tk.plan({"intent": "unit.attack_class", "unit": "Archer", "class_id": 3,
               "kind": "attack", "delta": 6})
print("   forward (unit.stat displayed_attack) : edits %d mirror_count %s"
      % (fwd["edit_count"], fwd.get("mirror_count")))
print("   reverse (unit.attack_class class 3)   : edits %d mirror_count %s"
      % (rev["edit_count"], rev.get("mirror_count")))
