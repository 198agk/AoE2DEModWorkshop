import io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
P = 'D:/Software/DeepSeek Harness/工作区2/_probe/xs_ai_research/AI_SCRIPTING_AIREF.md'
lines = io.open(P, encoding='utf-8', newline='').read().split('\n')

def at(p, after=0):
    for i in range(after, len(lines)):
        if lines[i].startswith(p):
            return i
    return len(lines)

a = at('## 5.'); b = at('### 5.1', a); c = at('## 6.', b)
d = at('### 7.7'); e = at('## 8.', d)

print("=== §5.1 first 12 lines ===")
for l in lines[b:b+12]:
    print("   ", repr(l[:120]))
print("\n=== §7.7 first 12 lines ===")
for l in lines[d:d+12]:
    print("   ", repr(l[:120]))
print("\n=== §7.7 counts ===")
seg = lines[d:e]
print("   total lines:", len(seg))
print("   '-'-leading:", len([l for l in seg if l.startswith('-')]))
print("   '*'-leading:", len([l for l in seg if l.startswith('*')]))
print("   '|'-leading:", len([l for l in seg if l.startswith('|')]))
print("   '***'-leading:", len([l for l in seg if l.startswith('***')]))
print("\n=== §5.1 counts ===")
seg5 = lines[b:c]
print("   total lines:", len(seg5))
for pfx in ['-', '*', '|', '####', '**']:
    print(f"   {pfx!r}-leading:", len([l for l in seg5 if l.startswith(pfx)]))
