import sys, io, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
G = r"d:\games\steam\steamapps\common\AoE2DE"
hits = glob.glob(os.path.join(G,"**","*techtree*"), recursive=True)
for h in hits: print(h.replace(G,""))
print()
hits2 = glob.glob(os.path.join(G,"**","*futureavailable*"), recursive=True)
for h in hits2: print(h.replace(G,""))
