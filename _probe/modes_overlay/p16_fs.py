"""p16: filesystem + JSON ground truth for the mod mechanism.
 - exact re-read of modes/Pompeii/Pompeii.json (byte level, key order)
 - does ANY other .json in the game tree mention use_modes_path_for_mods / storage_point_list?
 - locate user mod roots; enumerate installed mods; do any contain a modes/ dir?
 - inspect info.json / mod-status.json shapes
 - what do mods actually ship (top-level dirs of each mod)?
Read-only. Never writes outside _probe.
"""
import os, json, io, hashlib, re

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
POM = os.path.join(GAME, "modes", "Pompeii")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p16_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

P("#" * 100)
P("# 1) modes/Pompeii/Pompeii.json  — byte-exact")
p = os.path.join(POM, "Pompeii.json")
raw = open(p, "rb").read()
P(f"path {p}")
P(f"size {len(raw)}  sha256 {hashlib.sha256(raw).hexdigest()}")
P(f"first 3 bytes {raw[:3]!r}  (BOM?)")
txt = raw.decode("utf-8-sig")
P("--- raw text ---")
P(txt)
obj = json.loads(txt)
P("--- parsed keys (top level) ---")
P(json.dumps(list(obj.keys()), ensure_ascii=False))
P(f"--- storage_point_list: {len(obj['storage_point_list'])} entries ---")
for i, e in enumerate(obj["storage_point_list"]):
    present = {k: v for k, v in e.items()}
    P(f"  [{i:2d}] {json.dumps(present, ensure_ascii=False)}")

P("")
P("#" * 100)
P("# 2) search ALL .json/.txt/.xml in both trees for the two field names")
NEEDLES = [b"use_modes_path_for_mods", b"storage_point_list", b"morematerials", b"replace"]
found = {n.decode(): [] for n in NEEDLES}
nscan = 0
for root_label, root in [("base", GAME), ("pompeii", POM)]:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            fp = os.path.join(dp, f)
            if os.path.getsize(fp) > 40_000_000: continue
            try:
                b = open(fp, "rb").read()
            except Exception as e:
                continue
            nscan += 1
            for n in NEEDLES:
                if n in b:
                    found[n.decode()].append((root_label, os.path.relpath(fp, root), b.count(n)))
P(f"  files scanned: {nscan}")
for k, v in found.items():
    P(f"  {k!r}: {len(v)} file(s)")
    for t in v[:40]:
        P(f"      {t}")

P("")
P("#" * 100)
P("# 3) locate user mod roots")
cands = []
for env in ["USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA"]:
    v = os.environ.get(env)
    if v: cands.append((env, v))
for env, v in cands:
    P(f"  ${env} = {v}")
P("")
P("  --- probe well-known AoE2DE user dirs ---")
probe = []
up = os.environ.get("USERPROFILE", "")
for r in [os.path.join(up, "Games", "Age of Empires 2 DE"),
          os.path.join(up, "Games"),
          os.path.join(up, "Documents", "Games", "Age of Empires 2 DE"),
          os.path.join(up, "OneDrive", "Documents", "Games", "Age of Empires 2 DE")]:
    probe.append(r)
for r in probe:
    P(f"  {r} exists={os.path.exists(r)} isdir={os.path.isdir(r)}")
    if os.path.isdir(r):
        try:
            for x in sorted(os.listdir(r))[:40]:
                P(f"       {x}{'/' if os.path.isdir(os.path.join(r,x)) else ''}")
        except Exception as e:
            P(f"       <listdir failed: {e}>")

P("")
P("#" * 100)
P("# 4) userrelicid / mods tree")
def walk_mods(root, maxdepth=3):
    P(f"  --- walking {root} (depth<={maxdepth}) ---")
    base_depth = root.rstrip("\\").count("\\")
    hits = 0
    for dp, dn, fn in os.walk(root):
        d = dp.count("\\") - base_depth
        if d > maxdepth:
            dn[:] = []
            continue
        rel = os.path.relpath(dp, root)
        P(f"    [{d}] {rel}\\  ({len(fn)} files) {sorted(dn)[:12]}")
        hits += 1
        if hits > 120:
            P("    ... truncated"); break

up = os.environ.get("USERPROFILE", "")
root = os.path.join(up, "Games", "Age of Empires 2 DE")
if os.path.isdir(root):
    for sub in sorted(os.listdir(root)):
        sp = os.path.join(root, sub)
        if os.path.isdir(sp):
            P(f"  userdir child: {sub}")
            for sub2 in sorted(os.listdir(sp)):
                s2 = os.path.join(sp, sub2)
                P(f"      {sub2}{'/' if os.path.isdir(s2) else f' ({os.path.getsize(s2)} B)'}")
            m = os.path.join(sp, "mods")
            if os.path.isdir(m):
                flow = sorted(os.listdir(m))
                P(f"      mods/ -> {flow}")
                for f in flow:
                    fpd = os.path.join(m, f)
                    if os.path.isdir(fpd):
                        P(f"        {f}/ -> {sorted(os.listdir(fpd))}")

P("")
P("#" * 100)
P("# 5) game root: is there a mods dir inside the install?")
for x in ["mods", "modes", "widgetui", "resources", "Schema", "Tools_Builds"]:
    sp = os.path.join(GAME, x)
    if os.path.isdir(sp):
        ch = sorted(os.listdir(sp))
        P(f"  {x}/ ({len(ch)} children) {ch[:40]}")
    else:
        P(f"  {x}  -- not a dir")

P("")
P("#" * 100)
P("# 6) Schema dir contents (may document storage points)")
sd = os.path.join(GAME, "Schema")
if os.path.isdir(sd):
    for dp, dn, fn in os.walk(sd):
        for f in fn[:200]:
            fp = os.path.join(dp, f)
            P(f"    {os.path.relpath(fp, GAME)}  {os.path.getsize(fp)}")
F.close()
print("wrote p16_out.txt")
