import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

def miscorrupt(s):
    """Mimic .NET cp936 decoding of UTF-8 bytes: on invalid pair emit '?' and consume 2."""
    b = s.encode('utf-8')
    out = []
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if c < 0x80:
            out.append(chr(c)); i += 1; continue
        if i + 1 < n and 0x81 <= c <= 0xFE:
            t = b[i+1]
            if (0x40 <= t <= 0x7E) or (0x80 <= t <= 0xFE):
                try:
                    out.append(bytes([c, t]).decode('gbk')); i += 2; continue
                except UnicodeDecodeError:
                    pass
        out.append('?'); i += 2
    return ''.join(out)

def rd(n):
    return io.open(os.path.join(D, n), encoding='utf-8', newline='').read()

# sanity: reproduce the four known-good corruptions
SANE = [
 ('# AoE2 DE AI Scripting \u2014 AIREF Reference Extract',
  '# AoE2 DE AI Scripting \u9225?AIREF Reference Extract'),
 ('or an extension\u2014 the interpreter adds them',
  'or an extension\u9225?the interpreter adds them'),
 ("in UP\u2014 'Elements'", "in UP\u9225?'Elements'"),
 ('| `(defrule \u2026 ` |', '| `(defrule \u9225?` |'),
 ('(313\u2013511 carry no', '(313\u9225?11 carry no'),
 ('Strip to **0\u20131,222 chars**', 'Strip to **0\u9225?,222 chars**'),
]
print("=== decoder fidelity (must all be MATCH) ===")
ok = True
for o, want in SANE:
    got = miscorrupt(o)
    m = got == want
    ok &= m
    print(f"  {'MATCH ' if m else 'DIFFER'}  {o!r}")
    if not m:
        print(f"          want={want!r}\n          got ={got!r}")
print("ALL OK" if ok else "*** MODEL WRONG ***")

cur = rd('AI_SCRIPTING_AIREF.md').split('\n')
bak = rd('AI_SCRIPTING_AIREF.corrupt.bak.md').split('\n')
print(f"\nlines: cur={len(cur)} bak={len(bak)}")

print("\n=== literal '?' counts ===")
print(f"  backup total '?' = {sum(l.count('?') for l in bak)}")
print(f"  current total '?' = {sum(l.count('?') for l in cur)}")

mism = []
for i in range(min(len(cur), len(bak))):
    # guard against an accidental original '?' in current text
    if cur[i] == bak[i]:
        continue
    if miscorrupt(cur[i]) != bak[i]:
        mism.append(i)
print(f"\n=== re-corruption mismatches: {len(mism)} ===")
for i in mism:
    print(f"\nL{i+1}")
    print(f"  BAK: {bak[i]!r}")
    print(f"  CUR: {cur[i]!r}")
    print(f"  SIM: {miscorrupt(cur[i])!r}")
