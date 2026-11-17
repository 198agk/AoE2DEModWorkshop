import os as _os, sys as _sys
_p = _os.path.dirname(_os.path.abspath(__file__))
while _p and not _os.path.isfile(_os.path.join(_p, "_gamepaths.py")):
    _p = _os.path.dirname(_p)
if _p and _p not in _sys.path:
    _sys.path.insert(0, _p)
import _gamepaths as GP
"""Anatomy of one unit record: every field, its live value, and what a user-facing
'stat' actually decomposes into. Goal: know exactly what an intent like
'archers attack +2' must touch.

Also derives per-field byte offsets inside a Type50 unit record, so in-place
patching can address Attack / Armor / HP / etc. -- not just HitPoints.
"""
import os, sys, io, json, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_dat as P

BASE = GP.DAT
data, _ = P.load_dat(BASE)
p = P.Parser(data)
with contextlib.redirect_stdout(io.StringIO()):
    p.parse()
s = p.stats

civs = s["civs"]
print("civ count: %d" % len(civs))

# --- 1. full field dump of one representative unit -------------------------
def dump(rec, indent=0):
    pad = "  " * indent
    for k, v in rec.items():
        if isinstance(v, dict):
            print("%s%s:" % (pad, k)); dump(v, indent + 1)
        elif isinstance(v, list):
            if v and isinstance(v[0], dict):
                print("%s%s: [%d dicts]" % (pad, k, len(v)))
                if len(v) <= 6:
                    for i, x in enumerate(v):
                        print("%s  [%d]" % (pad, i)); dump(x, indent + 2)
                else:
                    print("%s  [0]" % pad); dump(v[0], indent + 2)
            else:
                preview = v if len(v) <= 24 else v[:24] + ["...(%d)" % len(v)]
                print("%s%s: %s" % (pad, k, preview))
        else:
            print("%s%s: %r" % (pad, k, v))

civ0 = civs[0]
print("\n=== civ[0] key list ===")
print(list(civ0.keys()))
units = civ0["units"]
print("civ[0] units: %d" % len(units))

target = None
for u in units:
    if u.get("id") == 4:      # ARCHR (Archer)
        target = u; break
print("\n=== civ[0] unit id=4 (Archer) FULL DUMP ===")
dump(target)

# --- 2. which fields differ between Archer(4) and Skirmisher(7)? -----------
def flat(d, pre=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out

byid = {u.get("id"): u for u in units}
for uid in (4, 7, 38, 83):
    if uid in byid:
        f = flat(byid[uid])
        print("\n--- unit %d flat scalar fields (%d) ---" % (uid, len(f)))
        if uid == 4:
            for k in sorted(f):
                print("   %-46s %r" % (k, f[k]))

# --- 3. attacks / armors semantics ----------------------------------------
print("\n=== attack & armor decomposition ===")
ARMS = json.load(open(os.path.join(os.path.dirname(HERE), "schema", "armor_classes.json"),
                      encoding="utf-8"))
cn = ARMS.get("class_names", {})
for uid in (4, 7, 38, 751, 83):
    u = byid.get(uid)
    if not u:
        continue
    t = u.get("type50") or {}
    atk = t.get("attacks") or []
    arm = t.get("armors") or []
    print("unit %-4s type=%-3s  attacks=%s  armors=%s" % (uid, u.get("type"), atk, arm))
    for kind, lst in (("attack", atk), ("armor", arm)):
        for e in lst:
            c = e.get("class") if isinstance(e, dict) else None
            a = e.get("amount") if isinstance(e, dict) else None
            print("      %-6s class %-4s (%-28s) amount %s"
                  % (kind, c, cn.get(str(c), "?"), a))

# sentinel convention: class -1 entries
print("\n=== sentinel check: entries with class -1 ===")
n = 0
for u in units[:400]:
    t = u.get("type50") or {}
    for e in (t.get("attacks") or []) + (t.get("armors") or []):
        if isinstance(e, dict) and e.get("class") == -1:
            n += 1
print("class -1 entries in first 400 units: %d" % n)

# --- 4. per-civ duplication of the very same stat --------------------------
print("\n=== per-civ copies: Archer(4) attack list across civs ===")
sigs = {}
for ci, c in enumerate(civs):
    u = next((x for x in c["units"] if x.get("id") == 4), None)
    if not u:
        continue
    t = u.get("type50") or {}
    sig = json.dumps([(e.get("class"), e.get("amount")) for e in (t.get("attacks") or [])])
    sigs.setdefault(sig, []).append((ci, c.get("name")))
for sig, who in sigs.items():
    print("  %d civs share identical attack list; e.g. %s" % (len(who), who[:3]))
print("  distinct attack-list signatures for unit 4: %d" % len(sigs))
