import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
p = r"d:\games\steam\steamapps\common\AoE2DE\resources\_common\palettes\palettes.conf"
t = open(p, encoding="latin1").read()
print("first 30 lines:")
for ln in t.splitlines()[:30]: print("   ", ln[:120])
ids = re.findall(r"^\s*(\d+)\s", t, re.M)
print("leading-int lines:", len(ids), "distinct:", len(set(ids)), "min/max:", min(int(x) for x in ids), max(int(x) for x in ids))
print("lines with 'New Unit player colors':", t.count("New Unit player colors"))
# what do ids 64..71 point to
for ln in t.splitlines():
    m = re.match(r"\s*(\d+)\s*[:\s]\s*(\S+)", ln)
    if m and 62 <= int(m.group(1)) <= 72: print("   ", ln[:120])
