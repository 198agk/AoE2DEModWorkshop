import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

def miscorrupt(s):
    """Exact .NET cp936 model: invalid pair -> '?' and consume 2 bytes."""
    b = s.encode('utf-8'); out = []; i = 0; n = len(b)
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

tests = [
 ('L227', '(313\u2013511 carry no engine behaviour',
          '(313\u9225?11 carry no engine behaviour'),
 ('L240a', 'goals **1\u201340 cannot be used',
           'goals **1\u9225?0 cannot be used'),
 ('L240b', 'avoid goals 511\u2013512 for point goals',
           'avoid goals 511\u9225?12 for point goals'),
 ('L240c', 'and 509\u2013512 for the four-goal commands',
           'and 509\u9225?12 for the four-goal commands'),
 ('L259', 'Strip to **0\u20131,222 chars**',
          'Strip to **0\u9225?,222 chars**'),
]
print("=== candidate originals re-corrupted: must MATCH the backup ===")
for tag, orig, want in tests:
    got = miscorrupt(orig)
    print(f"  {'MATCH ' if got == want else 'DIFFER'} {tag}: {orig!r}")
    if got != want:
        print(f"          want={want!r}\n          got ={got!r}")

print("\n=== does the CURRENT (wrong) text re-corrupt to the backup? ===")
wrong = [
 ('L227', '(313\u201311 carry no engine behaviour'),
 ('L240a', 'goals **1\u20130 cannot be used'),
 ('L240b', 'avoid goals 511\u201312 for point goals'),
 ('L240c', 'and 509\u201312 for the four-goal commands'),
 ('L259', 'Strip to **0\u2013,222 chars**'),
]
for tag, txt in wrong:
    print(f"  {tag}: {miscorrupt(txt)!r}")
