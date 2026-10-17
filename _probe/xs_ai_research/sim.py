import sys, io, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

def sim(s, enc='gbk', err='replace'):
    return s.encode('utf-8').decode(enc, err)

# KNOWN originals (pre-corruption) and their observed corrupt forms
cases = [
    ('L1',   '# AoE2 DE AI Scripting \u2014 AIREF Reference Extract',
             '# AoE2 DE AI Scripting \u9225?AIREF Reference Extract'),
    ('L72',  '### 1.1 File roles \u2014 and an honesty note',
             '### 1.1 File roles \u9225?and an honesty note'),
    ('L85',  "or an extension\u2014 the interpreter adds them",
             'or an extension\u9225?the interpreter adds them'),
    ('L100', '| `(defrule \u2026 ` |',
             '| `(defrule \u9225?` |'),
]
print("=== round-trip fidelity test: does .encode('utf-8').decode('gbk','replace') reproduce the corrupt form? ===")
for tag, orig, corrupt in cases:
    got = sim(orig)
    print(f"{tag}: {'MATCH  ' if got == corrupt else 'DIFFER '}")
    print(f"     orig   ={orig!r}")
    print(f"     expect ={corrupt!r}")
    print(f"     got    ={got!r}")

print()
print("=== which third-byte chars are distinguishable? ===")
for name, ch in [('em dash','\u2014'), ('en dash','\u2013'), ('ellipsis','\u2026'), ('right arrow','\u2192'), ('left-right arrow','\u2194'), ('less-equal','\u2264')]:
    for nxt in [' ', 't', 'A', '`', '"', ',', '1', 'o', 's']:
        s = 'X' + ch + nxt
        r = sim(s)
        if '?' in r:
            print(f"  {name:18} + {nxt!r:5} -> {r!r}")
