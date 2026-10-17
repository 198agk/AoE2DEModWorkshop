import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re, glob, collections
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
CTT = os.path.join(BASE, "CivTechTrees")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

def load(p):
    t = {}
    for line in open(p, "rb").read().decode("utf-8-sig", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            t[int(parts[0])] = parts[1].strip().strip('"')
    return t

EN = os.path.join(GAME, "resources", "en", "strings", "key-value")
order = ["key-value-paphos-strings-utf8.txt", "key-value-pomodded-strings-utf8.txt",
         "key-value-modded-strings-utf8.txt", "key-value-strings-utf8.txt"]
w("=" * 74)
w("A. English string resolution: base / modded / paphos (which table wins?)")
w("=" * 74)
w("  files present: %s" % sorted(os.listdir(EN)))
tables = collections.OrderedDict()
for fn in sorted(os.listdir(EN)):
    if fn.endswith(".txt"):
        tables[fn] = load(os.path.join(EN, fn))
for fn, t in tables.items():
    w("  %-42s %6d ids" % (fn, len(t)))
merged = {}
for fn in order:                       # later wins -> base last = highest priority
    if fn in tables:
        merged.update(tables[fn])
for fn in tables:                      # then anything else
    if fn not in order:
        merged.update(tables[fn])
w("  merged en table: %d ids" % len(merged))
w("  relative priority list used (later overrides earlier), base last:")
w("    %s" % order)

need = [405028, 405027, 405052, 407132, 414055, 407084]
for sid in need:
    w("  sid=%-7d -> %r" % (sid, merged.get(sid)))

def norm(s):
    return re.sub(r"\s+", " ", s.replace("\\n", " ")).strip().lower()
tot = soft = nf = 0
real = []
for fp in sorted(glob.glob(os.path.join(CTT, "*.json"))):
    d = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    for lst in ("civ_techs_buildings", "civ_techs_units"):
        for nd in d[lst]:
            nm, sid = nd.get("Name"), nd.get("Name String ID")
            if nm is None or sid is None:
                continue
            tot += 1
            s = merged.get(sid)
            if s is None:
                nf += 1; continue
            if s == nm:
                continue
            if norm(s) == norm(nm):
                soft += 1
            else:
                real.append((os.path.basename(fp), lst, sid, nm, s))
w("")
w("  TOTAL nodes=%d  exact=%d  soft-break-only=%d  id-missing=%d  TRUE-MISMATCH=%d"
  % (tot, tot - soft - nf - len(real), soft, nf, len(real)))
w("  true mismatch per civ: %s" % dict(collections.Counter(r[0] for r in real)))
for r in real[:50]:
    w("     %-16s %-19s sid=%-7d Name=%-34r EN=%r" % r)

open(os.path.join(OUT, "s33_names.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
