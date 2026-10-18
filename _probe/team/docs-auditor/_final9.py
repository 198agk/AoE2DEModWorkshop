import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
team = os.path.abspath("_probe/team")
def cnt(root, skip_team=True):
    n=0
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git","__pycache__")]
        if skip_team and os.path.abspath(dp).startswith(team): continue
        n += sum(1 for f in fn if f.endswith(".py"))
    return n
print("workspace .py excl _probe/team:", cnt("."))
print("_probe .py excl _probe/team:", cnt("_probe"))
print("_probe .py incl _probe/team:", cnt("_probe", False))
print("_probe top-level .py:", len([f for f in os.listdir("_probe") if f.endswith(".py")]))
print("_probe/team .py:", cnt(team, False))
print("aoe2mod .py:", cnt("aoe2mod"))
