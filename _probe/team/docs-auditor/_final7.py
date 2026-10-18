import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("数据模组能力目录v1.md",encoding="utf-8").read().splitlines()
for n in (850,918,923,936,2265,4135):
    print("%d| %s" % (n, L[n-1].strip()[:220]))
print()
# basename anywhere on disk?
names = ["_rng3.py","_rng5.py","cost_fallback_impact.py","probe_donor_bias.py","tech_describe_audit.py","tech_describe_audit2.py"]
found={}
for dp,dn,fn in os.walk("."):
    dn[:] = [d for d in dn if d not in (".git","__pycache__")]
    for f in fn:
        if f in names: found.setdefault(f,[]).append(os.path.join(dp,f))
for n in names:
    print("%-26s -> %s" % (n, found.get(n, "NOT ANYWHERE")))
