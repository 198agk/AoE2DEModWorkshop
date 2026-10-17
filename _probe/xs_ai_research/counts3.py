import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = _HERE_PATH("_probe", "xs_ai_research", "AI_SCRIPTING_AIREF.md")
lines = io.open(P, encoding='utf-8', newline='').read().split('\n')

def at(p, after=0):
    for i in range(after, len(lines)):
        if lines[i].startswith(p):
            return i
    return len(lines)

d = at('### 7.7'); e = at('## 8.', d)
block = [l for l in lines[d:e] if not l.startswith('#') and not l.startswith('`') and not l.startswith('###') and l.strip()]
names = []
for l in block:
    names += l.split()
names = [n for n in names if n and not n.startswith('`')]
print(f"§7.7 code-block tokens: {len(names)}  distinct: {len(set(names))}")

# compare to §2.1
a2 = at('### 2.1'); b2 = at('## 3.', a2)
rows = [l for l in lines[a2:b2] if l.startswith('| `')]
sec2 = []
for l in rows:
    m = re.match(r'\| `([^`]+)`', l)
    if m:
        sec2.append(m.group(1))
print(f"§2.1 command names: {len(sec2)}  distinct: {len(set(sec2))}")
print(f"§7.7 set == §2.1 set ? {set(names) == set(sec2)}")
d1 = set(names) - set(sec2)
d2 = set(sec2) - set(names)
print(f"  in 7.7 only: {sorted(d1)[:20]}")
print(f"  in 2.1 only: {sorted(d2)[:20]}")

# up-* sections
up = re.findall(r'^### `(up-[a-z0-9-]+)`', '\n'.join(lines), re.M)
print(f"\n§3 up-* '### ' sections: {len(up)}  distinct: {len(set(up))}")
p4 = re.findall(r'^#### `([^`]+)`', '\n'.join(lines), re.M)
print(f"§4.2 '#### ' entries: {len(p4)}  distinct: {len(set(p4))}")

print("\n=== §5.1 SN entry count ===")
b = at('### 5.1'); c = at('## 6.', b)
sn = [l for l in lines[b:c] if l.startswith('- **SN ')]
print(f"  SN bullets: {len(sn)}")
print(f"  first: {sn[0][:60]}")
print(f"  last : {sn[-1][:60]}")
