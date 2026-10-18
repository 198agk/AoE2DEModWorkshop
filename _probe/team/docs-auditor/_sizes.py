import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
gd = os.path.join(G,"resources","_common","drs","graphics")
for n in ["u_shp_junk_x1.sld","u_shp_canoe_x1.sld","u_shp_caravel_x1.sld",
          "u_shp_merchant_ship_x1.sld","u_shp_merchant_ship_x2.sld"]:
    p=os.path.join(gd,n)
    print("%-32s exists=%-5s size=%s" % (n, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else "-"))
print()
# installed mods total file count (doc says 623)
base=r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
tot=0; per={}
for kind in ("local","subscribed"):
    p=os.path.join(base,kind)
    if not os.path.isdir(p): continue
    for d in sorted(os.listdir(p)):
        q=os.path.join(p,d)
        if not os.path.isdir(q): continue
        n=sum(len(fs) for _,_,fs in os.walk(q))
        per[kind+"/"+d]=n; tot+=n
print("mods total files:", tot, "(doc 图形音效:329 says 623)")
for k,v in sorted(per.items()): print("  %-70s %d" % (k[:68], v))
