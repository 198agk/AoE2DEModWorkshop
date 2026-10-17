"""Deep probe of AoE2ScenarioParser using its locally-installed version data.

Part A: list which game-version structure folders ship with the installed release.
Part B: summarise the v1.54 structure.json (sections + field counts).
Part C: read 'The Siege' and print rich real numbers (triggers, units, map, messages).
Part D: create a NEW scenario from the bundled default template, add a trigger with a
        condition + effect + message, save, and re-read it.
"""
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import AoE2ScenarioParser
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

ROOT = os.path.dirname(os.path.abspath(AoE2ScenarioParser.__file__))
SCRATCH = os.path.dirname(os.path.abspath(__file__))

print("=" * 90)
print("PART A: versions shipped with the installed AoE2ScenarioParser")
print("=" * 90)
print("package:", ROOT)
for game in sorted(os.listdir(os.path.join(ROOT, "versions"))):
    if game.startswith("__"):
        continue
    print(f"  game folder: {game}")
    for ver in sorted(os.listdir(os.path.join(ROOT, "versions", game))):
        p = os.path.join(ROOT, "versions", game, ver)
        if os.path.isdir(p):
            files = sorted(os.listdir(p))
            sizes = {f: os.path.getsize(os.path.join(p, f)) for f in files}
            print(f"    {ver}: {files}  sizes={sizes}")

print()
print("=" * 90)
print("PART B: v1.54 structure.json summary")
print("=" * 90)
sp = os.path.join(ROOT, "versions", "DE", "v1.54", "structure.json")
if os.path.exists(sp):
    with open(sp, "r", encoding="utf-8") as f:
        struct = json.load(f)
    print("top-level type:", type(struct).__name__)
    print("keys/order:", list(struct.keys()) if isinstance(struct, dict) else f"len={len(struct)}")
    if isinstance(struct, dict):
        for k, v in struct.items():
            n = len(v) if hasattr(v, "__len__") else "?"
            print(f"  section {k!r}: {type(v).__name__} len={n}")
            if isinstance(v, dict):
                for k2, v2 in list(v.items())[:12]:
                    print(f"      {k2}: {type(v2).__name__} len={len(v2) if hasattr(v2,'__len__') else '?'}")
    with open(os.path.join(SCRATCH, "structure_v1.54_excerpt.txt"), "w", encoding="utf-8") as f:
        f.write(json.dumps(struct, indent=1)[:20000])

for nm in ("conditions.json", "effects.json"):
    p = os.path.join(ROOT, "versions", "DE", "v1.54", nm)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        print(f"\n{nm}: type={type(d).__name__} count={len(d)}")
        if isinstance(d, dict):
            print("  names:", list(d.keys()))
            k0 = list(d.keys())[0]
            print(f"  sample entry {k0!r}:")
            print(json.dumps(d[k0], indent=1)[:1200])

print()
print("=" * 90)
print("PART C: real numbers from 'The Siege' (v1.53)")
print("=" * 90)
siege = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario"
sc = AoE2DEScenario.from_file(siege)
print("scenario_version:", sc.scenario_version)
print("public attrs:", [a for a in dir(sc) if not a.startswith("_")])

tm = sc.trigger_manager
print(f"triggers   : {len(tm.triggers)}")
print(f"conditions : {sum(len(t.conditions) for t in tm.triggers)}")
print(f"effects    : {sum(len(t.effects) for t in tm.triggers)}")
try:
    print(f"variables  : {len(tm.variables)}")
except Exception as e:
    print("variables: n/a", e)
try:
    print(f"trigger display order: {tm.trigger_display_order}")
except Exception as e:
    print("display order n/a:", e)

for t in tm.triggers[:8]:
    conds = [type(c).__name__ for c in t.conditions][:4]
    effs = [type(e).__name__ for e in t.effects][:4]
    print(f"  trigger {t.trigger_id} name={t.name!r} desc={t.description!r} "
          f"enabled={t.enabled} looping={t.looping} conds={conds} effs={effs}")

um = sc.unit_manager
try:
    allu = um.get_all_units()
    print(f"units total: {len(allu)}")
    from collections import Counter
    print("  by player:", dict(Counter(u.player for u in allu)))
    print("  sample:", [(u.player, u.unit_id, u.x, u.y) for u in allu[:5]])
except Exception as e:
    print("units n/a:", type(e).__name__, e)

mm = sc.map_manager
print(f"map size: {mm.map_size.width}x{mm.map_size.height}")
try:
    print(f"terrain tiles: {len(mm.terrain_data)}")
except Exception as e:
    print("terrain n/a:", e)

pm = sc.player_manager
print("players:", len(pm.players), "active:", [p.player_id for p in pm.active_players])
for p in pm.players[:3]:
    print(f"  p{p.player_id}: name={p.name!r} civ={p.civilization} color={p.color} "
          f"pop={p.population_limit} res={getattr(p, 'resources', None)}")

try:
    msgm = sc.message_manager
    print("messages:", len(msgm.messages))
    for m in msgm.messages[:5]:
        print(f"  msg {m.message_id} {m.message!r}")
except Exception as e:
    print("messages n/a:", type(e).__name__, e)

print()
print("=" * 90)
print("PART D: create a NEW scenario from scratch")
print("=" * 90)
default = os.path.join(ROOT, "versions", "DE", "v1.54", "default.aoe2scenario")
print("template:", default, os.path.getsize(default), "bytes")
try:
    new = AoE2DEScenario.from_file(default)
    print("loaded template OK; version:", new.scenario_version)
    tr = new.trigger_manager.add_trigger("Hello from a generated scenario", enabled=True, looping=False)
    tr.new_condition.objects_in_area(1, 1, 1, 2, 2, 1)
    tr.new_effect.display_instructions(1, -1, "Welcome to your generated scenario!")
    out = os.path.join(SCRATCH, "generated_from_scratch.aoe2scenario")
    new.write_to_file(out)
    print(f"WROTE {out} ({os.path.getsize(out)} bytes)")
    back = AoE2DEScenario.from_file(out)
    bt = back.trigger_manager.triggers
    print("re-read triggers:", len(bt), [t.name for t in bt])
    print("re-read cond/eff:", [type(c).__name__ for c in bt[0].conditions],
          [type(e).__name__ for e in bt[0].effects])
except Exception as e:
    import traceback
    print("CREATE FAILED:", type(e).__name__, e)
    traceback.print_exc()
