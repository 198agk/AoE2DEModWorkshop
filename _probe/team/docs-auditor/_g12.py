import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open(".dsh/skills/aoe2-de-dat/SKILL.md",encoding="utf-8").read().splitlines()
print("=== dat SKILL: lines mentioning block / 118 / misread / omitted")
for i,t in enumerate(L,1):
    if ("118" in t) or ("misread" in t) or ("nowhere" in t) or ("not build menu" in t.lower()):
        print("%d: %s" % (i, t[:230]))
