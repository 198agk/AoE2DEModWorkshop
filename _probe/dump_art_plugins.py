# -*- coding: utf-8 -*-
"""Show the pixel-art / image-asset plugins the negative-search surfaced.

These appeared under "sprite"/"aseprite"/"游戏资源" rather than under any AoE
term, so they are only visible if the search is read rather than just counted.
"""
import json, io

CAT = r"D:\Software\DeepSeek Harness\工作区2\_probe\awesome_plugins.json"
data = json.load(io.open(CAT, encoding="utf-8"))
plugins = data["plugins"] if isinstance(data, dict) and "plugins" in data else data
by = {(p.get("npm") or p.get("name")): p for p in plugins}

WANT = [
    "dsh-aseprite",
    "dsh-game-material-master",
    "pbr-render",
    "dsh-cad-viewer",
    "godot-bridge",
    "@tindalosko/dsh-cheatengine",
    "dsh-pet-sprite",
    "dsh-diorama",
    "@wyh-hub/dsh-godot-mcp",
    "dsh-unity-mcp",
    "dsh-image-gen",
    "dsh-draw",
]

for name in WANT:
    p = by.get(name)
    if p is None:
        continue
    d = p.get("description") or {}
    print("=" * 78)
    print("%s   [%s]  stars %s  dl %s  v%s"
          % (name, p.get("category"), p.get("stars"), p.get("downloads"), p.get("version")))
    print("  url      %s" % p.get("url"))
    print("  install  %s" % p.get("install"))
    print("  caps     %s" % (", ".join(p.get("capabilities") or []) or "(none)"))
    rl = p.get("capabilityRedLines") or []
    print("  redlines %s" % (json.dumps(rl, ensure_ascii=False) if rl else "(none)"))
    print("  zh: %s" % d.get("zh"))
