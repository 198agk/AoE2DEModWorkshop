import re, io, collections

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
data = open(EXE, "rb").read()
out = io.StringIO()
w = out.write

runs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[\x20-\x7e]{3,}", data)]
w("runs: %d\n" % len(runs))

FLAG = re.compile(r"^[A-Z][A-Z0-9_]{2,40}$")
FLAGISH = re.compile(r"^[A-Z][A-Z0-9_]{2,40}$|^[A-Za-z_][A-Za-z0-9_]{2,40}$")

# Find maximal clusters of >=6 consecutive ALLCAPS runs (a flag table block)
clusters = []
cur = []
for off, s in runs:
    if FLAG.match(s):
        if cur and off - cur[-1][0] > 400:
            if len(cur) >= 6:
                clusters.append(cur)
            cur = []
        cur.append((off, s))
    else:
        if cur and len(cur) >= 6:
            clusters.append(cur)
        cur = []
if len(cur) >= 6:
    clusters.append(cur)

w("\n### %d ALLCAPS clusters (>=6) ###\n" % len(clusters))
for c in sorted(clusters, key=lambda x: -len(x))[:20]:
    w("\n--- cluster %d items @0x%x ---\n" % (len(c), c[0][0]))
    w("   " + ", ".join(s for _, s in c) + "\n")

# Also collect ALL distinct flags anywhere with a description-run immediately before
w("\n\n### flags preceded within 200 bytes by a sentence ###\n")
def is_desc(s):
    return " " in s and len(s) >= 12 and s.endswith(".") or (len(s) >= 20 and " " in s)
found = {}
for i, (off, s) in enumerate(runs):
    if not FLAG.match(s):
        continue
    back = [runs[j] for j in range(max(0, i - 4), i)]
    for boff, bs in reversed(back):
        if off - boff > 300:
            break
        if len(bs) >= 14 and " " in bs and not FLAG.match(bs):
            found.setdefault(s, []).append(bs)
            break

w("distinct flags with preceding sentence: %d\n" % len(found))
for f in sorted(found):
    w("  %-40s %s\n" % (f, found[f][0][:130]))

txt = out.getvalue()
io.open(r"D:\Software\DeepSeek Harness\工作区2\_probe\ui_surfaces\exe_flagtable2.txt", "w", encoding="utf-8").write(txt)
print("clusters:", len(clusters), "flags w/ desc:", len(found))
