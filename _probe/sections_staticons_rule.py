"""Verify the StatIcons prefix rule.

sections_last3_norm.py revealed the target family in materials.json:
    StatIconsArmor, StatIconsConvert, StatIconsHp, StatIconsRange-Armor, ...

Hypothesis:  stat_icon_<X>  ->  "StatIcons" + TitleCase(squash(<X>))
with documented exceptions to be measured, not assumed.

Verify it exhaustively against materials.json (Name OR TextureRef) and report
the exact exception list.  Read-only.
"""
import json
import os
import sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WIDGETUI = os.path.join(GAME, "widgetui")

sys.stdout.reconfigure(encoding="utf-8")

mat = json.load(open(os.path.join(WIDGETUI, "materials.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
names = {}
for wrap in mat.get("Materials", []):
    md = wrap.get("MaterialDef") or {}
    for key in ("Name", "TextureRef"):
        v = md.get(key)
        if v:
            names.setdefault(v, set()).add(key)
# normalized lookup: lowercase, punctuation removed
norm = {}
for v in names:
    k = "".join(c for c in v.lower() if c.isalnum())
    norm.setdefault(k, []).append(v)

doc = json.load(open(os.path.join(WIDGETUI, "icons.json"),
                     "r", encoding="utf-8-sig", errors="replace"))
sec = doc.get("StatIcons") or {}


def titlecase(s):
    parts = s.replace("-", "_").split("_")
    return "".join(p[:1].upper() + p[1:].lower() for p in parts if p)


print("=" * 100)
print("StatIcons: stat_icon_<X> -> StatIcons+TitleCase(<X>)")
print("=" * 100)
print("  %-8s %-30s %-30s %s" % ("hit", "icons.json value", "candidate", "materials"))
print("-" * 100)

exact = 0
normed = 0
missing = []
for k in sorted(sec.keys()):
    v = sec[k]
    if not isinstance(v, str) or not v:
        continue
    tail = v
    for pref in ("stat_icon_", "StatIcons", "stat_icon"):
        if tail.lower().startswith(pref.lower()):
            tail = tail[len(pref):]
            break
    cand = "StatIcons" + titlecase(tail)
    status = ""
    if cand in names:
        status = "EXACT Name/TextureRef"
        exact += 1
    elif cand.lower().replace("-", "") in norm:
        alts = norm[cand.lower().replace("-", "")]
        status = "norm-match %s" % alts
        normed += 1
    else:
        # try the raw value itself
        if v in names:
            status = "raw value IS a material"
            exact += 1
        else:
            missing.append((v, cand))
            status = "MISS"
    print("  %-8s %-30s %-30s %s" % ("OK" if "MISS" not in status else "??",
                                     v[:30], cand[:30], status))

print()
print("exact=%d norm=%d miss=%d  (total %d)" % (exact, normed, len(missing), exact + normed + len(missing)))
if missing:
    print()
    print("UNRESOLVED:")
    for v, c in missing:
        print("   %-30s tried %r" % (v, c))

# ---- same test for Notification / MenuIcons, honestly ----------------------
print()
print("=" * 100)
print("Notification / MenuIcons -- candidate searches")
print("=" * 100)
for sname, prefixes in (("Notification", ["", "Notification", "notify_", "notify"]),
                        ("MenuIcons", ["", "MenuIcons", "menu_icon_", "menu_"])):
    s = doc.get(sname) or {}
    for k in sorted(s.keys()):
        v = s[k]
        if not isinstance(v, str):
            continue
        tried = []
        for pref in prefixes:
            tail = v
            if pref and tail.lower().startswith(pref.lower()):
                tail = tail[len(pref):]
            for base in ("", "MenuIcons", "Notification", "Menu", "Icons"):
                cand = base + titlecase(tail) if base or pref else titlecase(tail)
                if cand and cand in names:
                    tried.append("%r -> %s" % (cand, sorted(names[cand])))
        print("  %-36s %s" % (v, "; ".join(tried) if tried else "<no candidate in materials.json>"))
