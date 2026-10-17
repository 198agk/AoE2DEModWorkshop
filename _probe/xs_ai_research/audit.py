import io, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')

cur = io.open('AI_SCRIPTING_AIREF.md', encoding='utf-8', newline='').read()
bak = io.open('AI_SCRIPTING_AIREF.corrupt.bak.md', encoding='utf-8', newline='').read()

# 1. every em dash in current file: is it " X Y " spaced on the left?
clines = cur.split('\n')
print('=== em dashes lacking a space BEFORE (need review) ===')
n = 0
for i, t in enumerate(clines):
    for m in re.finditer(r'(.{22})\u2014(.{22})', t):
        left = m.group(1)
        if not left.endswith(' '):
            n += 1
            print('L%-5d ...%s---> %r' % (i + 1, left[-14:], t[max(0, m.start() + 22 - 6):m.start() + 22 + 30]))
print('count=%d' % n)

# 2. all U+9225 '?' sites in backup, classified by the char before
print('\n=== backup U+9225 + "?" sites: char before / char after ===')
bl = bak.split('\n')
pat = re.compile(r'.(\u9225)\?(.)')
kinds = collections.Counter()
sites = []
for i, t in enumerate(bl):
    for m in re.finditer(r'.(\u9225)\?(.)', t):
        prev, nxt = m.group(1), m.group(2)
        sites.append((i + 1, prev, nxt, t))
        k = ('SP' if prev == ' ' else ('AL' if prev.isalnum() else prev),
             'SP' if nxt == ' ' else ('AL' if nxt.isalnum() else nxt))
        kinds[k] += 1
for k, v in kinds.most_common():
    print('   prev=%-4s next=%-4s  x%d' % (k[0], k[1], v))
print('total sites=%d' % len(sites))

print('\n=== sites where prev is NOT a space (ambiguous: em dash vs ellipsis) ===')
for ln, prev, nxt, t in sites:
    if prev != ' ':
        j = t.index('\u9225')
        print('L%-5d prev=%r next=%r | ...%s...' % (ln, prev, nxt, t[max(0, j - 40):j + 40]))
