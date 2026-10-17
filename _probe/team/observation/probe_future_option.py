"""Resolve IDS_OPT_DISPLAY_FUTURE_ITEMS / _HELP_TEXT and IDS_OPT_TECH_TREE_PREVIEW / _HELP.

Question: the game ships TWO separate Interface checkboxes (screenoptions.json
lines 1565 EnableFutureItemsDisplay, 1601 TechTreePreview).  Read their exact
player-facing text so we can tell WHICH subsystem 'future items' is.
"""
import json
import os
import re

ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
SR = os.path.join(ROOT, "widgetui", "stringreference.json")

ref = json.load(open(SR, encoding="utf-8-sig"))
ref = ref.get("StringReferences", ref) if isinstance(ref, dict) else ref
print("stringreference.json entries:", len(ref))

WANT = {
    "IDS_OPT_DISPLAY_FUTURE_ITEMS": 8898,
    "IDS_OPT_DISPLAY_FUTURE_ITEMS_HELP_TEXT": None,
    "IDS_OPT_TECH_TREE_PREVIEW": None,
    "IDS_OPT_TECH_TREE_PREVIEW_HELP": None,
}
if isinstance(ref, dict):
    for k in list(WANT):
        if k in ref:
            WANT[k] = ref[k]
print("resolved ids:", json.dumps(WANT, ensure_ascii=False, indent=4))

# also dump every id whose KEY mentions FUTURE / PREVIEW
print("\n--- every StringReference key matching FUTURE|PREVIEW|GREY ---")
for k, v in (ref.items() if isinstance(ref, dict) else []):
    if re.search(r"FUTURE|PREVIEW|GREY|GRAYED", k, re.I):
        print("   %-60s %s" % (k, v))


def load_locale(name):
    p = os.path.join(ROOT, "resources", name, "strings", "key-value",
                     "key-value-strings-utf8.txt")
    d = {}
    with open(p, encoding="utf-8-sig") as fh:
        for line in fh:
            m = re.match(r'^(\d+)\s+"(.*)"\s*$', line.rstrip("\n"))
            if m:
                d[int(m.group(1))] = m.group(2)
    return d


en = load_locale("en")
zh = load_locale("zh")
print("\nen strings=%d  zh strings=%d" % (len(en), len(zh)))

print("\n=== the option texts, EN + ZH ===")
for k, sid in WANT.items():
    if sid is None:
        print("   %-42s (id not found in stringreference.json)" % k)
        continue
    print("   %-42s id=%-8s" % (k, sid))
    print("        EN: %s" % (en.get(sid, "<missing>").replace("\n", " | "),))
    print("        ZH: %s" % (zh.get(sid, "<missing>").replace("\n", " | "),))
