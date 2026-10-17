import io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))
t = io.open(os.path.join(D, 'AI_SCRIPTING_AIREF.md'), encoding='utf-8', newline='').read()
lines = t.split('\n')

def sect(start, end):
    a = next(i for i, l in enumerate(lines) if l.startswith(start))
    if end is None:
        return lines[a:]
    b = next(i for i, l in enumerate(lines) if i > a and l.startswith(end))
    return lines[a:b]

s21 = sect('### 2.1', '## 3.')
rows = [l for l in s21 if l.startswith('|')]
print(f"§2.1 total '|' rows: {len(rows)}  (minus header+separator = {len(rows)-2} commands)")

s41 = sect('### 4.1', '### 4.2')
r41 = [l for l in s41 if l.startswith('|')]
print(f"§4.1 total '|' rows: {len(r41)}  (minus header+separator = {len(r41)-2} parameters)")

s51 = sect('### 5.1', '## 6.')
r51 = [l for l in s51 if l.startswith('|')]
print(f"§5.1 total '|' rows: {len(r51)}  (minus header+separator = {len(r51)-2} SNs)")

s74 = sect('### 7.4', '### 7.5')
r74 = [l for l in s74 if l.startswith('|')]
print(f"§7.4 total '|' rows: {len(r74)}")

s77 = sect('### 7.7', '## 8.')
names = re.findall(r'`([a-z0-9#-]+)`', '\n'.join(s77))
print(f"§7.7 command names listed: {len(set(names))}")

print("\n=== §8 tables ===")
s8 = sect('## 8.', None)
print(f"§8 '|' rows: {len([l for l in s8 if l.startswith('|')])}")
print(f"§8 '#### ' group headings: {len([l for l in s8 if l.startswith('####')])}")

print("\n=== final byte/size ===")
P = os.path.join(D, 'AI_SCRIPTING_AIREF.md')
print(f"  bytes={os.path.getsize(P)} chars={len(t)} lines={len(lines)}")

print("\n=== the 5 recovered digit sites ===")
for n in [227, 240, 259]:
    print(f"  L{n}: {lines[n-1][:230]}")
