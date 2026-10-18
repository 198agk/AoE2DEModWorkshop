import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L=open("项目状态.md",encoding="utf-8").read().splitlines()
s=L[151]
print("项目状态.md:152 len",len(s))
print("tail:", s[-220:])
print("has 已装待验:", "已装待验" in s)
print()
j=json.load(open("aoe2mod/schema/intents.json",encoding="utf-8"))
ints=j["intents"]
print("intent count:", len(ints))
from collections import Counter
print("strategies:", Counter(v["compile"]["strategy"] for v in ints.values()))
print("names:", list(ints.keys()))
