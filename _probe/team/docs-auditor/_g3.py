import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("数据模组能力目录v1.md",encoding="utf-8").read().splitlines()
for n in (3205,3210,3212,3530,3534,3536,3538,3540,3542):
    print("---- v1.md:%d" % n); print(L[n-1][:1400]); print()
