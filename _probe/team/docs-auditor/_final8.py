import sys, io, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
def cnt(root):
    n=0
    for dp,dn,fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git","__pycache__")]
        n += sum(1 for f in fn if f.endswith(".py"))
    return n
print("workspace .py total:", cnt("."))
print("_probe .py excl team:", cnt("_probe") - 0)
print("_rng4.py exists:", os.path.exists("_probe/_rng4.py"))
# git
def g(*a):
    return subprocess.run(["git"]+list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
print("commits:", len([l for l in g("log","--oneline").stdout.splitlines() if l.strip()]))
for l in g("log","--oneline").stdout.splitlines(): print("   ", l[:110])
# old-root files at HEAD
r = g("grep","-l","工作区2","HEAD","--","*.py")
print("HEAD *.py containing 工作区2:", len([l for l in r.stdout.splitlines() if l.strip()]))
# mods
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods"
loc = os.listdir(os.path.join(PROF,"local")); sub = [d for d in os.listdir(os.path.join(PROF,"subscribed")) if os.path.isdir(os.path.join(PROF,"subscribed",d))]
print("mods: local=%d subscribed=%d total=%d" % (len(loc), len(sub), len(loc)+len(sub)))
# 551412 sld count
p = os.path.join(PROF,"subscribed","551412_村民变羊 - Villagers turn into sheep - 贴图替换版")
n=0; tot=0
for dp,dn,fn in os.walk(p):
    for f in fn:
        tot+=1
        if f.endswith(".sld"): n+=1
print("551412: total files=%d  .sld=%d" % (tot, n))
# dat
G = r"d:\games\steam\steamapps\common\AoE2DE"
import zlib
datp = os.path.join(G,"resources","_common","dat","empires2_x2_p1.dat")
raw = open(datp,"rb").read()
try: dec = zlib.decompress(raw, 47)
except Exception: dec = zlib.decompress(raw[8:], -15)
print("dat on disk:", len(raw), " decompressed:", len(dec))
# sld count
gd = os.path.join(G,"resources","_common","drs","graphics")
names = [f for f in os.listdir(gd) if f.lower().endswith(".sld")]
print(".sld on disk:", len(names))
