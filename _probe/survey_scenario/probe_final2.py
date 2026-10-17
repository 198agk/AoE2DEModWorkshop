import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# Final consolidated probe for SCENARIO_SURVEY.md
# - full shape of a Trigger object (storage model)
# - condition/effect field values on a real trigger
# - difficulty handling
# - objectives / instructions / message storage
# - whether the Triggers section carries any id table
import os, sys, json, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

OUT = _HERE_PATH("_probe", "survey_scenario", "final2_out.txt")
buf = io.StringIO()
def p(*a):
    s = ' '.join(str(x) for x in a)
    print(s); buf.write(s + '\n')

SC = _HERE_PATH("_probe", "survey_scenario", "extracted", "xcam1_0.aoe2scenario")
sc = AoE2DEScenario.from_file(SC)
tm = sc.trigger_manager

p('=== Trigger class public API ===')
p(sorted(a for a in dir(tm.triggers[0]) if not a.startswith('_')))

t = tm.triggers[0]
p('\n=== trigger 0 attributes ===')
for a in ['trigger_id','name','description','enabled','looping','display_order','execute_on_load','short_list','trigger_display_order','new_condition','new_effect','conditions','effects']:
    try:
        v = getattr(t, a)
        if a in ('conditions','effects'):
            p(' ', a, '->', type(v).__name__, 'len', len(v))
        else:
            p(' ', a, '=', repr(v)[:200])
    except Exception as e:
        p(' ', a, '!!', type(e).__name__, str(e)[:110])

# find a trigger with both conditions and effects
cand = None
for tr in tm.triggers:
    if len(tr.conditions) >= 2 and len(tr.effects) >= 1:
        cand = tr; break
if cand is None:
    for tr in tm.triggers:
        if len(tr.conditions) >= 1:
            cand = tr; break
p('\n=== sample trigger with real content ===')
p(' id', cand.trigger_id, '| name', repr(cand.name), '| conds', len(cand.conditions), '| effects', len(cand.effects))
for c in cand.conditions:
    p('  CONDITION attrs:', sorted(a for a in dir(c) if not a.startswith('_')))
    break
for c in cand.conditions:
    d = {}
    for a in sorted(a for a in dir(c) if not a.startswith('_')):
        try:
            v = getattr(c, a)
        except Exception as e:
            v = '<%s>' % type(e).__name__
        if callable(v) or isinstance(v, (list, dict)):
            continue
        d[a] = v
    p('  COND', c.condition_type, json.dumps(d, default=str, ensure_ascii=False)[:400])
for e in cand.effects:
    d = {}
    for a in sorted(a for a in dir(e) if not a.startswith('_')):
        try:
            v = getattr(e, a)
        except Exception as ex:
            v = '<%s>' % type(ex).__name__
        if callable(v) or isinstance(v, (list, dict)):
            continue
        d[a] = v
    p('  EFF', e.effect_type, json.dumps(d, default=str, ensure_ascii=False)[:400])

p('\n=== difficulty ===')
p(' conditions of type 18 (difficulty level) count:',
  sum(1 for tr in tm.triggers for c in tr.conditions if int(c.condition_type) == 18))
for tr in tm.triggers:
    for c in tr.conditions:
        if int(c.condition_type) == 18:
            d = {a: getattr(c, a) for a in ['quantity','condition_type','inverted','source_player'] if hasattr(c, a)}
            p('   ', tr.name[:40], d)

p('\n=== objectives / instructions ===')
mm = sc.message_manager
for a in ['instructions','hints','victory','loss','history','scouts','instructions_string_table_id']:
    try:
        p(' ', a, '=', repr(getattr(mm, a))[:160])
    except Exception as ex:
        p(' ', a, '!!', type(ex).__name__)
p(' Messages section is', type(sc.sections['Messages']).__name__)

p('\n=== Triggers section shape ===')
sec = sc.sections['Triggers']
p(' ', type(sec).__name__, [a for a in dir(sec) if not a.startswith('_')][:20])
p('\n=== named vocabulary available for UI ===')
import AoE2ScenarioParser.datasets.trigger_lists as tl
p(' trigger_lists exports:', sorted(n for n in dir(tl) if not n.startswith('_'))[:60])
for nm in ('ConditionType','EffectType','ConditionId','EffectId','Attribute','ObjectClass'):
    if hasattr(tl, nm):
        o = getattr(tl, nm)
        try:
            p('  %s -> %d members' % (nm, len(list(o))))
        except Exception as ex:
            p('  %s -> %s' % (nm, type(o).__name__))

p('\n=== write to file at same version (roundtrip on extracted official scenario) ===')
dst = _HERE_PATH("_probe", "survey_scenario", "roundtrip", "xcam1_0.roundtrip.aoe2scenario")
sc.write_to_file(dst)
a = os.path.getsize(SC); b = os.path.getsize(dst)
p(' bytes in=%d out=%d ratio=%.5f' % (a, b, b / a))
p(' header in =', open(SC,'rb').read(8).hex(' '), ' out =', open(dst,'rb').read(8).hex(' '))
sc2 = AoE2DEScenario.from_file(dst)
p(' reread: triggers %d conds %d effects %d units %d' % (
    len(sc2.trigger_manager.triggers),
    sum(len(t.conditions) for t in sc2.trigger_manager.triggers),
    sum(len(t.effects) for t in sc2.trigger_manager.triggers),
    len(sc2.unit_manager.get_all_units())))

open(OUT, 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE', OUT)
