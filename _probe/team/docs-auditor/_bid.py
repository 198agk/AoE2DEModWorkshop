import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
for root in ("aoe2mod","tools"):
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d!="__pycache__"]
        for f in fn:
            if not f.endswith(".py"): continue
            p=os.path.join(dp,f)
            t=open(p,encoding="utf-8",errors="replace").read().splitlines()
            hits=[(i,l) for i,l in enumerate(t,1) if "button_id" in l]
            if hits:
                print("==",p,len(hits))
                for i,l in hits[:5]: print("   %d| %s" % (i,l.strip()[:150]))
