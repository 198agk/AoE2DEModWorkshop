import json, os, collections, io, sys

D = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
P = os.path.join(D, "CivTechTrees")

out = io.StringIO()
def w(s=""):
    out.write(str(s) + "\n")

files = sorted(os.listdir(P))
w("### dir listing (%d entries)" % len(files))
for f in files:
    fp = os.path.join(P, f)
    w("  %-40s %10d  %s" % (f, os.path.getsize(fp), __import__("datetime").datetime.fromtimestamp(os.path.getmtime(fp))))

# pick a well known civ
target = "BRITONS.json"
cand = [f for f in files if f.upper().startswith("BRITON")]
w("\nBRITON-ish files: %r" % cand)
target = cand[0]

raw = open(os.path.join(P, target), "rb").read()
w("\n### %s size=%d first 400 bytes:" % (target, len(raw)))
w(repr(raw[:400]))
w("\nlast 200 bytes: %r" % raw[-200:])

j = json.loads(raw.decode("utf-8-sig"))
w("\n### top-level type=%s" % type(j).__name__)
if isinstance(j, dict):
    for k, v in j.items():
        w("  topkey %-30s type=%-6s len=%s" % (k, type(v).__name__, (len(v) if hasattr(v,'__len__') else '-')))
        if isinstance(v, list) and v:
            w("      elem0 type=%s keys=%s" % (type(v[0]).__name__, list(v[0].keys()) if isinstance(v[0], dict) else repr(v[0])[:80]))
        elif isinstance(v, dict):
            w("      keys=%s" % list(v.keys())[:20])

# full key universe with depth
def walk(o, path, depth):
    if isinstance(o, dict):
        for k, v in o.items():
            yield (path + "." + str(k) if path else str(k), type(v).__name__, depth)
            yield from walk(v, path + "." + str(k) if path else str(k), depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            yield from walk(v, path + "[]", depth + 1)

ku = collections.Counter()
ktypes = collections.defaultdict(collections.Counter)
maxd = 0
for p, t, d in walk(j, "", 0):
    ku[p] += 1
    ktypes[p][t] += 1
    maxd = max(maxd, d)
w("\n### distinct key paths: %d  maxdepth=%d" % (len(ku), maxd))
for p, c in ku.most_common(60):
    w("   %-50s n=%-7d types=%s" % (p, c, dict(ktypes[p])))

# sample one leaf node verbatim
w("\n### verbatim first building node (json.dumps indent=2, 700 chars):")
s = json.dumps(j, ensure_ascii=False, indent=2)
w(s[:700])

open(r"D:\Software\DeepSeek Harness\工作区2\_probe\json_layer\s10_ctt_schema.txt", "w", encoding="utf-8").write(out.getvalue())
print(out.getvalue()[:6000])
