"""Full os.walk inventory of the game tree, EXCLUDING modes/ (base) and INCLUDING modes/ separately.
Writes two TSV catalogs + summary JSON. Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, sys, json, hashlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
MODES = os.path.join(GAME, "modes")
OUT = _HERE_PATH("_probe", "modes_overlay")

def walk(root, skip_prefixes=()):
    rows = []
    errs = []
    sp = tuple(os.path.normcase(p) for p in skip_prefixes)
    for dp, dn, fn in os.walk(root, onerror=lambda e: errs.append(repr(e))):
        nd = os.path.normcase(dp)
        dn[:] = [d for d in dn if not any(os.path.normcase(os.path.join(dp, d)).startswith(x) for x in sp)]
        if any(nd.startswith(x) for x in sp):
            continue
        for f in fn:
            p = os.path.join(dp, f)
            try:
                sz = os.path.getsize(p)
            except OSError as e:
                errs.append(f"{p}: {e}")
                continue
            rows.append((os.path.relpath(p, root).replace("\\", "/"), sz))
    return sorted(rows), errs

# ---- base tree (exclude modes) ----
base, berr = walk(GAME, skip_prefixes=[MODES, os.path.join(GAME, "modes")])
bbytes = sum(s for _, s in base)
print(f"BASE (excl modes): files={len(base)} bytes={bbytes} errors={len(berr)}")
json.dump(dict(files=len(base), bytes=bbytes, errors=berr),
          open(os.path.join(OUT, "inv_base_summary.json"), "w"), indent=1)
with open(os.path.join(OUT, "inv_base.tsv"), "w", encoding="utf-8") as f:
    f.write("relpath\tbytes\n")
    for r, s in base:
        f.write(f"{r}\t{s}\n")

# ---- modes/Pompeii ----
pom = os.path.join(MODES, "Pompeii")
por, perr = walk(pom)
pbytes = sum(s for _, s in por)
print(f"MODES/Pompeii: files={len(por)} bytes={pbytes} errors={len(perr)}")
json.dump(dict(files=len(por), bytes=pbytes, errors=perr),
          open(os.path.join(OUT, "inv_pompeii_summary.json"), "w"), indent=1)
with open(os.path.join(OUT, "inv_pompeii.tsv"), "w", encoding="utf-8") as f:
    f.write("relpath\tbytes\n")
    for r, s in por:
        f.write(f"{r}\t{s}\n")

# ---- top-level dir breakdown of both ----
def topdirs(rows):
    d = {}
    for r, s in rows:
        t = r.split("/")[0] if "/" in r else "(root)"
        e = d.setdefault(t, [0, 0])
        e[0] += 1
        e[1] += s
    return d

json.dump({"base": topdirs(base), "pompeii": topdirs(por)},
          open(os.path.join(OUT, "inv_topdirs.json"), "w"), indent=1)
print("wrote inv_*.tsv/json")
