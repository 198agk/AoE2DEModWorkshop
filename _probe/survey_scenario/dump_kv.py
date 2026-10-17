"""Dump the game's key-value string table to kv_all.json (scratch only, read-only on game dir)."""
import json
import os
import re

SRC = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\en\strings\key-value\key-value-strings-utf8.txt"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "kv_all.json")

pat = re.compile(r'^(\d+)\s+"(.*)"\s*$')
kv = {}
with open(SRC, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = pat.match(line.rstrip("\n"))
        if m:
            kv[int(m.group(1))] = m.group(2)

json.dump(kv, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(f"parsed {len(kv)} pairs from {SRC}")
print(f"size {os.path.getsize(SRC)} -> json {os.path.getsize(OUT)}")
ids = sorted(kv)
print("id range:", ids[0], "..", ids[-1])
print("sample:", {k: kv[k] for k in (0, 1, 10501, 11555) if k in kv})
