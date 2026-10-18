import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\palettes"
allf = glob.glob(os.path.join(G,"**","*"), recursive=True)
allf = [p for p in allf if os.path.isfile(p)]
import collections
print("recursive ext hist:", dict(collections.Counter(os.path.splitext(p)[1].lower() for p in allf)))
top = [p for p in allf if os.path.dirname(p)==G]
print("top-level ext hist:", dict(collections.Counter(os.path.splitext(p)[1].lower() for p in top)))
mag = collections.Counter()
for p in allf:
    if os.path.splitext(p)[1].lower() in (".pal",".palx"):
        head = open(p,"rb").read(9)
        mag[head.decode("latin1")] += 1
print("magic:", dict(mag))
conf = [p for p in allf if p.lower().endswith(".conf")]
print("conf files:", [os.path.basename(p) for p in conf])
for p in conf:
    t=open(p,encoding="latin1").read()
    ids=set()
    for ln in t.splitlines():
        s=ln.split("//")[0].split("#")[0].strip()
        if s and s.split()[0].isdigit() if s else False: ids.add(s.split()[0])
    print("  %s: lines %d, numeric ids %d" % (os.path.basename(p), len(t.splitlines()), len(ids)))
print("spritecolors:", [os.path.basename(p) for p in allf if "spritecolors" in p.lower()])
print("subdirs:", sorted({os.path.dirname(p).replace(G,"") for p in allf}))
