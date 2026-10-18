# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.getcwd()
GAME = r"d:\games\steam\steamapps\common\AoE2DE"
targets = [
    "_probe/sldlib.py", "_probe/run_suites.py", "_probe/loose_override_proof.py",
    "_probe/sections_last3_table.py", "_probe/sections_settle.py",
    "_probe/hud_render/hudrender.py", "_probe/hud_render/HUD_RENDER_REPORT.md",
    "_probe/hud_render/HUD_COMPARISON.png", "_probe/hud_render/HUD_COMPOSITE.png",
    "_shots/sld_render/big_teamcolor.png",
    "_probe/source/genieutils", "_probe/datparse/parse_dat.py", "_probe/serializer/write_dat.py",
    "_probe/build_resource_labels.py", "_probe/probe_attribute_unlock.py",
    "_probe/probe_refusal_reasons.py", "_probe/sweep_tech_effect.py",
    "_probe/probe_type3_contrast.py", "_probe/probe_tech_side_verdict.py",
    "_probe/diag_drift.py",
    "aoe2mod/tests/test_roundtrip.py", "aoe2mod/tests/test_emit_mod.py",
    "aoe2mod/intent/availability.py",
    "aoe2mod/schema", "aoe2mod/schema/intents.json",
    "tools/sync_engine.py",
]
for t in targets:
    for base in (ROOT, GAME):
        p = os.path.join(base, t)
        if os.path.exists(p):
            print("OK   %-55s %s" % (t, "ws" if base == ROOT else "game"))
            break
    else:
        print("MISS %-55s" % t)

print("\n--- dirs under _probe (top) ---")
for d in sorted(os.listdir(os.path.join(ROOT, "_probe"))):
    p = os.path.join(ROOT, "_probe", d)
    print(("[D] " if os.path.isdir(p) else "[F] ") + d)
