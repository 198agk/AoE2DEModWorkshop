import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
pats = [r"21,001", r"20,883", r"20883", r"15,486", r"15486", r"63 个文明", r"8,291", r"8,656", r"2,138", r"1,840"]
for f in ("项目状态.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md",
          ".dsh/skills/aoe2-de-dat/SKILL.md",".dsh/skills/aoe2-de-sprites/SKILL.md"):
    L=open(f,encoding="utf-8").read().splitlines()
    for i,line in enumerate(L,1):
        for p in pats:
            if re.search(p,line):
                print("%s:%d [%s] %s" % (f,i,p,line.strip()[:150])); break
