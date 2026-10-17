# Follow-up probe: difficulty enum, terrain/map access, objectives, trigger_order lists
import os, sys, io, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
import AoE2ScenarioParser.datasets.trigger_lists as tl

OUT = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\final3_out.txt'
buf = io.StringIO()
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); buf.write(s + '\n')

SC = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\extracted\xcam1_0.aoe2scenario'
sc = AoE2DEScenario.from_file(SC)

p('=== enum sizes (beginner-facing vocabulary) ===')
for nm in ['DifficultyLevel','VictoryCondition','Comparison','DiplomacyState','PanelLocation',
           'AttackStance','ObjectType','ObjectState','UnitAIAction','TimeUnit','Operation',
           'Attribute','ObjectClass','Age','TechnologyState','VisibilityState','VictoryTimerType']:
    o = getattr(tl, nm, None)
    if o is None: p('  %-20s MISSING' % nm); continue
    try:
        ms = [m.name for m in o]
        p('  %-20s %3d  %s' % (nm, len(ms), ms[:10]))
    except Exception as ex:
        p('  %-20s -> %s' % (nm, type(o).__name__))

p('\n=== DifficultyLevel full ===')
try:
    p('  ', [(m.name, m.value) for m in tl.DifficultyLevel])
except Exception as ex:
    p('  !!', ex)

p('\n=== MapManager API ===')
mm = sc.map_manager
p('  ', sorted(a for a in dir(mm) if not a.startswith('_')))
for a in ['map_size','map_height','map_color_mood','terrain','terrain_data','map_data','tiles']:
    try:
        v = getattr(mm, a)
        p('  %-14s %s len=%s' % (a, type(v).__name__, len(v) if hasattr(v,'__len__') else '-'))
    except Exception as ex:
        p('  %-14s !! %s' % (a, type(ex).__name__))
try:
    td = mm.terrain
    p('  terrain repr', repr(td)[:200], '| type', type(td).__name__)
    try:
        p('  terrain len', len(td))
    except Exception as ex:
        p('  terrain len !!', type(ex).__name__)
except Exception as ex:
    p('  terrain probe !!', type(ex).__name__, str(ex)[:120])
try:
    t0 = mm.terrain[0]
    p('  terrain[0] type', type(t0).__name__)
    p('  terrain[0] attrs', sorted(a for a in dir(t0) if not a.startswith('_')))
except Exception as ex:
    p('  terrain[0] !!', type(ex).__name__, str(ex)[:120])

p('\n=== objectives = triggers flagged display_as_objective ===')
tm = sc.trigger_manager
obj = [t for t in tm.triggers if getattr(t, 'display_as_objective', 0)]
p('  triggers displayed as objectives:', len(obj))
for t in obj[:8]:
    p('   id=%s name=%r short=%r stid=%s' % (t.trigger_id, t.name, getattr(t,'short_description',None), getattr(t,'short_description_stid',None)))

p('\n=== ordering lists on a trigger (display vs storage hazard) ===')
t = tm.triggers[4]
p('  trigger 4 name=%r conds=%d effs=%d' % (t.name, len(t.conditions), len(t.effects)))
def show(a, v):
    try:
        p('  %-18s = %r' % (a, list(v)))
    except TypeError:
        p('  %-18s = %r (not iterable)' % (a, v))
show('condition_order', t.condition_order)
show('effect_order', t.effect_order)
show('description_order', t.description_order)
show('manager trigger_display_order[:12]', list(tm.trigger_display_order)[:12])
p('  display_as_objective/display_on_screen of trigger 4 =', getattr(t,'display_as_objective',None), getattr(t,'display_on_screen',None))

p('\n=== messages: how a message string is stored on an effect ===')
found = 0
for tr in tm.triggers:
    for e in tr.effects:
        d = {}
        for a in ('effect_type','message','display_time','string_id','sound_name'):
            if hasattr(e, a):
                try: d[a] = getattr(e, a)
                except Exception as ex: d[a] = '<%s>' % type(ex).__name__
        if d.get('message'):
            p('  trig %r eff_type=%s msg=%r display_time=%s sound=%r' % (tr.name[:26], d.get('effect_type'), str(d['message'])[:90], d.get('display_time'), d.get('sound_name')))
            found += 1
            if found >= 6: break
    if found >= 6: break

p('\n=== xs ===')
try:
    p('  xs_manager.script_name =', repr(sc.xs_manager.script_name))
    xt = sc.xs_manager.xs_trigger
    p('  xs_trigger name=%r enabled=%s effects=%d' % (xt.name, xt.enabled, len(xt.effects)))
except Exception as ex:
    p('  !!', type(ex).__name__, str(ex)[:150])

open(OUT,'w',encoding='utf-8').write(buf.getvalue())
print('WROTE', OUT)
