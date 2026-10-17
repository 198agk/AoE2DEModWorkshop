import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# VERIFY the campaign index table: for every member of every campaign, the prologue's
# (span, offset) pair + filename must match the physically scanned span/offset.
import os, sys, io, zlib, glob, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = _HERE_PATH("_probe", "survey_scenario")
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

p('=== PROLOGUE INDEX FORMAT (verified on xcam1) ===')
b = open(os.path.join(CAMP, 'xcam1.aoe2campaign'), 'rb').read()
ms = members(b)
pro = b[:ms[0][0]]
i = pro.find(b'.aoe2scenario')
p('  prologue length %d B ; first filename ends at %d' % (len(pro), i + 13))
start = i - 3 - 24                      # 4-byte len prefix + name
p('  raw bytes around the first index entry:')
p('   %s' % pro[start:start + 96].hex(' '))
entry0 = struct.unpack_from('<II', pro, start - 8)
p('  u32 pair immediately BEFORE the filename: %s -> span=%d offset=%d' % (entry0, entry0[0], entry0[1]))
p('  physically scanned member 0: span=%d offset=%d' % (ms[0][2], ms[0][0]))
p('  => match: %s' % (entry0 == (ms[0][2], ms[0][0])))

p('\n=== INDEX vs PHYSICAL SCAN, ALL 42 CAMPAIGNS / ALL 229 MEMBERS ===')
tot = okc = 0
anom = []
for f in sorted(glob.glob(os.path.join(CAMP, '*.aoe2campaign'))):
    b = open(f, 'rb').read(); ms = members(b)
    pro = b[:ms[0][0]]
    # collect entries: scan for '<span u32><offset u32>' immediately followed by a filename pair
    entries = []
    for m in ms:
        key = struct.pack('<II', m[2], m[0])
        j = pro.find(key)
        if j != -1:
            L = struct.unpack_from('<I', pro, j + 8)[0]
            nm2 = pro[j + 12:j + 12 + L] if 4 < L < 80 else b''
            if nm2.endswith(b'.aoe2scenario'):
                entries.append((j, m[2], m[0], nm2.decode()))
    names = b'.aoe2scenario'
    n_ok = len(entries)
    tot += len(ms); okc += n_ok
    if n_ok != len(ms):
        anom.append((os.path.basename(f), len(ms), n_ok))
    p('  %-28s members=%-3d indexed=%-3d prologue=%-7d tail=%-7d %s' % (
        os.path.basename(f), len(ms), n_ok, ms[0][0],
        len(b) - (ms[0][0] + sum(m[2] for m in ms)),
        'OK' if n_ok == len(ms) else 'MISMATCH ' + str([m[2] for m in ms]) + ' vs ' + str([e[1] for e in entries])))
p('\n  index entries matched to physical members: %d / %d' % (okc, tot))
p('  campaigns with index/physical mismatches: %s' % anom)

p('\n=== anomaly detail ===')
for nm in ('coop3', 'coop6', 'kcam1'):
    b = open(os.path.join(CAMP, nm + '.aoe2campaign'), 'rb').read()
    ms = members(b)
    pro_len = ms[0][0]
    p('  %s: prologue %d B' % (nm, pro_len))
    # does the prologue itself contain a deflate stream?
    hits = []
    for o in range(0, min(pro_len, 4096)):
        d = zlib.decompressobj(-15)
        try: out = d.decompress(b[o:])
        except Exception: continue
        if d.eof and len(out) > 5000: hits.append((o, len(out)))
    p('     deflate streams starting inside prologue[:4096]: %s' % hits[:5])
    tail = b[pro_len + sum(m[2] for m in ms):]
    p('     tail after last member: %d B, head %r' % (len(tail), tail[:48]))

open(os.path.join(HERE, 'campaign_index_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign_index_out.txt')
