
import sys, os, io, contextlib, time, json, warnings
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
p = sys.argv[1]
ver = open(p, "rb").read(4).decode("ascii", "replace")
t0 = time.time()
rec = {"path": p, "file_version": ver}
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sc = AoE2DEScenario.from_file(p)
    rec.update(status="OK", reported_version=str(sc.scenario_version),
               variant=str(sc.variant), seconds=round(time.time() - t0, 3),
               triggers=len(sc.trigger_manager.triggers),
               units=len(sc.unit_manager.get_all_units()),
               map=sc.map_manager.map_size)
except Exception as e:
    rec.update(status="FAIL", reported_version=None, seconds=round(time.time() - t0, 3),
               err=type(e).__name__ + ": " + str(e).replace("\n", " ")[:140])
print(json.dumps(rec, ensure_ascii=False))
