
import sys, os, io, contextlib, json, warnings, traceback
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
v = sys.argv[1]
dst = sys.argv[2]
rec = {"version": v}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        sc = AoE2DEScenario.from_default(v)
    rec["map"] = sc.map_manager.map_size
    sc.write_to_file(dst)
    re_ok = True
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            AoE2DEScenario.from_file(dst)
    except Exception as e2:
        re_ok = "reread FAILED: " + type(e2).__name__
    rec.update(status="OK", bytes=os.path.getsize(dst), reread=str(re_ok),
               triggers=len(sc.trigger_manager.triggers))
except Exception as e:
    rec.update(status="FAIL", err=type(e).__name__ + ": " + str(e)[:120])
print(json.dumps(rec, ensure_ascii=False))
