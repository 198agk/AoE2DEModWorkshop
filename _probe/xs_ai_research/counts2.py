import io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = 'D:/Software/DeepSeek Harness/工作区2/_probe/xs_ai_research/AI_SCRIPTING_AIREF.md'
t = io.open(P, encoding='utf-8', newline='').read()
lines = t.split('\n')

def idx(pred, after=0):
    for i in range(after, len(lines)):
        if pred(lines[i]):
            return i
    return len(lines)

a = idx(lambda l: l.startswith('## 5.'))
b = idx(lambda l: l.startswith('### 5.1'), a)
c = idx(lambda l: l.startswith('## 6.'), b)
snrows = [l for l in lines[a:b] if l.startswith('|')]
print(f"SN table '|' rows: {len(snrows)} -> {len(snrows)-2} SNs")
snsec = [l for l in lines[b:c] if l.startswith('|')]
print(f"§5.1 description rows: {len(snsec)}")

d = idx(lambda l: l.startswith('### 7.7'))
e = idx(lambda l: l.startswith('## 8.'), d)
s77 = '\n'.join(lines[d:e])
names = re.findall(r'`([a-z0-9#_-]+)`', s77)
print(f"§7.7 names: {len(names)} occurrences, {len(set(names))} distinct")
print("   first 5:", names[:5])
print("   last 5:", names[-5:])
