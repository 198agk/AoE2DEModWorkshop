import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open(".dsh/skills/aoe2-de-dat/SKILL.md",encoding="utf-8").read().splitlines()
for n in (44,45,46,47,48):
    print("--- %d: %s" % (n, L[n-1][:1500]))
print()
for n in (463,464,465,466,467,468,469,470,471):
    print("--- %d: %s" % (n, L[n-1][:900]))
