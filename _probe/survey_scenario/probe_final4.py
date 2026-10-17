
import sys, io, json, contextlib, warnings, os
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
OUT = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\final4_out.txt'
buf = io.StringIO()
def p(*a):
    s=' '.join(str(x) for x in a); print(s); buf.write(s+'\n')
SC = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario\extracted\xcam1_0.aoe2scenario'
with contextlib.redirect_stdout(io.StringIO()):
    sc = AoE2DEScenario.from_file(SC)

p('=== Options section: everything a beginner sees in the Options tab ===')
om = sc.option_manager
names = sorted(a for a in dir(om) if not a.startswith('_'))
p('  attrs:', names)
for a in names:
    if a in ('commit','construct','get_scenario','instance_number_history'): continue
    try:
        v = getattr(om, a)
    except Exception as ex:
        v = '<%s>' % type(ex).__name__
    if callable(v): continue
    p('   %-42s = %r' % (a, v))

p('\n=== GlobalVictory raw (from section) ===')
gv = sc.sections['GlobalVictory']
for a in sorted(a for a in dir(gv) if not a.startswith('_')):
    try:
        v = getattr(gv, a)
    except Exception as ex:
        continue
    if callable(v): continue
    p('   %s = %r' % (a, v))

p('\n=== Player 1 fields (beginner-facing) ===')
pl = sc.player_manager.players[1]
for a in sorted(a for a in dir(pl) if not a.startswith('_')):
    if a in ('commit','construct','get_scenario','instance_number_history'): continue
    try:
        v = getattr(pl, a)
    except Exception as ex:
        v = '<%s>' % type(ex).__name__
    if callable(v): continue
    p('   %-34s = %r' % (a, v))

p('\n=== AI files (Files section) ===')
for st in sc.sections['Files'].struct_models:
    for sm in getattr(st, 'struct_models', []) or []:
        try:
            fm = sm.retriever_map
            p('   AI: %r' % (getattr(sm, 'name', None),))
        except Exception:
            pass
fs = sc.sections['Files']
for a in sorted(a for a in dir(fs) if not a.startswith('_')):
    try: v = getattr(fs, a)
    except Exception: continue
    if callable(v): continue
    p('   Files.%s = %r' % (a, str(v)[:80]))

p('\n=== trigger display/objective flags available ===')
tm = sc.trigger_manager
t = tm.triggers[13]
for a in ('trigger_id','name','description','short_description','short_description_stid','display_as_objective','display_on_screen','mute_objectives','enabled','looping','execute_on_load','condition_order','effect_order','description_order'):
    try: p('   %-26s = %r' % (a, getattr(t, a)))
    except Exception as ex: p('   %-26s !! %s' % (a, type(ex).__name__))

p('\n=== Units: a single unit record ===')
u = sc.unit_manager.get_all_units()[0]
for a in sorted(a for a in dir(u) if not a.startswith('_')):
    if a in ('commit','construct','get_scenario','instance_number_history'): continue
    try: v = getattr(u, a)
    except Exception as ex: v = '<%s>' % type(ex).__name__
    if callable(v): continue
    p('   %-26s = %r' % (a, v))

p('\n=== MapManager write API (terrain editing) ===')
mm = sc.map_manager
for a in ('map_size','map_width','map_height','map_color_mood','get_tile','get_square_2d','set_elevation'):
    p('   %s -> %s' % (a, type(getattr(mm, a)).__name__))
import inspect
for a in ('get_tile','set_elevation','get_square_2d'):
    try: p('   %s%s' % (a, inspect.signature(getattr(mm, a))))
    except Exception as ex: p('   %s sig !! %s' % (a, ex))
import AoE2ScenarioParser.datasets.terrains as TER
p('   terrains module members:', [n for n in dir(TER) if not n.startswith('_')][:12])
try:
    p('   TerrainId members:', len(list(TER.TerrainId)))
except Exception as ex:
    p('   TerrainId !!', ex)

open(OUT,'w',encoding='utf-8').write(buf.getvalue())
print('WROTE', OUT)
