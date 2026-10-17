import io, re, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

SRC = 'AI_SCRIPTING_AIREF.md'
BAK = 'AI_SCRIPTING_AIREF.corrupt.bak.md'
if not shutil.os.path.exists(BAK):
    shutil.copyfile(SRC, BAK)
    print('backup written: ' + BAK)

s = io.open(SRC, encoding='utf-8', newline='').read()

EM = '\u2014'   # —
EN = '\u2013'   # –
EL = '\u2026'   # …
SEC = '\u00a7'  # §
RA = '\u2192'   # →
LR = '\u2194'   # ↔
LE = '\u2264'   # ≤
CED = '\u00e7'  # ç

log = []
def rep(i, n, new, why):
    global s
    log.append((cur_line_no(i), why, s[max(0, i - 45):i + n + 35], new))
    s = s[:i] + new + s[i + n:]

cur_line_no = lambda i: s.count('\n', 0, i) + 1

# ---- pass 1: PUA pairs (U+9225 + PUA) derived from GBK byte pairs ----
out = []
i = 0
while i < len(s):
    c = s[i]
    if c == '\u9225' and i + 1 < len(s) and s[i + 1] == '\ue6c6':
        rep(i, 2, EL + '`', 'U+9225+U+E6C6 = E2 80 A6 + 60 = ellipsis + backtick')
        i += 2
    elif c == '\u9225' and i + 1 < len(s) and s[i + 1] == '\ue6d5':
        rep(i, 2, EL + 'o', 'U+9225+U+E6D5 = E2 80 A6 + 6F = ellipsis + o')
        i += 2
    else:
        i += 1

# ---- pass 2: U+9225 followed by '?' ----
i = 0
while i < len(s) - 1:
    if s[i] == '\u9225' and s[i + 1] == '?':
        prev = s[i - 1] if i > 0 else ''
        after = s[i + 2] if i + 2 < len(s) else ''
        if prev.isdigit() and (after.isdigit() or after == ','):
            rep(i, 2, EN, 'digit-digit -> en dash')
        else:
            rep(i, 2, EM + ' ', 'space consumed -> em dash + space')
        i += 0
        continue
    i += 1

# ---- pass 3: ellipsis sites where the third byte merged with a following ASCII char ----
# (already handled for the PUA pairs; remaining U+9225 + ASCII are em/en dash cases)

# ---- pass 4: arrows, <=, section sign, cedilla ----
i = 0
while i < len(s) - 1:
    if s[i] == '\u922b' and s[i + 1] == '?':
        nxt = s[i + 2] if i + 2 < len(s) else ''
        new = LR + ' ' if nxt == 'X' else RA + ' '
        rep(i, 2, new, 'arrow ' + ('<->' if nxt == 'X' else '->'))
        continue
    i += 1
i = 0
while i < len(s) - 1:
    if s[i] == '\u922e' and s[i + 1] == '?':
        rep(i, 2, LE + ' ', '<=  (U+2264 + space)')
        continue
    i += 1
i = 0
while i < len(s):
    if s[i] == '\u6402':
        rep(i, 1, SEC, 'section sign (C2 A7)')
        continue
    i += 1
i = 0
while i < len(s) - 1:
    if s[i] == '\u947e' and s[i + 1] == '\u7d66':
        rep(i, 2, CED + 'o', 'cedilla + consumed o  (Alencon)')
        continue
    i += 1

io.open(SRC, 'w', encoding='utf-8', newline='').write(s)
print('replacements applied: %d' % len(log))
with io.open('_fixlog.txt', 'w', encoding='utf-8', newline='') as f:
    for ln, why, ctx, new in log:
        f.write('%s  %-42s  -> %r\n    ...%s...\n' % (ln, why, new, ctx))

# ---- verify ----
bad = {}
for m in re.finditer(r'[^\x00-\x7F]+', s):
    bad[m.group(0)] = bad.get(m.group(0), 0) + 1
print('remaining distinct non-ASCII runs: %d' % len(bad))
for k, v in sorted(bad.items(), key=lambda kv: -kv[1]):
    print('   x%-5d %s' % (v, ' '.join('U+%04X' % ord(c) for c in k)))
print('total non-ASCII runs: %d' % sum(bad.values()))
print('chars=%d lines=%d' % (len(s), s.count('\n') + 1))
