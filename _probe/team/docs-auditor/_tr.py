import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src = open("aoe2mod/game/buildpanel.py",encoding="utf-8").read()
for i,l in enumerate(src.splitlines(),1):
    if "train" in l.lower() and ("def " in l or "=" in l):
        print("buildpanel:%d| %s" % (i, l.strip()[:170]))
print("---- api.py train refs")
src2 = open("aoe2mod/api.py",encoding="utf-8").read()
for i,l in enumerate(src2.splitlines(),1):
    if "train_location" in l or "_train" in l:
        print("api:%d| %s" % (i, l.strip()[:170]))
