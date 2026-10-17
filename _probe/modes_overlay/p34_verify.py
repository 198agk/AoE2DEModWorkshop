"""p34: verify the widgetui differing/only extension breakdown from the authoritative
file-level table, so the report's numbers are exact rather than approximate.
Read-only -> p34_out.txt
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, csv, collections, json

OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p34_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

path = os.path.join(OUT, "cmp_filelevel.tsv")
with open(path, encoding="utf-8", newline="") as f:
    rdr = csv.DictReader(f, delimiter="\t")
    rows = list(rdr)
P(f"cmp_filelevel.tsv: {len(rows)} rows; columns = {list(rows[0].keys())}")

# locate the storage-point + classification columns robustly
cols = list(rows[0].keys())
def pick(*cands):
    for c in cands:
        for k in cols:
            if k.lower() == c.lower(): return k
    return None
SP = pick("sp", "storage_point", "type", "point")
CL = pick("class", "classification", "kind", "status")
PT = pick("path", "file", "rel", "relpath")

P(f"using columns: SP={SP!r} CLASS={CL!r} PATH={PT!r}")
if not (SP and CL):
    P("!! could not identify columns; dumping header + 3 sample rows:")
    P(str(cols)); 
    for r in rows[:3]: P(str(r))
    F.close(); raise SystemExit

by_sp = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    by_sp[r[SP]][r[CL]] += 1
P("")
P("# classification counts per storage point (all 28):")
for sp in sorted(by_sp):
    c = by_sp[sp]
    P(f"  {sp:24s} total={sum(c.values()):6d}  {dict(c)}")

P("")
P("# widgetui extension breakdown, by class:")
wu = [r for r in rows if r[SP] == "WIDGETUI"]
P(f"  widgetui rows = {len(wu)}")
for cl in sorted(set(r[CL] for r in wu)):
    exts = collections.Counter(os.path.splitext(r[PT])[1].lower() for r in wu if r[CL] == cl)
    P(f"  {cl:16s} n={sum(exts.values()):5d}  {dict(exts.most_common())}")

P("")
P("# global per-class totals:")
allc = collections.Counter(r[CL] for r in rows)
P(f"  {dict(allc)}")
F.close()
print("wrote p34_out.txt")
