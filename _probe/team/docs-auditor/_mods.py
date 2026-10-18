# -*- coding: utf-8 -*-
import sys, os, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.getcwd())
from aoe2mod.game import locations as L
g = L.find_game_root()
pr = L.find_profile_root()
mods = L.list_mods(pr)
out = {
  "game_root": g,
  "profile_root": pr,
  "mods": [{"folder": os.path.basename(m.get("folder","")), "name": m.get("name"), "title": m.get("title"), "enabled": m.get("enabled"), "kind": m.get("kind")} for m in mods],
}
open("_probe/team/docs-auditor/mods.json","w",encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(len(mods), "mods")
for m in mods:
    print(("ON " if m.get("enabled") else "off"), m.get("kind"), "|", m.get("title"))
