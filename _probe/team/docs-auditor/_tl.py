import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src=open("aoe2mod/dat/parser.py",encoding="utf-8").read().splitlines()
for i in range(700,740):
    print("%4d| %s" % (i, src[i-1].rstrip()[:180]))
