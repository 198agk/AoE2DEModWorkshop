# Decode the campaign prologue index *exactly*, resolve anomalies (coop3/coop6/kcam1),
# and verify the padded in-place member swap re-reads correctly.
import os, sys, io, zlib, glob, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario'
buf = io.StringIO()
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); buf.write(s + '\n')

def scan(b, off):
    for h in range(24, 400):
        d = zlib.decompressobj(-15)
        try: out = d.decompress(b[off + h:])
        except Exception: continue
        if d.eof and len(out) > 1000:
            return h, len(b) - (off + h) - len(d.unused_data), len(out)
    return None

def members(b):
    res, pos = [], 0
    while True:
        i = b.find(b'1.', pos); found = None
        while i != -1:
            if (i + 8 <= len(b) and b[i+1:i+2] == b'.' and b[i+2:i+4].isdigit()
                    and b[i+4:i+8] == b'\x00\x00\x00\x00'):
                r = scan(b, i)
                if r: found = (i, r); break
            i = b.find(b'1.', i + 1)
        if not found: break
        off, (h, c, inf) = found
        res.append((off, h, h + c, inf, b[off:off+4].decode()))
        pos = off + h + c
    return res

b = open(os.path.join(CAMP, 'xcam1.aoe2campaign'), 'rb').read()
ms = members(b) if False else None
pro = b[:676]
p('=== xcam1 prologue: word-aligned dump from offset 320 ===')
for o in range(320, min(676, 520), 4):
    w = struct.unpack_from('<I', pro, o)[0]
    asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in pro[o:o+4])
    p('  +%3d  %08x  %-11d  %r' % (o, w, w, asc))

p('\n=== xcam1 prologue tail (filenames + u32 pairs) decoded positionally ===')
o = pro.find(b'C1_Attila_1')
p('  first filename at +%d' % o)
p('  8 bytes BEFORE it: %s' % pro[o-8:o].hex(' '))
p('  4 bytes BEFORE it: %s  = u32 %d' % (pro[o-4:o].hex(' '), struct.unpack_from('<I', pro, o-4)[0]))
o2 = o + len(b'C1_Attila_1.aoe2scenario')
p('  bytes AFTER first filename: %s  (u32 %d)' % (pro[o2:o2+4].hex(' '), struct.unpack_from('<I', pro, o2)[0]))
p('  next 24 chars: %r' % pro[o2+4:o2+4+24])
o3 = o2 + 4 + 24
p('  bytes AFTER second filename: %s = (u32 %d, u32 %d)' % (
    pro[o3:o3+8].hex(' '), struct.unpack_from('<I', pro, o3)[0], struct.unpack_from('<I', pro, o3+4)[0]))
p('  member 0 physical: span=%d offset=%d' % (91684, 676))
p('  member 1 physical: span=%d offset=%d' % (121523, 92360))
p('  => interpretation: <u32 span><u32 offset> then the filename written TWICE,')
p('     the filename being length-prefixed by the u32 that PRECEDES the name (value = byte length).')
p('  check: u32 before first name = %d ; strlen = %d' % (
    struct.unpack_from('<I', pro, o-4)[0], len('C1_Attila_1.aoe2scenario')))

p('\n=== is the pre-filename u32 == strlen for every name? ===')
ok = bad = 0
i = 0
while True:
    j = pro.find(b'.aoe2scenario', i)
    if j == -1: break
    j += len(b'.aoe2scenario')
    k = j
    while k > 0 and 32 <= pro[k-1] < 127: k -= 1
    name = pro[k:j]
    L = struct.unpack_from('<I', pro, k-4)[0] if k >= 4 else -1
    good = (L == len(name))
    ok += good; bad += (not good)
    p('  %-30s declared_len=%-4d actual_len=%-4d %s' % (name.decode(), L, len(name), 'OK' if good else 'BAD'))
    i = j
p('  names with correct length prefix: %d ok / %d bad' % (ok, bad))

open(os.path.join(HERE, 'campaign_prologue_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign_prologue_out.txt')
