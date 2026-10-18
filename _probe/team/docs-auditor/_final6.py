import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("变更日志.md",encoding="utf-8").read().splitlines()
for n in (9,58,164):
    print("变更日志.md:%d| %s" % (n, L[n-1][:200]))
print()
# every _probe/*.py mentioned anywhere in the 4 core docs - existence
docs = ["项目状态.md","数据模组能力目录v1.md","图形音效模组能力目录v1.md","变更日志.md",
        ".dsh/skills/aoe2-de-dat/SKILL.md",".dsh/skills/aoe2-de-sprites/SKILL.md",".dsh/skills/aoe2-de-ui-textures/SKILL.md"]
missing={}
for d in docs:
    for i,line in enumerate(open(d,encoding="utf-8").read().splitlines(),1):
        for m in re.finditer(r"_probe[\\/][A-Za-z0-9_./\\-]+?\.py", line):
            p = m.group(0).replace("\\","/")
            if not os.path.exists(p):
                missing.setdefault(p, []).append("%s:%d" % (d,i))
print("cited _probe/*.py that DO NOT EXIST (%d):" % len(missing))
for p,v in sorted(missing.items()):
    print("   %-58s %s" % (p, ", ".join(v[:3])))
