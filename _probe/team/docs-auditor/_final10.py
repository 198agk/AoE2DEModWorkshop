import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
t="_probe/team"
for d in sorted(os.listdir(t)):
    p=os.path.join(t,d)
    if os.path.isdir(p):
        n=sum(1 for dp,dn,fn in os.walk(p) for f in fn if f.endswith(".py"))
        print("%-28s %5d .py" % (d, n))
print()
# top-level _probe .py by mtime bucket
files=[f for f in os.listdir("_probe") if f.endswith(".py")]
recent=[f for f in files if time.time()-os.path.getmtime(os.path.join("_probe",f)) < 7*86400]
print("top-level _probe .py:", len(files), " modified in last 7d:", len(recent))
for f in sorted(recent)[:15]: print("    recent:", f)
