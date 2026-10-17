"""Where do Notification / MenuIcons / StatIcons values actually resolve?

sections_last3.py reported "layout_ref(1)" for each, but sections_last3_roles.py
showed the only hit was icons.json itself -- a self-match artifact, because
icons.json lives inside widgetui/.  So these sections do NOT resolve to a
widgetui layout.

This script checks the remaining honest options:
  A. exact membership in materials.json (Name / TextureRef)
  B. presence anywhere else in the game tree, as text
  C. presence in the exe string pool (engine-side runtime mapping)
Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")
EXE = os.path.join(GAME, "AoE2DE_s.exe")

sys.stdout.reconfigure(encoding="utf-8")

VALUES = {
    "Notification": ["wonder_icon", "relic_icon"],
    "MenuIcons": ["submenu_button_base", "submenu_open_arrow_overlay",
                  "submenu_return_arrow_overlay", "submenu_open", "submenu_return",
                  "submenu_oligarchy", "submenu_democracy", "submenu_tyranny",
                  "mutually_exclusive_tech_unavailable"],
    "StatIcons": ["stat_icon_powerup", "stat_icon_armor", "stat_icon_convert",
                  "stat_icon_damage", "stat_icon_food", "stat_icon_garrison",
                  "stat_icon_gold", "stat_icon_hp", "stat_icon_hpregen",
                  "stat_icon_movement_speed", "stat_icon_pierce_attack",
                  "stat_icon_hploss", "stat_icon_range", "stat_icon_range_armor",
                  "stat_icon_reload_time", "stat_icon_stone", "stat_icon_transport",
                  "stat_icon_wood", "stat_icon_workrate",
                  "StatIconsPowerUpArmor", "StatIconsPowerUpRange",
                  "StatIconsPowerUpRegeneration", "StatIconsPowerUpReloadTime",
                  "StatIconsPowerUpMovementSpeed"],
}

# ---- A. materials.json ------------------------------------------------------
mat = json.load(open(os.path.join(WIDGETUI, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
mnames, trefs = set(), set()
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    if md.get("Name"):
        mnames.add(md["Name"])
    if md.get("TextureRef"):
        trefs.add(md["TextureRef"])

# ---- C. exe ----------------------------------------------------------------
print("loading exe ...")
exe = open(EXE, "rb").read()
print("  %d B" % len(exe))

# ---- B. tree (text-ish files only, skip the exe and giant binaries) --------
print("indexing tree text ...")
tree_hits = {}
checked = 0
SKIPDIR = ("drs", "campaign", "movies", "sound.")
for root, dirs, files in os.walk(GAME):
    dirs[:] = [d for d in dirs if not any(s in d.lower() for s in SKIPDIR)]
    for fn in files:
        low = fn.lower()
        if low.endswith((".exe", ".dll", ".pdb")):
            continue
        p = os.path.join(root, fn)
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            with open(p, "rb") as f:
                blob = f.read()
        except Exception:
            continue
        checked += 1
        for sec, vals in VALUES.items():
            for v in vals:
                if v.encode("ascii") in blob:
                    rel = os.path.relpath(p, GAME)
                    tree_hits.setdefault(v, []).append(rel)
print("  text files checked: %d" % checked)

print()
print("=" * 100)
for sec, vals in VALUES.items():
    print("%s" % sec)
    print("-" * 100)
    for v in vals:
        inname = v in mnames
        intref = v in trefs
        exe_n = exe.count(v.encode("ascii"))
        others = [r for r in tree_hits.get(v, [])
                  if not r.lower().endswith("icons.json")]
        tag = []
        if inname:
            tag.append("materials.Name")
        if intref:
            tag.append("materials.TextureRef")
        if exe_n:
            tag.append("exe x%d" % exe_n)
        if others:
            tag.append("tree: " + ",".join(others[:2]))
        print("  %-34s %s" % (v, "; ".join(tag) if tag else "<NOWHERE>"))
    print()
