"""Round 4: message manager API, trigger cond/effect fields, roundtrip, create-from-scratch."""
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
mm = sc.map_manager
tm = sc.trigger_manager

print("=== MESSAGE MANAGER API ===")
msgm = sc.message_manager
print("  attrs:", [a for a in dir(msgm) if not a.startswith('_')])
for a in [a for a in dir(msgm) if not a.startswith('_')]:
    try:
        v = getattr(msgm, a)
        if not callable(v):
            print(f"  msgm.{a} = {str(v)[:120]}")
    except Exception as e:
        print(f"  msgm.{a} -> {type(e).__name__}")
for meth in ('get_message', 'get_messages', 'add_message', 'remove_message'):
    if hasattr(msgm, meth):
        safe(f"has {meth}", lambda m=meth: True)

print("\n=== MESSAGES CONTENT ===")
try:
    msgs = list(msgm._messages) if hasattr(msgm, '_messages') else []
    print("  _messages len:", len(msgs))
    for m in msgs[:4]:
        print("   attrs:", [a for a in dir(m) if not a.startswith('_')])
        d = {}
        for a in [a for a in dir(m) if not a.startswith('_')]:
            try:
                v = getattr(m, a)
                if not callable(v):
                    d[a] = str(v)[:80]
            except Exception:
                pass
        print("   ", d)
        print("   text:", repr(getattr(m, 'message', ''))[:200])
except Exception as e:
    print("  err:", type(e).__name__, e)
try:
    im = msgm.instructions
    print("  instructions len:", len(im))
    for x in im[:3]:
        print("   instr:", repr(getattr(x, 'message', getattr(x, 'text', x)))[:200])
except Exception as e:
    print("  instructions ->", type(e).__name__, str(e)[:90])
try:
    hi = msgm.hints
    print("  hints len:", len(hi))
except Exception as e:
    print("  hints ->", type(e).__name__, str(e)[:90])
try:
    vt = msgm.victory
    print("  victory:", repr(vt)[:150])
except Exception as e:
    print("  victory ->", type(e).__name__, str(e)[:90])
try:
    lt = msgm.loss
    print("  loss:", repr(lt)[:150])
except Exception as e:
    print("  loss ->", type(e).__name__, str(e)[:90])
try:
    hst = msgm.history
    print("  history:", repr(hst)[:120])
except Exception as e:
    print("  history ->", type(e).__name__, str(e)[:90])
try:
    scn = msgm.scenario_instructions
    print("  scenario_instructions:", repr(scn)[:150])
except Exception as e:
    print("  scenario_instructions ->", type(e).__name__, str(e)[:90])

print("\n=== TRIGGER DETAIL ===")
print("  TriggerManager attrs:", [a for a in dir(tm) if not a.startswith('_')])
for t in tm.triggers:
    if t.effects and t.conditions:
        print(f"  --- trigger id={t.trigger_id} name={t.name!r} desc={t.description!r}")
        print(f"      conds={len(t.conditions)} effs={len(t.effects)} looping={t.looping} enabled={t.enabled}")
        c = t.conditions[0]
        print("      cond real class:", type(c).__name__, "| bases:", [b.__name__ for b in type(c).__mro__[1:4]])
        for a in [a for a in dir(c) if not a.startswith('_')]:
            try:
                v = getattr(c, a)
                if not callable(v):
                    print(f"        c.{a} = {str(v)[:90]}")
            except Exception as ex:
                print(f"        c.{a} -> {type(ex).__name__}: {str(ex)[:60]}")
        e = t.effects[0]
        print("      eff real class:", type(e).__name__, "| bases:", [b.__name__ for b in type(e).__mro__[1:4]])
        for a in [a for a in dir(e) if not a.startswith('_')]:
            try:
                v = getattr(e, a)
                if not callable(v):
                    print(f"        e.{a} = {str(v)[:90]}")
            except Exception as ex:
                print(f"        e.{a} -> {type(ex).__name__}: {str(ex)[:60]}")
        break

print("\n=== TRIGGER TYPE HISTOGRAM ===")
from collections import Counter
ct = Counter(type(c).__name__ for t in tm.triggers for c in t.conditions)
et = Counter(type(e).__name__ for t in tm.triggers for e in t.effects)
print("  condition types:", ct.most_common(20))
print("  effect types:", et.most_common(20))
print("  disabled triggers:", sum(1 for t in tm.triggers if not t.enabled))
print("  looping triggers:", sum(1 for t in tm.triggers if t.looping))

print("\n=== ROUNDTRIP (scratch only) ===")
out = os.path.join(HERE, "roundtrip", "The Siege.out.aoe2scenario")
os.makedirs(os.path.dirname(out), exist_ok=True)
sc.write_to_file(out)
sz_in, sz_out = os.path.getsize(siege), os.path.getsize(out)
print(f"  size in={sz_in} out={sz_out} ratio={sz_out/sz_in:.5f} delta={sz_out-sz_in}")
r = AoE2DEScenario.from_file(out)
print("  reread triggers:", len(r.trigger_manager.triggers),
      " units:", len(r.unit_manager.get_all_units()),
      " map:", r.map_manager.map_size)
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
print(f"  common prefix bytes: {common} / in={len(b_in)} out={len(b_out)}")

print("\n=== CREATE FROM SCRATCH ===")
for ver in ("1.54", "1.59"):
    try:
        fresh = AoE2DEScenario.from_default(scenario_version=ver)
        fout = os.path.join(HERE, "roundtrip", f"fresh_{ver}.aoe2scenario")
        fresh.write_to_file(fout)
        rf = AoE2DEScenario.from_file(fout)
        print(f"  from_default({ver}) OK: map={rf.map_manager.map_size} "
              f"units={len(rf.unit_manager.get_all_units())} "
              f"triggers={len(rf.trigger_manager.triggers)} "
              f"bytes={os.path.getsize(fout)} header={open(fout,'rb').read(4)}")
    except Exception as e:
        print(f"  from_default({ver}) FAILED: {type(e).__name__}: {str(e)[:140]}")

print("\n=== ADD-AND-WRITE SMOKE TEST (new trigger + new unit) ===")
try:
    sc2 = AoE2DEScenario.from_file(siege)
    t = sc2.trigger_manager.add_trigger("__probe__")
    c = t.new_condition.own_objects(source_player=1, quantity=5)
    e = t.new_effect.display_instructions(source_player=1, message="probe", display_time=5)
    sc2.unit_manager.add_unit(player=1, unit_const=83, x=100.5, y=100.5)
    o2 = os.path.join(HERE, "roundtrip", "The Siege.mutated.aoe2scenario")
    sc2.write_to_file(o2)
    r2 = AoE2DEScenario.from_file(o2)
    print("  mutated OK: triggers", len(r2.trigger_manager.triggers),
          "units", len(r2.unit_manager.get_all_units()),
          "bytes", os.path.getsize(o2))
    names = [x.name for x in r2.trigger_manager.triggers]
    print("  contains __probe__:", "__probe__" in names)
except Exception as e:
    import traceback
    print("  MUTATION FAILED:", type(e).__name__, str(e)[:200])
    traceback.print_exc()
