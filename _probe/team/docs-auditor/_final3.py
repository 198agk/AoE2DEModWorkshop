import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def count(root, skipteam=True):
    n=0
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git","__pycache__")]
        if skipteam and (os.sep+"team") in dp: continue
        n += sum(1 for f in fn if f.endswith(".py"))
    return n
print("_probe .py excluding _probe/team:", count("_probe"))
t = open("_probe/out_suites_final2.txt", encoding="utf-8", errors="replace").read()
lines = [l for l in t.splitlines() if l.strip()]
print("out_suites_final2.txt non-empty lines:", len(lines))
print("--- first 3:"); [print("   ", l[:120]) for l in lines[:3]]
print("--- last 6:"); [print("   ", l[:120]) for l in lines[-6:]]
print("PASSED marker present:", "PASSED" in t, "| FAILED count:", t.count("FAILED"))
