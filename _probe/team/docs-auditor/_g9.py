import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open(".dsh/skills/aoe2-de-dat/SKILL.md",encoding="utf-8").read().splitlines()
for n in range(292,340):
    t=L[n-1]
    if t.strip(): print("%d: %s" % (n, t[:300]))
