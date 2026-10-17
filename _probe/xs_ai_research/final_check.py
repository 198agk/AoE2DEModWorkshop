import io, os, sys, re, unicodedata
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(D, 'AI_SCRIPTING_AIREF.md')

t = io.open(P, encoding='utf-8', newline='').read()
lines = t.split('\n')
print(f"bytes on disk = {os.path.getsize(P)}")
print(f"chars = {len(t)}  lines = {len(lines)}")

print("\n=== non-ASCII inventory ===")
inv = {}
for ch in t:
    if ord(ch) > 127:
        inv[ch] = inv.get(ch, 0) + 1
for ch, c in sorted(inv.items(), key=lambda kv: -kv[1]):
    print(f"  x{c:<5} U+{ord(ch):04X}  {ch!r}  {unicodedata.name(ch,'<none>')}")
cjk = [ch for ch in inv if 0x4E00 <= ord(ch) <= 0x9FFF]
pua = [ch for ch in inv if 0xE000 <= ord(ch) <= 0xF8FF]
print(f"  CJK ideographs: {len(cjk)}   PUA: {len(pua)}")
repl = t.count('\ufffd')
print(f"  U+FFFD replacement chars: {repl}")

print("\n=== structure ===")
for pat, label in [
    (r'^## \d+\.', 'H2 sections'),
    (r'^### \d+\.\d+', 'H3 subsections'),
]:
    hs = [l for l in lines if re.match(pat, l)]
    print(f"  {label}: {len(hs)}")
    for h in hs:
        print(f"     {h}")

print("\n=== dataset counts ===")
print(f"  §2.1 table rows (| `...` | ...) : ")
sec2 = t.split('## 2.')[1].split('## 3.')[0] if '## 2.' in t else ''
rows2 = [l for l in sec2.split('\n') if l.startswith('| `')]
print(f"     {len(rows2)}")
upsec = re.findall(r'^### `(up-[a-z0-9-]+)`', t, re.M)
print(f"  up-* '### `up-...`' sections: {len(set(upsec))} (distinct)")
allup = re.findall(r'`(up-[a-z0-9-]+)`', t)
print(f"  distinct up-* names anywhere: {len(set(allup))}")
allsn = re.findall(r'`(sn-[a-z0-9-]+)`', t)
print(f"  distinct sn-* names anywhere: {len(set(allsn))}")
sec4 = re.findall(r'^#### `([^`]+)`', t, re.M)
print(f"  §4.2 '#### ' parameter entries: {len(sec4)}")
print(f"  total '|'-leading rows: {len([l for l in lines if l.startswith('|')])}")

print("\n=== spot checks ===")
for n in [1, 85, 114, 138, 227, 240, 259, 8601, 8756, 8760, 9630]:
    print(f"  L{n}: {lines[n-1][:150]}")
