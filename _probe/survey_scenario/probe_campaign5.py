import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# Parse the campaign prologue index: per member it stores filename + (span, offset).
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
        try:
            out = d.decompress(b[off + h:])
        except Exception:
            continue
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
                if r:
                    found = (i, r); break
            i = b.find(b'1.', i + 1)
        if not found:
            break
        off, (h, c, inf) = found
        res.append((off, h, h + c, inf, b[off:off+4].decode()))
        pos = off + h + c
    return res

p('=== prologue index parse: does it hold (filename, span, offset) per member? ===')
p('%-24s %-5s %-10s %-10s %-7s %s' % ('campaign', 'mem', 'span@idx', 'offset@idx', 'span_ok', 'filename'))
for nm in ['xcam1', 'acam1', 'cam2', 'fcam7', 'dcam0', 'coop3', 'coop6', 'kcam1']:
    f = os.path.join(CAMP, nm + '.aoe2campaign')
    b = open(f, 'rb').read()
    ms = members(b)
    pro = b[:ms[0][0]]
    # filenames: str16 = u32 length + bytes, value appears twice
    names, i = [], 0
    while i < len(pro) - 4:
        L = struct.unpack_from('<I', pro, i)[0]
        if 4 < L < 80 and i + 4 + L <= len(pro):
            s = pro[i+4:i+4+L]
            if s.endswith(b'.aoe2scenario') and all(32 <= c < 127 for c in s):
                names.append((i, s.decode()))
                i += 4 + L
                continue
        i += 1
    ok = 0
    for k, (o, h, sp, inf, v) in enumerate(ms[:6]):
        # find the k-th distinct filename entry (each name appears twice in a row)
        span_ok = '-'; idx = '-'
        if k < len(names):
            start = names[k][0]
            j = pro.find(names[k][1].encode(), start)          # 2nd copy
            if j != -1:
                t = j + len(names[k][1])
                if t + 8 <= len(pro):
                    s1, s2 = struct.unpack_from('<II', pro, t)
                    idx, span_ok = '%d/%d' % (s1, s2), (s1 == sp and s2 == o)
                    if span_ok: ok += 1
        p('%-24s %-5d %-10s %-10s %-7s %s' % (nm, k, sp, o, span_ok, names[k][1] if k < len(names) else '?'))
    p('   -> %d/%d members had exact (span,offset) index entries' % (ok, min(len(ms), 6)))
    p('   -> prologue %d B, %d member files, %d name entries' % (len(pro), len(ms), len(names)))

p('\n=== anomaly campaigns (large prologue) ===')
for nm in ['coop3', 'coop6', 'kcam1']:
    b = open(os.path.join(CAMP, nm + '.aoe2campaign'), 'rb').read()
    ms = members(b)
    p('  %s: %d B, %d members, prologue %d, tail %d' % (nm, len(b), len(ms), ms[0][0], len(b) - (ms[0][0] + sum(m[2] for m in ms))))
    p('    first 96 B: hex %s' % b[:96].hex(' '))
    p('    first 96 B: asc %r' % b[:96])
    p('    member offsets: %s' % [m[0] for m in ms])
    if nm == 'kcam1':
        tail = b[ms[-1][0] + ms[-1][2]:]
        p('    tail %d B: hex %s' % (len(tail), tail[:64].hex(' ')))
        p('    tail asc %r' % tail[:64])

open(os.path.join(HERE, 'campaign4_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign4_out.txt')
