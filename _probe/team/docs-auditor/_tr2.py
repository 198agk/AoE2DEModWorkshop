import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for f in ["aoe2mod/dat/parser.py","aoe2mod/game/buildpanel.py","aoe2mod/intent/availability.py","_probe/probe_train_locations.py"]:
    try: src=open(f,encoding="utf-8").read().splitlines()
    except Exception as e: print(f, "ERR", e); continue
    hits=[(i,l) for i,l in enumerate(src,1) if "train_location" in l or "training_building" in l or "train_map" in l]
    print("==",f,len(src),"lines, train hits:",len(hits))
    for i,l in hits[:8]: print("  %d| %s" % (i,l.strip()[:170]))
