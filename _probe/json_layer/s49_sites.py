import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=" * 90)
w("Y. 'moved to' pointer stubs anywhere in the game tree (engine-authored)")
w("=" * 90)
for root, dirs, files in os.walk(GAME):
    for fn in files:
        if fn.lower().endswith(".json"):
            fp = os.path.join(root, fn)
            try:
                if os.path.getsize(fp) > 4000: continue
                t = open(fp, "rb").read().decode("utf-8-sig", "replace")
            except Exception:
                continue
            if "has been moved to" in t or "moved to" in t:
                w("  %-70s %s" % (os.path.relpath(fp, GAME), t.strip()[:160]))

w("")
w("=" * 90)
w("Z. history.json: keys vs exe parse site")
w("=" * 90)
hj = os.path.join(GAME, "widgetui", "history.json")
w("  exists=%s size=%s" % (os.path.exists(hj), os.path.getsize(hj) if os.path.exists(hj) else "-"))
if os.path.exists(hj):
    j = json.loads(open(hj, "rb").read().decode("utf-8-sig"))
    w("  top keys=%s" % (list(j)[:8] if isinstance(j, dict) else type(j).__name__))
w("  exe window @54131300:")
for m in re.finditer(rb"[ -~]{4,}", exe[54131200:54131700]):
    w("     %8d %s" % (54131200 + m.start(), m.group(0).decode("latin-1")))

w("")
w("=" * 90)
w("AA. FINAL: for each in-scope root JSON, the KEY-LITERAL BLOCK (proof of parser)")
w("=" * 90)
def keyset(o, acc=None):
    if acc is None: acc = set()
    if isinstance(o, dict):
        for k, v in o.items():
            acc.add(k); keyset(v, acc)
    elif isinstance(o, list):
        for v in o: keyset(v, acc)
    return acc

def firstsite(fp):
    """Find the offset of the densest run of this file's keys in the exe."""
    j = json.loads(open(fp, "rb").read().decode("utf-8-sig"))
    ks = sorted(k for k in keyset(j) if len(k) >= 4 and re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*$", k))
    offs = sorted((m.start(), k) for k in ks for m in [re.search(re.escape(k.encode()), exe)] if m)
    if not offs: return None, [], 0
    best = (0, 0, 0)
    for i in range(len(offs)):
        j2 = i
        while j2 + 1 < len(offs) and offs[j2 + 1][0] - offs[j2][0] <= 600:
            j2 += 1
        if j2 - i + 1 > best[0]:
            best = (j2 - i + 1, i, j2)
    n, i0, i1 = best
    return offs[i0][0], [k for _, k in offs[i0:i1 + 1]], n

for e in sorted(os.listdir(BASE)):
    if not e.endswith(".json"): continue
    fp = os.path.join(BASE, e)
    off, block, n = firstsite(fp)
    w("  %-38s site=%-9s run=%-3d block=%s" % (e, off, n, json.dumps(block, ensure_ascii=False)[:150]))
# CivTechTrees representative
for civ in ("BRITONS.json", "KHITANS.json"):
    fp = os.path.join(BASE, "CivTechTrees", civ)
    off, block, n = firstsite(fp)
    w("  CivTechTrees/%-24s site=%-9s run=%-3d block=%s" % (civ, off, n,
                                                             json.dumps(block, ensure_ascii=False)[:150]))
open(os.path.join(OUT, "s49_sites.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
