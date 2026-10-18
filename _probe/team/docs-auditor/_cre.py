import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src=open("aoe2mod/dat/parser.py",encoding="utf-8").read().splitlines()
for i,l in enumerate(src,1):
    if "read_creatable" in l or "read_unit" in l or "unit_headers" in l or '"units"' in l:
        print("%4d| %s" % (i, l.strip()[:170]))
