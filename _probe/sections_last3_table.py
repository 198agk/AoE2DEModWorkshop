"""Definitive per-value resolution table for icons.json's last three segments.

Prints, for every value in Notification / StatIcons / MenuIcons:
  value -> rule -> resolved material -> atlas -> FileName -> on-disk?

Also cross-checks the engine-side hardcoded material tokens found in the exe.
Read-only.
"""
import json
import os
import re
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
W = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

icons = json.load(open(os.path.join(W, "icons.json"),
                       "r", encoding="utf-8-sig", errors="replace"))
mat = json.load(open(os.path.join(W, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))

ref_to_file, ref_to_atlas = {}, {}
for wrap in mat.get("AtlasTextures", []):
    ad = wrap.get("AtlasDef") or {}
    for t in ad.get("Textures", []):
        if t.get("RefName"):
            ref_to_file[t["RefName"]] = t.get("FileName")
            ref_to_atlas[t["RefName"]] = ad.get("Name")

matdefs = {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        matdefs[md["Name"]] = md

def resolve(name):
    """material name -> (atlas, FileName, on_disk)"""
    md = matdefs.get(name)
    if md is None:
        return None
    k = md.get("TextureRef") or name
    fn = ref_to_file.get(k)
    disk = None
    if fn:
        disk = os.path.isfile(os.path.join(W, fn.replace("/", os.sep)))
    return (ref_to_atlas.get(k), fn, disk)

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

FILES = {norm(n): n for n in matdefs}

def by_norm(cand):
    return FILES.get(norm(cand))

def by_substr(s):
    n = norm(s)
    hits = [orig for k, orig in FILES.items() if n and n in k and orig.startswith("StatIcons")]
    return hits

print("=" * 100)
print("A. Notification (2 values)")
print("=" * 100)
NMAP = {"wonder_icon": "ScorePanelWonder", "relic_icon": "ScorePanelRelic"}
for k, v in sorted(icons.get("Notification", {}).items()):
    m = NMAP.get(v)
    print("   [%s] %-14s -> %-20s %s" % (k, v, m, resolve(m) if m else "<no mapping>"))

print()
print("=" * 100)
print("B. StatIcons (24 values)")
print("=" * 100)
rows = []
ok = 0
for k, v in sorted(icons.get("StatIcons", {}).items()):
    rule, m = None, None
    if v in matdefs:                                  # bare material name
        rule, m = "bare-name", v
    else:
        stem = v[len("stat_icon_"):] if v.startswith("stat_icon_") else v
        cand = "StatIcons" + stem[:1].upper() + stem[1:]
        if cand in matdefs:
            rule, m = "derive", cand
        else:
            g = by_norm(cand)
            if g:
                rule, m = "norm", g
            else:
                sub = by_substr(stem)
                if len(sub) == 1:
                    rule, m = "substr", sub[0]
    r = resolve(m) if m else None
    if r:
        ok += 1
    rows.append((k, v, rule, m, r))
    print("   [%s] %-28s %-10s %-28s %s" % (
        k, v, rule or "MISS", m or "-",
        ("%s | %s | disk=%s" % r) if r else "-"))
print("   -> %d / %d resolved" % (ok, len(rows)))

print()
print("=" * 100)
print("C. MenuIcons (9 values)")
print("=" * 100)
ROME = {"submenu_oligarchy": "TechIconsT155Oligarchy",
        "submenu_democracy": "TechIconsT156Democracy",
        "submenu_tyranny": "TechIconsT154Tyranny"}
for k, v in sorted(icons.get("MenuIcons", {}).items()):
    # try the Return-of-Rome government mapping
    m = ROME.get(v)
    if m is None and v in matdefs:
        m = v
    if m is None:
        cand = "TechIcons" + "".join(p[:1].upper() + p[1:] for p in v.split("_"))
        m = cand if cand in matdefs else None
    sym = "GOVT" if v in ROME else ("exact" if m else "DEAD")
    print("   [%s] %-36s %-5s %-28s %s" % (
        k, v, sym, m or "-", resolve(m) if m else "-"))

print()
print("=" * 100)
print("D. engine-side hardcoded material tokens (from exe string pool)")
print("=" * 100)
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()
toks = sorted(set(re.findall(rb"<MATERIAL=([A-Za-z0-9_-]+)", exe)))
for t in toks:
    n = t.decode()
    print("   %-28s %s" % (n, resolve(n)))

print()
print("=" * 100)
print("E. engine input check")
print("=" * 100)
for name in (b"icons.json", b"CustomMapIcons.json", b"materials\x00",
             b"morematerials\x00", b"buttons.json"):
    print("   %-24s %d" % (name.decode().replace("\x00", " (bare)"), exe.count(name)))
