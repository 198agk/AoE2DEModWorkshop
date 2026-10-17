import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = 'D:/Software/DeepSeek Harness/工作区2/_probe/xs_ai_research/AI_SCRIPTING_AIREF.md'
lines = io.open(P, encoding='utf-8', newline='').read().split('\n')

def at(p, after=0):
    for i in range(after, len(lines)):
        if lines[i].startswith(p):
            return i
    return len(lines)

d = at('### 7.7'); e = at('## 8.', d)
# keep every line inside the fenced code block, no filtering by '#'/'`'
seg = lines[d:e]
inblk, toks = False, []
for l in seg:
    if l.startswith('```'):
        inblk = not inblk
        continue
    if inblk:
        toks += [t for t in l.split() if t]
toks = [t for t in toks if t != '---']
print(f"§7.7 tokens (code block only): {len(toks)}  distinct: {len(set(toks))}")

a2 = at('### 2.1'); b2 = at('## 3.', a2)
sec2 = [re.match(r'\| `([^`]+)`', l).group(1) for l in lines[a2:b2] if re.match(r'\| `([^`]+)`', l)]
print(f"§2.1 names: {len(sec2)}")
print(f"SETS EQUAL: {set(toks) == set(sec2)}")
print(f"  7.7 only: {sorted(set(toks)-set(sec2))}")
print(f"  2.1 only: {sorted(set(sec2)-set(toks))}")
