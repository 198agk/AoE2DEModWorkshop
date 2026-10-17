# -*- coding: utf-8 -*-
"""Confirm the negative: is there ANY plugin in the catalog that touches AoE2,
game data formats, or mod tooling?

Stating "none exist" needs evidence, so this searches every catalog field for
the vocabularies such a plugin would have to use.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, io, re

CAT = _HERE_PATH("_probe", "awesome_plugins.json")
data = json.load(io.open(CAT, encoding="utf-8"))
plugins = data["plugins"] if isinstance(data, dict) and "plugins" in data else data

TERMS = ["aoe", "age of empires", "empires", "mod", "modding", "模组",
         "游戏数据", "游戏模组", "rts", "scenario", "战役", "游戏",
         "sprite", "精灵图", "dds", "sld", "dat 文件", "游戏资源"]

hits = {}
for p in plugins:
    blob = json.dumps(p, ensure_ascii=False).lower()
    for t in TERMS:
        if t.lower() in blob:
            hits.setdefault(t, []).append(p.get("npm") or p.get("name"))

print("catalog size: %d" % len(plugins))
for t in TERMS:
    h = hits.get(t, [])
    print("%-14s %4d  %s" % (t, len(h), ", ".join(h[:10])))

# The word "mod"/"游戏" alone is noise; show what the strongest signal actually
# says, so "0 relevant" is a checked claim rather than a filtered one.
print("\n--- entries containing BOTH a game word and a mod word ---")
for p in plugins:
    blob = json.dumps(p, ensure_ascii=False).lower()
    if ("game" in blob or "游戏" in blob) and ("mod" in blob or "模组" in blob):
        print("%-44s %s" % (p.get("npm") or p.get("name"),
                            (p.get("description") or {}).get("zh", "")[:70]))
