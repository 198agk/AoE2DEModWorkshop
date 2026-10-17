"""End-to-end test: read real AoE2DE scenario files with AoE2ScenarioParser.

Round-trips each file (parse -> save -> re-parse) and reports section counts.
"""
import os
import sys
import traceback

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roundtrip")
os.makedirs(OUT, exist_ok=True)

FILES = [
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario",
    r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2\real_world_amazon.scx",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2\special_map_journeysouth.scx",
    r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2\real_world_world.scx",
]

for path in FILES:
    print("=" * 90)
    print("FILE:", path)
    if not os.path.exists(path):
        print("  MISSING")
        continue
    try:
        scenario = AoE2DEScenario.from_file(path)
    except Exception as e:
        print(f"  READ FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
        continue
    try:
        print(f"  version         : {scenario.version}")
        mgr = scenario.trigger_manager
        print(f"  triggers        : {len(mgr.triggers)}")
        conds = sum(len(t.conditions) for t in mgr.triggers)
        effs = sum(len(t.effects) for t in mgr.triggers)
        print(f"  conditions      : {conds}")
        print(f"  effects         : {effs}")
        try:
            print(f"  variables       : {len(mgr.variables)}")
        except Exception:
            pass
        try:
            ud = scenario.unit_manager
            allu = ud.get_all_units()
            print(f"  units           : {len(allu)}")
        except Exception as e:
            print(f"  units: n/a ({type(e).__name__})")
        try:
            md = scenario.map_manager
            print(f"  map size        : {md.map_size.width}x{md.map_size.height} "
                  f"({len(md.terrain_data)} terrain tiles)")
        except Exception as e:
            print(f"  map: n/a ({type(e).__name__}: {e})")
        try:
            pm = scenario.player_manager
            print(f"  active players  : {len(pm.active_players)}/{len(pm.players)}")
        except Exception as e:
            print(f"  players: n/a ({type(e).__name__})")
        # show a few trigger names + first condition/effect type
        for t in mgr.triggers[:6]:
            cn = [type(c).__name__ for c in t.conditions][:3]
            en = [type(e).__name__ for e in t.effects][:3]
            print(f"    trigger id={t.trigger_id} name={t.name!r} desc={t.description!r} conds={cn} effs={en}")
        # round trip
        out = os.path.join(OUT, os.path.splitext(os.path.basename(path))[0] + ".aoe2scenario")
        scenario.write_to_file(out)
        sz_in, sz_out = os.path.getsize(path), os.path.getsize(out)
        reread = AoE2DEScenario.from_file(out)
        print(f"  WRITE ok        : {sz_in} -> {sz_out} bytes "
              f"({sz_out/sz_in:.3f}x); re-read triggers={len(reread.trigger_manager.triggers)}")
    except Exception as e:
        print(f"  POST-READ FAILED: {type(e).__name__}: {e}")
        traceback.print_exc()
