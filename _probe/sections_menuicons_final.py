"""Final decisive check for the 9 MenuIcons values.

Exhausted so far (all negative):
  - verbatim in materials.json Name/TextureRef
  - verbatim in any tree text file (ICONS.JSON self-match only)
  - verbatim in the exe (exact case)
  - official filename->RefName normalization (5 candidate forms)
  - any on-disk PNG whose name contains 'submenu'/'open_arrow'/'return_arrow'
  - any material name containing the value's tokens

Remaining honest options:
  1. case-insensitive presence in the exe
  2. UTF-16LE presence in the exe (some engines store wide strings)
  3. case-insensitive presence anywhere in the tree
  4. they might be dead entries
Read-only.
"""
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")

sys.stdout.reconfigure(encoding="utf-8")

VAL = ["submenu_button_base", "submenu_open_arrow_overlay",
       "submenu_return_arrow_overlay", "submenu_open", "submenu_return",
       "submenu_oligarchy", "submenu_democracy", "submenu_tyranny",
       "mutually_exclusive_tech_unavailable"]

print("loading exe ...")
exe = open(EXE, "rb").read()
low = exe.lower()
print("  %d B" % len(exe))

print()
print("=" * 92)
print("1. exe, case-insensitive ASCII")
print("=" * 92)
for v in VAL:
    n = low.count(v.encode("ascii"))
    print("   %-36s %d" % (v, n))

print()
print("=" * 92)
print("2. exe, UTF-16LE")
print("=" * 92)
for v in VAL:
    n = exe.count(v.encode("utf-16-le"))
    print("   %-36s %d" % (v, n))

# are the *sub-parts* in the exe at all?
print()
print("=" * 92)
print("3. exe, sub-tokens (to see if the engine knows the concept)")
print("=" * 92)
for tok in ("submenu", "mutually_exclusive", "tech_unavailable", "oligarchy",
            "democracy", "tyranny", "open_arrow", "return_arrow", "button_base",
            "MenuIcons", "menu_icon"):
    n = low.count(tok.encode("ascii"))
    print("   %-24s %d" % (tok, n))

print()
print("=" * 92)
print("4. whole tree, case-insensitive, non-binary")
print("=" * 92)
SKIP = ("drs", "campaign", "movies")
found = {}
checked = 0
for root, dirs, files in os.walk(GAME):
    dirs[:] = [d for d in dirs if not any(s in d.lower() for s in SKIP)]
    for fn in files:
        if fn.lower().endswith((".exe", ".dll", ".pdb")):
            continue
        p = os.path.join(root, fn)
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
            blob = open(p, "rb").read().lower()
        except Exception:
            continue
        checked += 1
        rel = os.path.relpath(p, GAME)
        for v in VAL:
            if v.encode("ascii") in blob:
                found.setdefault(v, []).append(rel)
print("   files checked: %d" % checked)
for v in VAL:
    hits = [h for h in found.get(v, []) if "icons.json" not in h]
    print("   %-36s %s" % (v, hits if hits else "<only icons.json / nowhere>"))

print()
print("=" * 92)
print("5. wpfg tree, any file with 'submenu' in its path")
print("=" * 92)
n = 0
for root, dirs, files in os.walk(GAME):
    for fn in files:
        rp = os.path.join(root, fn)
        if "submenu" in rp.lower():
            print("   ", os.path.relpath(rp, GAME))
            n += 1
print("   total: %d" % n)
