import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("项目状态.md",encoding="utf-8").read().splitlines()
for n in range(111,158):
    print("%4d| %s" % (n, L[n-1][:250]))
