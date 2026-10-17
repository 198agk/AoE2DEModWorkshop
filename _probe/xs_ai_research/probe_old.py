import io, os, unicodedata

D = os.path.dirname(os.path.abspath(__file__))
BAD = [0x9225, 0x922B, 0x922E, 0xE6C6, 0xE6D5, 0x6402, 0x947E, 0x7D66]

def load(n):
    p = os.path.join(D, n)
    if not os.path.exists(p):
        return None
    return io.open(p, encoding='utf-8', errors='replace', newline='').read()

def scan(name, txt):
    if txt is None:
        print(f"--- {name}: MISSING")
        return None
    counts = {}
    for ch in txt:
        if ch in '?\n':
            continue
        o = ord(ch)
        if o in BAD or (0x4E00 <= o <= 0x9FFF) or (0xE000 <= o <= 0xF8FF):
            counts[o] = counts.get(o, 0) + 1
    q = txt.count('?')
    print(f"--- {name}: chars={len(txt)} lines={txt.count(chr(10))+1} '?'={q} suspicious={sum(counts.values())}")
    for o, c in sorted(counts.items(), key=lambda kv: -kv[1])[:12]:
        print(f"      x{c:<5} U+{o:04X} {unicodedata.name(chr(o),'?')}")
    return counts

for n in ['_reverse_dryrun.md', 'guide_part1.md', 'guide_part2.md', '_section8.md',
          'AI_SCRIPTING_AIREF.corrupt.bak.md']:
    scan(n, load(n))
