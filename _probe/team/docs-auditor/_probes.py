import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for n in ["test_panel_is_not_build_menu.py","test_zero_mod_experiment.py","test_button_groups.py",
          "test_reskin.py","test_civ_unit_gate.py","test_scan_panels.py","sldlib.py",
          "loose_override_proof.py","sections_last3_table.py","sections_settle.py","run_long.py"]:
    hits = glob.glob(os.path.join("_probe","**",n), recursive=True)
    print("%-40s %s" % (n, hits[:2] if hits else "*** ABSENT ***"))
print()
print("hud_render contents:", sorted(os.path.basename(p) for p in glob.glob("_probe/hud_render/*"))[:40])
