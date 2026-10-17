import io, os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

SRC = os.path.join(D, 'AI_SCRIPTING_AIREF.md')
BAK2 = os.path.join(D, 'AI_SCRIPTING_AIREF.pre_digitfix.bak.md')

EN = '\u2013'   # en dash

FIXES = [
    # (line_no, old, new, reason)
    (227, f'(313{EN}11 carry no engine behaviour',
          f'(313{EN}511 carry no engine behaviour',
          'digit-lossy: 511 upper bound eaten (Data Limits: SNs 313-511)'),
    (240, f'goals **1{EN}0 cannot be used',
          f'goals **1{EN}40 cannot be used',
          'digit-lossy: 40 upper bound eaten (Data Limits: goals 1-40)'),
    (240, f'avoid goals 511{EN}12 for point goals',
          f'avoid goals 511{EN}512 for point goals',
          'digit-lossy: 512 upper bound eaten (UserPatch: goals 511 & 512)'),
    (240, f'and 509{EN}12 for the four-goal commands',
          f'and 509{EN}512 for the four-goal commands',
          'digit-lossy: 512 upper bound eaten (UserPatch: goals 509-512)'),
    (259, f'Strip to **0{EN},222 chars**',
          f'Strip to **0{EN}3,222 chars**',
          'digit-lossy: hundreds digit eaten; txt_objects.txt measures 3222 chars'),
]

txt = io.open(SRC, encoding='utf-8', newline='').read()
lines = txt.split('\n')

if not os.path.exists(BAK2):
    shutil.copyfile(SRC, BAK2)
    print(f'backup written: {os.path.basename(BAK2)}')

applied = 0
for ln, old, new, reason in FIXES:
    i = ln - 1
    if old in lines[i]:
        lines[i] = lines[i].replace(old, new, 1)
        applied += 1
        print(f'  L{ln}: OK   {reason}')
    elif new in lines[i]:
        print(f'  L{ln}: already fixed')
    else:
        print(f'  L{ln}: *** TARGET NOT FOUND ***')
        print(f'         line = {lines[i]!r}')

print(f'\napplied={applied}')
out = '\n'.join(lines)
io.open(SRC, 'w', encoding='utf-8', newline='').write(out)
print(f'chars={len(out)} lines={len(lines)}')

# sanity: show every remaining literal '?'
print("\n=== all remaining literal '?' occurrences ===")
for n, l in enumerate(out.split('\n'), 1):
    if '?' in l:
        for k, ch in enumerate(l):
            if ch == '?':
                print(f"  L{n}: ...{l[max(0,k-70):k+40]}...")
