"""Parse an AoE2DE key-value-strings-utf8.txt and dump the trigger-related id ranges.

Format of the file (verified by inspection): id-number, then "quoted string", per line.
Usage: python kv_dump.py <file> <start> <end> [<start2> <end2> ...]
"""
import re
import sys
import io

path = sys.argv[1]
pairs = []
pat = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')
with io.open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        m = pat.match(line.rstrip("\n"))
        if m:
            pairs.append((int(m.group(1)), m.group(2)))

print(f"# parsed {len(pairs)} key-value pairs from {path}")
ids = [p[0] for p in pairs]
print(f"# min id {min(ids)}, max id {max(ids)}")

ranges = list(zip(sys.argv[2::2], sys.argv[3::2]))
for a, b in ranges:
    a, b = int(a), int(b)
    print(f"\n===== id {a} .. {b} =====")
    for i, s in pairs:
        if a <= i <= b:
            print(f"  {i:6d}  {s[:150]}")
