"""Round 7: (a) old-vs-new Messages section, (b) campaign container structure."""
import json
import os
import re
import struct
import zlib
import warnings
warnings.filterwarnings("ignore")

SITE = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser"
HERE = os.path.dirname(os.path.abspath(__file__))
CAMP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"

print("=== Messages section: v1.36 (old) vs v1.54 (new) ===")
for v in ("1.36", "1.46", "1.53", "1.54"):
    p = os.path.join(SITE, "versions", "DE", f"v{v}", "structure.json")
    s = json.load(open(p, encoding="utf-8"))
    m = s["Messages"]["retrievers"]
    print(f"  v{v}: {len(m)} retrievers -> {list(m.keys())}")

print()
print("=== v1.36 Messages detail (first 3) ===")
s36 = json.load(open(os.path.join(SITE, "versions", "DE", "v1.36", "structure.json"), encoding="utf-8"))
print(json.dumps({k: s36["Messages"]["retrievers"][k] for k in list(s36["Messages"]["retrievers"])[:3]}, indent=1)[:800])

print()
print("=== CAMPAIGN CONTAINER ANALYSIS ===")
files = ["xcam1.aoe2campaign", "dcam0.aoe2campaign", "acam1.aoe2campaign", "fcam1.aoe2campaign"]
for fn in files:
    p = os.path.join(CAMP, fn)
    if not os.path.exists(p):
        print(f"  {fn}: MISSING")
        continue
    b = open(p, "rb").read()
    print(f"\n  --- {fn} ({len(b)} bytes) ---")
    print("   first 64:", b[:64].hex(" "), "|", repr(b[:64]))
    # look for embedded scenario version strings
    vers = [(m.start(), m.group().decode()) for m in re.finditer(rb"[12]\.\d\d", b)]
    print(f"   version-like strings: {len(vers)} -> first 20: {vers[:20]}")
    # count distinct
    from collections import Counter
    print("   version counts:", Counter(v for _, v in vers).most_common())
    # try to inflate anywhere
    found = []
    for off in range(0, min(len(b), 200000), 1):
        if len(found) >= 3:
            break
        d = zlib.decompressobj(-15)
        try:
            out = d.decompress(b[off:])
            out += d.flush()
            if d.eof and out:
                found.append((off, len(out)))
        except Exception:
            continue
    print(f"   exact-to-EOF deflate streams in first 200KB: {found}")

print()
print("=== campaign internal name table ===")
b = open(os.path.join(CAMP, "xcam1.aoe2campaign"), "rb").read()
strs = [(m.start(), m.group().decode("ascii", "replace")) for m in re.finditer(rb"[ -~]{4,}", b)]
print("  ascii runs:", len(strs))
for off, s in strs[:40]:
    print(f"   @{off:<8} {s[:100]}")

print()
print("=== lrm/wk1 campaign for comparison (older) ===")
for fn in sorted(os.listdir(CAMP))[:6]:
    p = os.path.join(CAMP, fn)
    b = open(p, "rb").read(16)
    print(f"  {fn:<28} {b[:12].hex(' ')} | {b[:6]!r}")
