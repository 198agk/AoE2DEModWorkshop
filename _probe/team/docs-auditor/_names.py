import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
names = ["test_civ_unit_gate.py","probe_dat_layer_modifiable.py","probe_dat_only_defect.py","probe_availability_readside.py",
         "test_dat_edit_routes.py","test_overlay_depth.py","test_dat_json_override.py","test_reskin.py","test_retarget.py",
         "loose_override_proof.py","sections_last3_table.py","sections_settle.py","probe_dat_roundtrip.py"]
idx = {}
for dp, dn, fn in os.walk("_probe"):
    dn[:] = [d for d in dn if d != "__pycache__"]
    for f in fn: idx.setdefault(f, []).append(os.path.join(dp, f))
for n in names:
    print("%-38s %s" % (n, idx.get(n, "**ABSENT**")))
print()
print("sld_out exists:", os.path.isdir("_probe/sld_out"))
print("out_suites_bundle2 exists:", os.path.exists("_probe/out_suites_bundle2.txt"))
print("big_teamcolor anywhere:", [p for k,v in idx.items() if "teamcolor" in k.lower() for p in v][:5])
print("HUD_COMPOSITE anywhere:", [p for k,v in idx.items() if "hud_compo" in k.lower() or "hud_compar" in k.lower() for p in v][:5])
