"""Precise numeric alignment between ASP's trigger enums and the game's string-table ids,
plus a quick look at editor UI + .gpv files."""
import json
import os
import re
import struct

SITE = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser"
HERE = os.path.dirname(os.path.abspath(__file__))
G = r"D:\Games\Steam\steamapps\common\AoE2DE"
KV = {int(k): v for k, v in json.load(open(os.path.join(HERE, "kv_all.json"), encoding="utf-8")).items()}


def enum_pairs(src, path):
    s = open(os.path.join(*path), encoding="utf-8").read()
    return [(nm, int(n)) for nm, n in re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*$", s, re.M)]


print("=== CONDITIONS: ASP index n vs kv[10500+n] ===")
pairs = enum_pairs(None, (SITE, "datasets", "conditions.py"))
pairs.sort(key=lambda x: x[1])
mismatch = []
for nm, n in pairs:
    kv = KV.get(10500 + n)
    if kv is None or kv.upper().replace("/", " ").replace(" ", "_") != nm:
        mismatch.append((n, nm, kv))
print(f"  entries={len(pairs)} misaligned/unnamed={len(mismatch)}")
for n, nm, kv in mismatch:
    print(f"   idx {n:>4}  ASP={nm:<34} kv[10500+{n}]={kv!r}")

print()
print("=== EFFECTS: ASP index n vs kv[11555+n] ===")
ep = enum_pairs(None, (SITE, "datasets", "effects.py"))
ep.sort(key=lambda x: x[1])
bad = []
for nm, n in ep:
    kv = KV.get(11555 + n)
    if kv is None:
        bad.append((n, nm, None))
    else:
        norm = kv.upper().replace("/", " ").replace(" ", "_").replace("-", "_")
        if norm != nm:
            bad.append((n, nm, kv))
print(f"  entries={len(ep)}; ASP min={ep[0][1]} max={ep[-1][1]}")
print(f"  first mismatch index: {bad[0] if bad else 'NONE'}")
print("  --- all mismatches ---")
for n, nm, kv in bad:
    print(f"   idx {n:>4}  ASP={nm:<40} kv[11555+{n}]={kv!r}")

print()
print("=== does a simple shift fix the tail? try kv = 11550+n for n>=? ===")
for shift in (11550, 11551, 11552, 11553, 11554, 11555):
    hits = sum(1 for nm, n in ep if (KV.get(shift + n) or "").upper().replace("/", " ").replace(" ", "_").replace("-", "_") == nm)
    print(f"  shift {shift}: {hits}/{len(ep)} names match")

print()
print("=== EDITOR UI: files mentioning scenario editor / trigger editing ===")
for dp, dns, fns in os.walk(os.path.join(G, "widgetui")):
    for fn in fns:
        if not fn.lower().endswith(".json"):
            continue
        p = os.path.join(dp, fn)
        low = fn.lower()
        if any(k in low for k in ("editor", "trigger", "scenario")):
            print(f"  {os.path.relpath(p, G)}  {os.path.getsize(p)}")
print()
print("  Tools_Builds contents:")
tb = os.path.join(G, "Tools_Builds")
if os.path.isdir(tb):
    for fn in sorted(os.listdir(tb))[:30]:
        p = os.path.join(tb, fn)
        print(f"   {fn}  {os.path.getsize(p) if os.path.isfile(p) else '<dir>'}")

print()
print("=== .gpv FILES (campaign preview assets) ===")
camp = os.path.join(G, "resources", "_common", "campaign")
for fn in sorted(os.listdir(camp))[:3]:
    if fn.endswith(".gpv"):
        b = open(os.path.join(camp, fn), "rb").read(48)
        print(f"  {fn}: {b[:16].hex(' ')} | {b[:10]!r}")

print()
print("=== CAMPAIGN JSON metadata: what fields a tool would need ===")
x = json.load(open(os.path.join(camp, "xcam1.json"), encoding="utf-8-sig"))
print("  top keys:", list(x))
print("  Scenarios entries:", len(x["Scenarios"]))
s0 = x["Scenarios"][0]
def keys(o, d=0, out=None):
    if out is None: out = []
    if isinstance(o, dict):
        for k, v in o.items():
            out.append(("  " * d) + k + ("" if isinstance(v, (dict, list)) else f" = {str(v)[:60]}"))
            if d < 2:
                keys(v, d + 1, out)
    elif isinstance(o, list) and o:
        keys(o[0], d, out)
    return out
for line in keys(s0)[:60]:
    print("   ", line)
