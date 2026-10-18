import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def show(path, nums, w=260):
    L = open(path, encoding="utf-8").read().splitlines()
    print("### " + path + "  (%d lines)" % len(L))
    for n in nums:
        if 1 <= n <= len(L):
            print("%s:%d| %s" % (path, n, L[n-1][:w]))
        else:
            print("%s:%d| <OUT OF RANGE>" % (path, n))
    print()
show("项目状态.md", [236, 219, 140, 154, 181])
show(".dsh/skills/aoe2-de-sprites/SKILL.md", [17, 26, 116, 121, 169, 179, 279, 335, 336, 338, 339])
show(".dsh/skills/aoe2-de-dat/SKILL.md", [38, 46, 298, 300, 302, 303, 304, 306, 448, 467])
show(".dsh/skills/aoe2-de-ui-textures/SKILL.md", [42, 82, 87])
show("图形音效模组能力目录v1.md", [6, 22, 225, 292, 329, 386, 389, 390])
show("数据模组能力目录v1.md", [1993, 2988, 3204, 3210, 3212, 3517, 3519, 3532])
show("_恢复说明.md", [11, 17, 18, 19, 20, 26, 36, 37])
