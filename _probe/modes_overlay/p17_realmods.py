"""p17: ground truth from REAL installed mods.
Goal: determine, from files on disk, (a) what a mod folder looks like (top-level layout),
(b) whether any mod ships a `modes/` directory, (c) how mods override DAT / WIDGETUI / WPFG,
(d) what mod-status.json contains (Priority etc.), (e) whether mod file paths mirror game root
directly (no extra resources/ level) -- the claim to test.
Read-only. Writes only into _probe/modes_overlay.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, json, hashlib

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
OUT = _HERE_PATH("_probe", "modes_overlay")
F = open(os.path.join(OUT, "p17_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

USERS = [
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods",
    r"C:\Users\26913\Games\Age of Empires 2 DE\0\mods",
]

def size_of_tree(root):
    n = b = 0
    for dp, dn, fn in os.walk(root):
        for f in fn:
            fp = os.path.join(dp, f)
            try:
                b += os.path.getsize(fp); n += 1
            except OSError:
                pass
    return n, b

# Game-root top-level names, to test "mod mirrors game root" claim
game_top = set(os.listdir(GAME))
P("#" * 100)
P("# 0) game root top-level (for mirror test)")
P(f"  {sorted(game_top)}")

for U in USERS:
    P("")
    P("#" * 100)
    P(f"# USER MOD DIR: {U}")
    if not os.path.isdir(U):
        P("  ABSENT"); continue
    P(f"  children: {sorted(os.listdir(U))}")
    ms = os.path.join(U, "mod-status.json")
    if os.path.isfile(ms):
        P("")
        P("  --- mod-status.json (raw) ---")
        try:
            P(open(ms, "r", encoding="utf-8", errors="replace").read()[:20000])
        except Exception as e:
            P(f"   <read failed {e}>")
    else:
        P("  no mod-status.json here")

    for kind in ["local", "subscribed"]:
        KD = os.path.join(U, kind)
        if not os.path.isdir(KD):
            P(f"  {kind}/ ABSENT"); continue
        P("")
        P("#" * 90)
        P(f"# {kind}/  -> {sorted(os.listdir(KD))}")
        for mod in sorted(os.listdir(KD)):
            MD = os.path.join(KD, mod)
            if not os.path.isdir(MD):
                P(f"  - file {mod} ({os.path.getsize(MD)} B)"); continue
            n, b = size_of_tree(MD)
            P("")
            P(f"  === MOD {kind}/{mod} ===  {n} files, {b} B")
            # immediate children + their types
            tops = sorted(os.listdir(MD))
            P(f"    top-level: {tops}")
            # mirror test: which top-level names are plausible game-root names
            mirror = [t for t in tops if t in game_top]
            P(f"    top-level matching a game-root name: {mirror}")
            P(f"    top-level NOT in game-root names: {[t for t in tops if t not in game_top]}")
            # depth-2 listing (first 60)
            cnt = 0
            for dp, dn, fn in os.walk(MD):
                rel = os.path.relpath(dp, MD)
                d = 0 if rel == "." else rel.count("\\") + 1
                if d > 2:
                    dn[:] = []; continue
                if rel != ".":
                    P(f"      d{d} {rel}\\ ({len(fn)} files) {sorted(dn)[:10]}")
                cnt += 1
                if cnt > 80:
                    P("      ... trunc"); break
            ij = os.path.join(MD, "info.json")
            if os.path.isfile(ij):
                P(f"    info.json: {os.path.getsize(ij)} B")
                try:
                    P("      " + open(ij, "r", encoding="utf-8", errors="replace").read()[:1200].replace("\n", "\n      "))
                except Exception as e:
                    P(f"      <{e}>")
            # does it contain a modes dir?
            for dp, dn, fn in os.walk(MD):
                if os.path.basename(dp).lower() == "modes":
                    P(f"    *** FOUND modes/ dir at {os.path.relpath(dp, MD)} -> {sorted(os.listdir(dp))[:20]}")

P("")
P("#" * 100)
P("# 7) the mods' override targets: hunt for DAT/WIDGETUI/WPFG files inside mods")
for U in USERS:
    for kind in ["local", "subscribed"]:
        KD = os.path.join(U, kind)
        if not os.path.isdir(KD): continue
        for mod in sorted(os.listdir(KD)):
            MD = os.path.join(KD, mod)
            if not os.path.isdir(MD): continue
            hits = []
            for dp, dn, fn in os.walk(MD):
                for f in fn:
                    rel = os.path.relpath(os.path.join(dp, f), MD)
                    low = rel.lower()
                    if (low.endswith(".dat") or "widgetui" in low or "wpfg" in low
                            or low.startswith("modes" + os.sep) or "morematerials" in low
                            or low.endswith(".sld") or "key-value" in low):
                        hits.append((rel, os.path.getsize(os.path.join(dp, f))))
            if hits:
                P(f"  {kind}/{mod}: {len(hits)} override-shaped file(s)")
                for h in hits[:25]:
                    P(f"      {h}")
F.close()
print("wrote p17_out.txt")
