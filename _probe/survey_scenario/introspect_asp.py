"""Introspect ASP manager APIs so the final report uses correct attribute names."""
import warnings
warnings.filterwarnings("ignore")
import AoE2ScenarioParser
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

siege = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario"
sc = AoE2DEScenario.from_file(siege)

def pub(o):
    return [a for a in dir(o) if not a.startswith("_")]

print("UNIT MANAGER:", pub(sc.unit_manager))
u = sc.unit_manager.get_all_units()[0]
print("UNIT attrs:", pub(u))
print("sample unit repr:", u)

print()
print("MAP MANAGER:", pub(sc.map_manager))
mm = sc.map_manager
print("map_size =", mm.map_size, type(mm.map_size))
try:
    print("terrain_data type:", type(mm.terrain_data), "len:", len(mm.terrain_data))
except Exception as e:
    print("terrain_data err:", e)
for a in pub(mm):
    try:
        v = getattr(mm, a)
        if not callable(v):
            print(f"   mm.{a} = {str(v)[:90]}")
    except Exception as e:
        print(f"   mm.{a} -> {type(e).__name__}")

print()
print("PLAYER MANAGER:", pub(sc.player_manager))
pm = sc.player_manager
print("players len:", len(pm.players))
p = pm.players[1]
print("PLAYER attrs:", pub(p))
for a in pub(p):
    try:
        v = getattr(p, a)
        if not callable(v):
            print(f"   p1.{a} = {str(v)[:110]}")
    except Exception as e:
        pass

print()
print("MESSAGE MANAGER:", pub(sc.message_manager))
msgm = sc.message_manager
print("messages:", len(msgm.messages))
if msgm.messages:
    m = msgm.messages[0]
    print("MESSAGE attrs:", pub(m))
    print("first message:", repr(m.message)[:200], "id:", getattr(m, "message_id", None))

print()
print("TRIGGER MANAGER:", pub(sc.trigger_manager))
print("OPTION MANAGER:", pub(sc.option_manager))
print("XS MANAGER:", pub(sc.xs_manager))

print()
print("--- saving roundtrip on a COPY (never writes to game dir) ---")
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roundtrip", "The Siege.out.aoe2scenario")
os.makedirs(os.path.dirname(out), exist_ok=True)
sc.write_to_file(out)
sz_in = os.path.getsize(siege)
sz_out = os.path.getsize(out)
print(f"size in={sz_in} out={sz_out} ratio={sz_out/sz_in:.4f}")
r = AoE2DEScenario.from_file(out)
print("reread triggers:", len(r.trigger_manager.triggers),
      "units:", len(r.unit_manager.get_all_units()),
      "messages:", len(r.message_manager.messages),
      "variables:", len(r.trigger_manager.variables))
print("first bytes in :", open(siege,'rb').read(8))
print("first bytes out:", open(out,'rb').read(8))
