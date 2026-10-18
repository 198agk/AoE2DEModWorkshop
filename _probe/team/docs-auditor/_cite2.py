import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def run(path, nums, w=400):
    L = open(path, encoding="utf-8").read().splitlines()
    print("### " + path)
    for n in nums:
        print("%s:%d| %s" % (path, n, L[n-1][:w] if n<=len(L) else "<OOR>"))
    print()
run(".dsh/skills/aoe2-de-dat/SKILL.md", [46, 448, 467])
run("项目状态.md", [126, 219])
