import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\palettes\palettes.conf"
t = open(p, encoding="latin1").read()
ids = re.findall(r"^\s*(\d+)\s*,", t, re.M)
print("id lines:", len(ids), "distinct:", len(set(ids)), "min:", min(map(int,ids)), "max:", max(map(int,ids)))
print("16..71 present:", sorted(int(x) for x in ids if 60 <= int(x) <= 72))
print()
print("'New Unit player colors' count:", t.count("New Unit player colors"))
for ln in t.splitlines():
    if "New Unit player colors" in ln: print("   >>", ln[:140])
print()
print("last 20 lines:")
for ln in t.splitlines()[-20:]: print("   ", ln[:120])
