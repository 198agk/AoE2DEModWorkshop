import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t = open("_probe/test_panel_is_not_build_menu.py", encoding="utf-8").read()
print("lines:", len(t.splitlines()))
for i, ln in enumerate(t.splitlines(), 1):
    if any(k in ln for k in ("ZERO","zero civs","0 civs","absent","omits","omitted","MISSING","missing")):
        print("  %d: %s" % (i, ln[:170]))
print("---- in run_suites?")
s = open("_probe/run_suites.py", encoding="utf-8").read()
for name in ("test_panel_is_not_build_menu","test_panel_shape"):
    print(name, "->", name+".py" in s)
