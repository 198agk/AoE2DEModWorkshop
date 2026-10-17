# -*- coding: utf-8 -*-
"""Both directions of the displayed<->raw desync.

Direction A: unit.stat displayed_attack  -> panel number moves, damage does not.
Direction B: unit.attack_class (raw)     -> damage moves, panel number does not.

If both are true, the tool has no single intent that keeps the pair in step with
shipped data (which agrees 96-99.9% of the time).
"""
import sys, os, io, contextlib, tempfile, zlib
root = r"D:\Software\DeepSeek Harness\工作区2"
sys.path.insert(0, root)
from aoe2mod import api as A
from aoe2mod import dat as D
from aoe2mod.dat import parser as P, locate as L

tk = A.open_toolkit()
ver = tk.version
print("game version:", ver)

def raw_of(unit):
    t50 = unit.get("type50") or {}
    atk = [(a["class"], a["amount"]) for a in (t50.get("attacks") or [])]
    return t50.get("displayed_attack"), atk

def trace(label, intent):
    out = tempfile.mkdtemp(prefix="probe_")
    res = tk.build(dict(intent), out, title="probe", author="probe", overwrite=True)
    dat = os.path.join(out, "resources", "_common", "dat", "empires2_x2_p1.dat")
    raw = open(dat, "rb").read()
    data, how = P.load_dat(dat)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    loc = L.locate(data, parser=p)
    civs = loc[0]
    u = None
    for c in civs:
        for cand in c["units"]:
            if cand["id"] == intent.get("unit_id", 4):
                u = cand
                break
        if u:
            break
    disp, atk = raw_of(u)
    print()
    print("=== %s ===" % label)
    print("   plan :", res.get("description") if isinstance(res, dict) else res)
    print("   edits:", res["edit_count"] if isinstance(res, dict) and "edit_count" in res else "?")
    print("   AFTER: displayed_attack = %s | raw attacks = %s" % (disp, atk))
    print("   class3 =", dict(atk).get(3), " class4 =", dict(atk).get(4))

print()
print("BEFORE: archer displayed/raw")
data, how = P.load_dat(tk.dat_path)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
civs = L.locate(data, parser=p)[0]
u = next(cand for c in civs for cand in c["units"] if cand["id"] == 4)
disp, atk = raw_of(u)
print("   displayed_attack = %s | raw attacks = %s" % (disp, atk))

trace("A: unit.stat displayed_attack value=10",
      {"intent": "unit.stat", "unit": "Archer", "stat": "displayed_attack",
       "value": 10, "unit_id": 4})
trace("B: unit.attack_class attack class_id=3 delta=+6",
      {"intent": "unit.attack_class", "unit": "Archer", "kind": "attack",
       "class_id": 3, "delta": 6, "unit_id": 4})
