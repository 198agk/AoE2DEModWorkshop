import io, sys, re
sys.stdout.reconfigure(encoding='utf-8')

# --- (a) ground truth: how did "Alencon" get corrupted? ---
raw = open('raw_commands.js', 'rb').read()
i = raw.find(b'Alen')
print('raw_commands.js Alen context hex:', raw[i-6:i+16].hex(' '))
print('  as utf-8 :', raw[i-6:i+16].decode('utf-8', 'replace'))
print('  as cp936 :', raw[i-6:i+16].decode('cp936', 'replace'))

# --- (b) does cp936 round-trip the em dash? ---
for ch in ['\u2014', '\u2013', '\u2026', '\u00a7', '\u2192', '\u2194', '\u2264', '\u00e7']:
    b = ch.encode('utf-8')
    bad = b.decode('cp936', 'replace')
    print('U+%04X %r -> utf8 %s -> cp936 %r  cps=%s' % (ord(ch), ch, b.hex(' '), bad,
          ' '.join('U+%04X' % ord(c) for c in bad)))

# --- (c) dry-run reverse on the deliverable ---
s = io.open('AI_SCRIPTING_AIREF.md', encoding='utf-8').read()
print('\n--- deliverable distinct non-ascii runs ---')
runs = {}
for m in re.finditer(r'[^\x00-\x7F]+', s):
    runs[m.group(0)] = runs.get(m.group(0), 0) + 1
for r, c in sorted(runs.items(), key=lambda kv: -kv[1]):
    print('  x%-4d %s' % (c, ' '.join('U+%04X' % ord(ch) for ch in r)))

PUA = {'\ue6c6': b'\xa6\x60', '\ue6d5': b'\xa6\x6f'}
out = bytearray()
for ch in s:
    if ch in PUA:
        out += PUA[ch]
        continue
    if ord(ch) < 128:
        out += ch.encode('ascii')
        continue
    try:
        out += ch.encode('cp936')
    except Exception as e:
        out += b'?'
        print('ENCODE FAIL U+%04X %r: %s' % (ord(ch), ch, e))
back = bytes(out).decode('utf-8', 'replace')
n_fffd = back.count('\ufffd')
print('\nreverse pass: replacement chars = %d' % n_fffd)
for m in re.finditer(r'.{0,50}\ufffd+.{0,30}', back):
    print('   LOSSY: %r' % m.group(0))
io.open('_reverse_dryrun.md', 'w', encoding='utf-8', newline='').write(back)
print('wrote _reverse_dryrun.md, chars=%d' % len(back))
