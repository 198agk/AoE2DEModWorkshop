import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src = open("aoe2mod/game/buildpanel.py",encoding="utf-8").read().splitlines()
for i,l in enumerate(src,1):
    s=l.strip()
    if s.startswith("def ") or s.startswith("class "):
        print("%4d| %s" % (i, s[:160]))
