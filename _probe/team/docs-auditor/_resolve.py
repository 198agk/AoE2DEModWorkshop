import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def scan(root, needle, label):
    hits=[]
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ("__pycache__",".git")]
        for f in fn:
            if not f.endswith(".py"): continue
            p=os.path.join(dp,f)
            try: t=open(p,encoding="utf-8",errors="replace").read()
            except Exception: continue
            for i,l in enumerate(t.splitlines(),1):
                if needle in l: hits.append((p,i,l.strip()[:180]))
    print("== %s: %d hit(s) under %s" % (label, len(hits), root))
    for p,i,l in hits[:12]: print("   %s:%d  %s" % (p,i,l))
scan("aoe2mod","resolve_mod_name","resolve_mod_name/aoe2mod")
scan("_probe","def resolve_mod_name","def resolve_mod_name/_probe")
scan("aoe2mod","NO in-game test","NO in-game test/aoe2mod")
scan("aoe2mod","EITHER file","EITHER file/aoe2mod")
