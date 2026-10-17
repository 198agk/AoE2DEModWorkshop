"""Final facts for the report: variant meaning, victory, messages, trigger naming, cinematics."""
import io, contextlib, os, warnings
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.datasets.scenario_variant import ScenarioVariant

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "extracted", "xcam1_0.aoe2scenario")   # 1.57, 134 triggers
B = os.path.join(HERE, "extracted", "xcam1_1.aoe2scenario")   # 1.58, 47 triggers
LEG = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\gamedata_x2\real_world_amazon.scx"

print("=== ScenarioVariant enum ===")
try:
    print("  members:", [(m.name, m.value) for m in ScenarioVariant])
except Exception as e:
    print("  ", type(e).__name__, e)
for p in (A, B, LEG):
    src = open(p, "rb").read(4).decode()
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sc = AoE2DEScenario.from_file(p)
        print(f"  {os.path.basename(p):<34} ver={src} variant={sc.variant!r} (type {type(sc.variant).__name__})")
    except Exception as e:
        print(f"  {os.path.basename(p):<34} ver={src} FAIL {type(e).__name__}")


def rd(p):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return AoE2DEScenario.from_file(p)


sc = rd(A)
print()
print("=== MESSAGES on a real campaign scenario (xcam1_0) ===")
m = sc.message_manager
for a in ("instructions", "hints", "victory", "loss", "history", "scouts"):
    v = getattr(m, a)
    print(f"  {a}: {repr(v)[:160]}")
print("  instructions_string_table_id:", m.instructions_string_table_id)
print("  victory_string_table_id     :", m.victory_string_table_id)

print()
print("=== GLOBAL VICTORY ===")
for a in [a for a in dir(sc.player_manager) if not a.startswith('_')]:
    pass
try:
    from AoE2ScenarioParser.objects.data_objects.player import Player
except Exception:
    pass
# Victory lives in options manager in ASP
om = sc.option_manager
for a in ("victory_condition", "victory_score", "victory_years", "victory_custom_conditions_required",
          "all_techs", "lock_teams", "lock_coop_alliances", "allow_players_choose_teams",
          "random_start_points", "secondary_game_modes", "collide_and_correct", "villager_force_drop"):
    try:
        print(f"  om.{a} = {getattr(om, a)!r}")
    except Exception as e:
        print(f"  om.{a} -> {type(e).__name__}")

print()
print("=== TRIGGER NAMING + DISPLAY ORDER HAZARD ===")
tm = sc.trigger_manager
print(f"  triggers={len(tm.triggers)} variables={len(tm.variables)}")
print("  first 12 trigger names:", [t.name for t in tm.triggers[:12]])
dorder = tm.trigger_display_order
print("  trigger_display_order[:20]:", dorder[:20])
print("  display order == storage order?", dorder == list(range(len(tm.triggers))))
print("  is it a permutation of range(N)?", sorted(dorder) == list(range(len(tm.triggers))))
named = sum(1 for t in tm.triggers if t.name and not t.name.startswith("Trigger "))
print(f"  triggers with a real (non-default) name: {named}/{len(tm.triggers)}")
print("  description sample:", [t.description[:60] for t in tm.triggers[:6]])
print("  enabled/looping:", sum(t.enabled for t in tm.triggers), "/", sum(t.looping for t in tm.triggers))

print()
print("=== VARIABLES ===")
if tm.variables:
    v = tm.variables[0]
    print("  attrs:", [a for a in dir(v) if not a.startswith('_')])
    for a in [a for a in dir(v) if not a.startswith('_')]:
        try:
            x = getattr(v, a)
            if not callable(x):
                print(f"   v.{a} = {x!r}")
        except Exception as e:
            print(f"   v.{a} -> {type(e).__name__}")

print()
print("=== CONDITION/EFFECT TYPE COUNTS ON A REAL SCENARIO (xcam1_0) ===")
from collections import Counter
def tname(c):
    try:
        return c.condition_type.name if hasattr(c.condition_type, "name") else c.condition_type
    except Exception:
        return "?"
def ename(e):
    try:
        return e.effect_type.name if hasattr(e.effect_type, "name") else e.effect_type
    except Exception:
        return "?"
cc = Counter(tname(c) for t in tm.triggers for c in t.conditions)
ec = Counter(ename(e) for t in tm.triggers for e in t.effects)
print("  distinct condition types used:", len(cc))
print("  top 12 conditions:", cc.most_common(12))
print("  distinct effect types used:", len(ec))
print("  top 12 effects:", ec.most_common(12))
print("  total conditions:", sum(cc.values()), "total effects:", sum(ec.values()))

print()
print("=== CINEMATICS / BACKGROUND ===")
print("  cinematics:", [a for a in dir(sc) if 'cinematic' in a.lower()])
for a in ("ascii_pregame", "ascii_victory", "ascii_loss"):
    try:
        print(f"   {a} = {getattr(sc, a)!r}")
    except Exception as e:
        print(f"   {a} -> {type(e).__name__}")
