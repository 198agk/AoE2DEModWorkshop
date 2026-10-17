"""Robust introspection of ASP managers (no __repr__ on version-gated objects)."""
import os
import warnings
warnings.filterwarnings("ignore")

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

siege = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario"
sc = AoE2DEScenario.from_file(siege)

def safe(label, fn):
    try:
        v = fn()
        print(f"  {label} = {str(v)[:140]}")
    except Exception as e:
        print(f"  {label} -> {type(e).__name__}: {str(e)[:110]}")

print("variant:", sc.variant, "| game_version:", sc.game_version,
      "| scenario_version:", sc.scenario_version, "| name:", sc.name)

print("\n--- UNITS ---")
um = sc.unit_manager
allu = um.get_all_units()
print("count:", len(allu))
u = allu[0]
safe("u.unit_const", lambda: u.unit_const)
safe("u.tile", lambda: u.tile)
safe("u.player", lambda: u.player)
safe("u.x/u.y", lambda: (u.x, u.y))
safe("u.reference_id", lambda: u.reference_id)
safe("u.name", lambda: u.name)
safe("u.rotation", lambda: u.rotation)
from collections import Counter
print("units per player:", dict(Counter(x.player.value if hasattr(x.player,'value') else x.player for x in allu)))
print("distinct unit_const values:", len(set(x.unit_const for x in allu)))
print("top 12 unit_const:", Counter(x.unit_const for x in allu).most_common(12))

print("\n--- MAP ---")
mm = sc.map_manager
safe("mm.map_size", lambda: mm.map_size)
safe("type(map_size)", lambda: type(mm.map_size).__name__)
try:
    ms = mm.map_size
    print("  map_size dir:", [a for a in dir(ms) if not a.startswith('_')])
    for a in [a for a in dir(ms) if not a.startswith('_')]:
        safe(f"map_size.{a}", (lambda a=a: getattr(ms, a)))
except Exception as e:
    print("  ", e)
safe("len(mm.terrain_data)", lambda: len(mm.terrain_data))
safe("mm.terrain_data[0]", lambda: mm.terrain_data[0])
try:
    td = mm.terrain_data
    print("  terrain_data type:", type(td).__name__, "len:", len(td))
    flat = list(td) if not isinstance(td, list) else td
    print("  first 10 terrain tiles:", flat[:10])
    print("  distinct terrain ids (first 5000):", sorted(set(flat[:5000]))[:20])
except Exception as e:
    print("  terrain err:", type(e).__name__, e)
for a in [a for a in dir(mm) if not a.startswith('_')]:
    if a in ('get_scenario','construct','commit','terrain_data'): continue
    safe(f"mm.{a}", (lambda a=a: getattr(mm, a)))

print("\n--- PLAYERS ---")
pm = sc.player_manager
print("players len:", len(pm.players), "| active:", [getattr(p,'player_id',None) for p in pm.active_players])
p = pm.players[1]
attrs = [a for a in dir(p) if not a.startswith('_')]
print("player attrs:", attrs)
for a in attrs:
    if a in ('get_scenario','construct','commit'): continue
    try:
        v = getattr(p, a)
        if not callable(v):
            print(f"  p1.{a} = {str(v)[:110]}")
    except Exception as e:
        print(f"  p1.{a} -> {type(e).__name__}")

print("\n--- MESSAGES ---")
msgm = sc.message_manager
print("count:", len(msgm.messages))
for m in msgm.messages[:4]:
    print("  attrs:", [a for a in dir(m) if not a.startswith('_')])
    print("  id:", getattr(m,'message_id',None), "text:", repr(getattr(m,'message',''))[:160])

print("\n--- TRIGGERS sample detail ---")
tm = sc.trigger_manager
for t in tm.triggers:
    if t.effects and t.conditions:
        print(f"  trigger {t.trigger_id} {t.name!r}")
        c = t.conditions[0]
        e = t.effects[0]
        print("   cond attrs:", [a for a in dir(c) if not a.startswith('_')][:40])
        print("   eff  attrs:", [a for a in dir(e) if not a.startswith('_')][:40])
        for a in ('condition_type','objects_in_area','area_x1','object_list','source_player','quantity','variable','comparison'):
            safe(f"cond.{a}", (lambda a=a: getattr(c, a)))
        for a in ('effect_type','message','display_time','source_player','object_list_unit_id','quantity','location_x','location_y','operation','object_attributes'):
            safe(f"eff.{a}", (lambda a=a: getattr(e, a)))
        break

print("\n--- ROUNDTRIP (writes to scratch only) ---")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roundtrip", "The Siege.out.aoe2scenario")
os.makedirs(os.path.dirname(out), exist_ok=True)
sc.write_to_file(out)
sz_in, sz_out = os.path.getsize(siege), os.path.getsize(out)
print(f"size in={sz_in} out={sz_out} ratio={sz_out/sz_in:.4f}")
r = AoE2DEScenario.from_file(out)
print("reread: triggers=", len(r.trigger_manager.triggers),
      " units=", len(r.unit_manager.get_all_units()),
      " messages=", len(r.message_manager.messages),
      " variables=", len(r.trigger_manager.variables))
print("header in :", open(siege,'rb').read(8))
print("header out:", open(out,'rb').read(8))
