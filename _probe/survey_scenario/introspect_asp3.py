"""Round 3: players, messages, triggers detail, terrain array, and a scratch-only roundtrip."""
import os
import warnings
warnings.filterwarnings("ignore")

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

HERE = os.path.dirname(os.path.abspath(__file__))
siege = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario"


def safe(label, fn, n=130):
    try:
        v = fn()
        print(f"  {label} = {str(v)[:n]}")
        return v
    except Exception as e:
        print(f"  {label} -> {type(e).__name__}: {str(e)[:100]}")
        return None


sc = AoE2DEScenario.from_file(siege)

print("=== TERRAIN ===")
mm = sc.map_manager
safe("map_size", lambda: mm.map_size)
safe("map_width/height", lambda: (mm.map_width, mm.map_height))
t = safe("len(mm.terrain)", lambda: len(mm.terrain))
print("  terrain tile attrs:", [a for a in dir(mm.terrain[0]) if not a.startswith('_')])
safe("terrain[0].terrain_id", lambda: mm.terrain[0].terrain_id)
safe("terrain[0].elevation", lambda: mm.terrain[0].elevation)
from collections import Counter
tc = Counter(x.terrain_id for x in mm.terrain)
print("  distinct terrain_ids:", len(tc))
print("  top 10 terrain_ids:", tc.most_common(10))
ec = Counter(x.elevation for x in mm.terrain)
print("  elevation levels:", sorted(ec.items())[:12])

print("\n=== PLAYERS ===")
pm = sc.player_manager
print("  PlayerManager attrs:", [a for a in dir(pm) if not a.startswith('_')])
safe("len(pm.players)", lambda: len(pm.players))
safe("pm.active_players", lambda: pm.active_players)
safe("pm.human_players", lambda: pm.human_players)
for i in (1, 2):
    p = pm.players[i]
    print(f"  --- player {i} ---")
    for a in [a for a in dir(p) if not a.startswith('_')]:
        if a in ('get_scenario', 'construct', 'commit', 'instance_number_history', 'uuid'):
            continue
        try:
            v = getattr(p, a)
            if callable(v):
                continue
            print(f"    p.{a} = {str(v)[:120]}")
        except Exception as e:
            print(f"    p.{a} -> {type(e).__name__}")

print("\n=== MESSAGES ===")
msgm = sc.message_manager
print("  count:", len(msgm.messages))
for m in msgm.messages[:3]:
    print("   attrs:", [a for a in dir(m) if not a.startswith('_')])
    print("   ", {a: (str(getattr(m, a))[:90]) for a in ('message_id', 'message', 'sound_id') if hasattr(m, a)})

print("\n=== TRIGGER/CONDITION/EFFECT DETAIL ===")
tm = sc.trigger_manager
print("  triggers:", len(tm.triggers), " vars:", len(tm.variables))
print("  TriggerManager attrs:", [a for a in dir(tm) if not a.startswith('_')])
if tm.variables:
    v0 = tm.variables[0]
    print("  variable attrs:", [a for a in dir(v0) if not a.startswith('_')])
    print("  var0:", {a: str(getattr(v0, a))[:40] for a in dir(v0) if not a.startswith('_') and not callable(getattr(v0, a, None))})
# find trigger with both conds and effects
for t in tm.triggers:
    if t.effects:
        print(f"  trigger id={t.trigger_id} name={t.name!r} conds={len(t.conditions)} effs={len(t.effects)}")
        if t.conditions:
            c = t.conditions[0]
            print("   cond class:", type(c).__mro__[1].__name__)
            ca = [a for a in dir(c) if not a.startswith('_')]
            print("   cond attrs:", ca)
        e = t.effects[0]
        print("   eff class:", type(e).__mro__[1].__name__)
        print("   eff attrs:", [a for a in dir(e) if not a.startswith('_')])
        print("   ---- full condition ----")
        for a in [a for a in dir(t.conditions[0]) if not a.startswith('_')]:
            try:
                v = getattr(t.conditions[0], a)
                if not callable(v):
                    print(f"     c.{a} = {str(v)[:100]}")
            except Exception as ex:
                print(f"     c.{a} -> {type(ex).__name__}")
        print("   ---- full effect ----")
        for a in [a for a in dir(e) if not a.startswith('_')]:
            try:
                v = getattr(e, a)
                if not callable(v):
                    print(f"     e.{a} = {str(v)[:100]}")
            except Exception as ex:
                print(f"     e.{a} -> {type(ex).__name__}")
        break

print("\n=== ROUNDTRIP (scratch only) ===")
out = os.path.join(HERE, "roundtrip", "The Siege.out.aoe2scenario")
os.makedirs(os.path.dirname(out), exist_ok=True)
sc.write_to_file(out)
sz_in, sz_out = os.path.getsize(siege), os.path.getsize(out)
print(f"  size in={sz_in} out={sz_out} ratio={sz_out/sz_in:.5f} delta={sz_out-sz_in}")
r = AoE2DEScenario.from_file(out)
print("  reread triggers:", len(r.trigger_manager.triggers),
      " units:", len(r.unit_manager.get_all_units()),
      " messages:", len(r.message_manager.messages),
      " variables:", len(r.trigger_manager.variables))
print("  header in :", open(siege, 'rb').read(8))
print("  header out:", open(out, 'rb').read(8))
b_in = open(siege, 'rb').read()
b_out = open(out, 'rb').read()
common = 0
for a, b in zip(b_in, b_out):
    if a == b:
        common += 1
    else:
        break
print(f"  common prefix bytes: {common} / {min(len(b_in), len(b_out))}")

print("\n=== CREATE FROM SCRATCH ===")
try:
    fresh = AoE2DEScenario.from_default(scenario_version="1.54")
    print("  from_default OK; version:", fresh.scenario_version)
    nm = fresh.map_manager
    safe("fresh map_size", lambda: nm.map_size)
    safe("fresh units", lambda: len(fresh.unit_manager.get_all_units()))
    safe("fresh triggers", lambda: len(fresh.trigger_manager.triggers))
    fout = os.path.join(HERE, "roundtrip", "fresh_1.54.aoe2scenario")
    fresh.write_to_file(fout)
    print("  fresh file size:", os.path.getsize(fout))
    rf = AoE2DEScenario.from_file(fout)
    print("  fresh reread OK, version:", rf.scenario_version, "map:", rf.map_manager.map_size)
except Exception as e:
    print("  from_default FAILED:", type(e).__name__, e)
