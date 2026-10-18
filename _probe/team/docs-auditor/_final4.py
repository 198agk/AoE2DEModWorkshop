import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t = open("_probe/out_suites_final2.txt", encoding="utf-16").read()
print("decoded utf-16: exit=0 count =", t.count("exit=0"), "| ALL PASSED:", "SUITES: ALL PASSED" in t)
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE"
hits=[]
for dp,dn,fn in os.walk(PROF):
    for d in dn:
        if "dsh test" in d.lower(): hits.append(os.path.join(dp,d))
print("mods named 'dsh test*' on disk:")
for h in hits: print("   ", h)
print()
# info.json Title for each
import json
for h in hits:
    p=os.path.join(h,"info.json")
    if os.path.exists(p):
        txt=open(p,encoding="utf-8",errors="replace").read()
        for line in txt.splitlines():
            if '"Title"' in line: print("   ", os.path.basename(h), "->", line.strip()[:110])
print()
print("HUD pngs anywhere:", [f for dp,dn,fn in os.walk(".") for f in fn if "HUD_COMP" in f][:5])
print("_shots exists:", os.path.exists("_shots"))
print("hud_render files:", len(os.listdir("_probe/hud_render")))
