"""Deep dive on the three big storage points: WIDGETUI, DRS/SPRITES, DAT, STRINGS.
Extension breakdown, largest diffs, sample hashes. Read-only.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, json, hashlib, collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POM = os.path.join(GAME, "modes", "Pompeii")
OUT = _HERE_PATH("_probe", "modes_overlay")
OUTP = OUT

def load_tsv(p):
    d = {}
    with open(p, encoding="utf-8") as f:
        next(f)
        for line in f:
            line = line.rstrip("\n")
            if not line: continue
            r, s = line.rsplit("\t", 1)
            d[r] = int(s)
    return d

base = load_tsv(os.path.join(OUT, "inv_base.tsv"))
pom = load_tsv(os.path.join(OUT, "inv_pompeii.tsv"))

# ---- file-level comparison rows produced by p10 ----
det = collections.defaultdict(list)
with open(os.path.join(OUT, "cmp_filelevel.tsv"), encoding="utf-8") as f:
    next(f)
    for line in f:
        sp, kind, rel, pb, bb = line.rstrip("\n").split("\t")
        det[sp].append((kind, rel, pb, bb))

def ext(p):
    b = p.rsplit("/", 1)[-1]
    return ("." + b.rsplit(".", 1)[1].lower()) if "." in b else "(noext)"

print("=" * 70)
print("A) extension breakdown")
for sp in ["WIDGETUI", "SPRITES", "DRS", "DAT", "WPFG", "TERRAIN", "PALETTES", "PARTICLES",
           "CAMPAIGNS", "AI", "ACHIEVEMENTS", "COMMON_STRINGS"]:
    rows = det.get(sp, [])
    c = collections.Counter()
    for kind, rel, pb, bb in rows:
        c[(kind, ext(rel))] += 1
    print(f"\n-- {sp}: {len(rows)} comparison rows")
    agg = collections.defaultdict(int)
    for (k, e), n in c.items():
        agg[(k, e)] += n
    for (k, e) in sorted(agg):
        print(f"     {k:16s} {e:12s} {agg[(k,e)]}")

print("\n" + "=" * 70)
print("B) WIDGETUI: pompeii-only + differences (sampled)")
w = det["WIDGETUI"]
po = [r for r in w if r[0] == "POMPEII_ONLY"]
df = [r for r in w if r[0].startswith("DIFF")]
bo = [r for r in w if r[0] == "BASE_ONLY"]
print(f"  pompeii-only={len(po)} diff={len(df)} base-only={len(bo)}")
print("  --- pompeii-only, top 40 by size ---")
for kind, rel, pb, bb in sorted(po, key=lambda r: -int(r[2]))[:40]:
    print(f"     {int(pb):>12,}  {rel}")
print("  --- differing, top 30 by |Δ| ---")
for kind, rel, pb, bb in sorted(df, key=lambda r: -abs(int(r[2]) - int(r[3])))[:30]:
    print(f"     pom={int(pb):>12,}  base={int(bb):>12,}  Δ={int(pb)-int(bb):>+13,}  {rel}")
print("  --- pompeii-only extension counts ---")
cc = collections.Counter(ext(r[1]) for r in po)
print("    ", dict(cc.most_common()))
print("  --- differing extension counts ---")
cc = collections.Counter(ext(r[1]) for r in df)
print("    ", dict(cc.most_common()))

print("\n" + "=" * 70)
print("C) SPRITES (.sld etc)")
s = det["SPRITES"]
po = [r for r in s if r[0] == "POMPEII_ONLY"]
df = [r for r in s if r[0].startswith("DIFF")]
for nm, rows in [("pompeii-only", po), ("differing", df)]:
    cc = collections.Counter(ext(r[1]) for r in rows)
    print(f"  {nm}: {len(rows)}   ext={dict(cc.most_common(10))}")
print("  --- differing (same-name) SPRITES: top 25 by size ---")
for kind, rel, pb, bb in sorted(df, key=lambda r: -int(r[2]))[:25]:
    print(f"     pom={int(pb):>12,}  base={int(bb):>12,}  {rel}")
print("  --- pompeii-only SPRITES sample 20 ---")
for kind, rel, pb, bb in sorted(po, key=lambda r: -int(r[2]))[:20]:
    print(f"     {int(pb):>12,}  {rel}")

print("\n" + "=" * 70)
print("D) DAT storage point full listing (Pompeii side, compared)")
for kind, rel, pb, bb in sorted(det["DAT"], key=lambda r: (r[0], r[1])):
    print(f"     {kind:22s} pom={str(pb):>12s} base={str(bb):>12s}  {rel}")

print("\n" + "=" * 70)
print("E) STRINGS: all Pompeii files under resources/<locale>/strings/")
loc = [r for r in pom if r.startswith("resources/") and "/strings/" in r]
print(f"   count={len(loc)}")
for r in sorted(loc):
    print(f"     {pom[r]:>12,}  {r}")

print("\n" + "=" * 70)
print("F) hash spot-checks (recompute live)")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()
samples = [
    "widgetui/dialogs/ingame_main_menu.json",
    "resources/_common/dat/empires2_x2_p1.dat",
    "resources/_common/strings/key-value/key-value-strings-utf8.txt",
]
for rel in samples:
    bp = os.path.join(GAME, rel.replace("/", os.sep))
    pp = os.path.join(POM, rel.replace("/", os.sep))
    print(f"  {rel}")
    print(f"     base exists={os.path.exists(bp)} pom exists={os.path.exists(pp)}")
    if os.path.exists(bp) and os.path.exists(pp):
        print(f"     base sha={sha(bp)[:24]} size={os.path.getsize(bp)}")
        print(f"     pom  sha={sha(pp)[:24]} size={os.path.getsize(pp)}")
