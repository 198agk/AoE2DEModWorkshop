import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

BAK = 'AI_SCRIPTING_AIREF.corrupt.bak.md'
s = io.open(BAK, encoding='utf-8', newline='').read()
lines = s.split('\n')

def show(n, label=''):
    t = lines[n - 1]
    vis = ''.join(c if ord(c) < 128 else '[U+%04X]' % ord(c) for c in t)
    print('BAK L%d %s\n    %s' % (n, label, vis))

for n in (85, 114, 138, 227, 240, 259, 8760):
    show(n)

print('\n===== source: xor/xnor description in commands.js =====')
js = io.open('raw_commands.js', encoding='utf-8', newline='').read()
for m in re.finditer(r'.{0,300}xnor.{0,700}', js):
    print(m.group(0)[:1000]); print('-----'); break
