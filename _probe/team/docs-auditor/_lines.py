import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for f, lines in [("项目状态.md",[4,78,86,118,123,124,126,140,146,147,151,154,163,164,165,166,181,209,214,219]),
                 (".dsh/skills/aoe2-de-sprites/SKILL.md",[17,26,116,121,169,179,279,335,336,338,339]),
                 (".dsh/skills/aoe2-de-ui-textures/SKILL.md",[42,82,87]),
                 ("图形音效模组能力目录v1.md",[6,22,225,329,386,389]),
                 ("_恢复说明.md",[11,17,18,19,20,26,36,37])]:
    L = open(f, encoding="utf-8").read().splitlines()
    print("="*20, f, len(L), "lines")
    for n in lines:
        s = L[n-1] if n-1 < len(L) else "<EOF>"
        print("%4d| %s" % (n, s[:300]))
