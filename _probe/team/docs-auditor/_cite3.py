import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def run(path, nums, w=320):
    L = open(path, encoding="utf-8").read().splitlines()
    print("### " + path)
    for n in nums:
        print("%d| %s" % (n, L[n-1][:w] if n<=len(L) else "<OOR>"))
    print()
run("项目状态.md", [4, 78, 86, 143, 152, 163, 164, 165, 166, 214])
run("数据模组能力目录v1.md", [2001, 2099, 2209, 2865])
run("图形音效模组能力目录v1.md", [240, 241, 273])
run(".dsh/skills/aoe2-de-dat/SKILL.md", [126, 272])
