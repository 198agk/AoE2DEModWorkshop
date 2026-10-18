import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def dump(path, rng, w=500):
    L=open(path,encoding="utf-8").read().splitlines()
    print("### %s (%d lines)" % (path, len(L)))
    for n in rng:
        if 1 <= n <= len(L) and L[n-1].strip():
            print("%d| %s" % (n, L[n-1][:w]))
    print()
dump("图形音效模组能力目录v1.md", range(1,30))
dump("图形音效模组能力目录v1.md", range(378,400))
dump(".dsh/skills/aoe2-de-sprites/SKILL.md", range(326,343))
dump("项目状态.md", range(208,222))
