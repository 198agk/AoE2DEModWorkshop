import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, re, json, struct

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
DAT = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
OUT = _HERE_PATH("_probe", "json_layer")
buf = open(EXE, "rb").read()
low = bytes(buf[i] if 65 <= buf[i] <= 90 else buf[i] for i in range(len(buf)))  # not used; do manual lower
print("exe size", len(buf))

# build lowercase copy once
low = buf.lower()

def strings(seg, minlen=3):
    out = []
    cur = bytearray()
    for b in seg:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= minlen:
                out.append(cur.decode("ascii"))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(cur.decode("ascii"))
    return out

KEYLIKE = re.compile(r"^[A-Za-z][A-Za-z0-9 _]*$")

names = sorted(f for f in os.listdir(DAT) if f.lower().endswith(".json"))
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

summary = []
for f in names:
    nb = f.encode()
    nb2 = f.lower().encode()
    idxs = []
    start = 0
    while True:
        i = low.find(nb2, start)
        if i < 0:
            break
        idxs.append(i)
        start = i + 1
        if len(idxs) > 20:
            break
    if not idxs:
        summary.append((f, 0, None, 0, []))
        continue
    i = idxs[0]
    win = bytes(buf[i + len(nb): i + len(nb) + 1600])
    ss = strings(win)
    keys = [s for s in ss if KEYLIKE.match(s) and (("_" in s) or s.islower()) and 3 <= len(s) <= 45]
    summary.append((f, len(idxs), i, len(keys), keys[:18]))

w("### per-file exe presence and following key-like literals")
w("%-42s %4s %10s %5s  %s" % ("file", "n", "offset", "#key", "first key-like strings after filename"))
for f, n, i, nk, keys in summary:
    w("%-42s %4d %10s %5d  %s" % (f, n, (i if i is not None else "-"), nk, ", ".join(keys[:12])))

# also try full-path forms and case-variants
w("\n### variants / full path forms")
for pat in ["CivTechTrees", "civtechtrees", "AIResourceTypes", "airesourcetypes",
            "DATProcessingToolConfig", "adapter_blacklist", "adapterblacklist",
            "key-value-modded", "morematerials", "materials.json", "paphosfutureavailableunits",
            "chronicles_selection_group_def", "selection_group_def"]:
    p = pat.lower().encode()
    n = low.count(p)
    w("  %-34s occurrences=%d" % (pat, n))
    if n:
        s = 0
        for _ in range(min(n, 4)):
            i = low.find(p, s)
            seg = buf[max(0, i - 60): i + 260]
            w("      @%d  ...%s..." % (i, repr(seg)[:300]))
            s = i + 1

open(os.path.join(OUT, "s13_allsites.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
