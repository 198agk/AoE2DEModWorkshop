# Campaign container structure, fixed scan (+h bug), gap analysis, and in-place member swap test.
import os, sys, io, json, zlib, glob, contextlib, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore'); import logging; logging.disable(logging.CRITICAL)

CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario'
buf = io.StringIO()
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); buf.write(s + '\n')

def scan(b, off):
    """smallest header length h such that b[off+h:] is a deflate stream with eof and >1000 B out"""
    for h in range(24, 400):
        d = zlib.decompressobj(-15)
        try:
            out = d.decompress(b[off + h:])
        except Exception:
            continue
        if d.eof and len(out) > 1000:
            consumed = len(b) - (off + h) - len(d.unused_data)
            return h, consumed, len(out)
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
        off, (h, consumed, inflated) = found
        res.append((off, h, h + consumed, inflated, b[off:off+4].decode()))
        pos = off + h + consumed
    return res

p('=== campaign member scan (all 42) ===')
p('%-30s %9s %4s %10s %9s %s' % ('campaign', 'size', 'nmem', 'covered', 'tail', 'members [off/hdr/span/ver]'))
ALL = {}
total_tail = 0
for f in sorted(glob.glob(os.path.join(CAMP, '*.aoe2campaign'))):
    b = open(f, 'rb').read()
    ms = members(b)
    ALL[os.path.basename(f)] = (len(b), ms)
    covered = sum(m[2] for m in ms)
    tail = len(b) - (ms[0][0] + covered) if ms else len(b)
    total_tail += tail
    s = ' '.join('%d/%d/%d/%s' % (m[0], m[1], m[2], m[4]) for m in ms[:3])
    p('%-30s %9d %4d %10d %9d %s%s' % (os.path.basename(f), len(b), len(ms), covered, tail, s, ' ...' if len(ms) > 3 else ''))
p('\ntotal bytes outside scenario spans (prefix + gaps + tail): %d' % total_tail)

# ---- gap bytes between members of xcam1 ----
p('\n=== bytes BETWEEN members (xcam1) ===')
b = open(os.path.join(CAMP, 'xcam1.aoe2campaign'), 'rb').read()
ms = members(b)
p('  file %d B, %d members' % (len(b), len(ms)))
prev_end = 0
for k, m in enumerate(ms):
    gap = b[prev_end:m[0]]
    p('  member %d @%d hdr=%d span=%d ver=%s inflated=%d ; gap before = %d B' % (k, m[0], m[1], m[2], m[4], m[3], len(gap)))
    if gap:
        p('     gap hex  %s' % gap[:96].hex(' '))
        p('     gap asc  %r' % gap[:96])
    prev_end = m[0] + m[2]
tail = b[prev_end:]
p('  tail after last member = %d B ; hex %s ; asc %r' % (len(tail), tail[:64].hex(' '), tail[:64]))
p('  first 128 B of file: hex %s' % b[:128].hex(' '))
p('  first 128 B of file: asc %r' % b[:128])

# ---- in-place swap test ----
p('\n=== in-place embedded-member swap test (xcam1 member 0) ===')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
off, h, span, infl, ver = ms[0]
orig_member = b[off:off + span]
p('  original member: offset %d header %d span %d (blob %d B) version %s' % (off, h, span, span - h, ver))
# rebuild original member as standalone via ASP and compare
mem_path = os.path.join(HERE, 'roundtrip', 'camp_member0.orig.aoe2scenario')
open(mem_path, 'wb').write(orig_member)
with contextlib.redirect_stdout(io.StringIO()):
    sc = AoE2DEScenario.from_file(mem_path)
n0 = len(sc.trigger_manager.triggers)
with contextlib.redirect_stdout(io.StringIO()):
    sc.trigger_manager.add_trigger('PROBE ADDED TRIGGER')
mod_path = os.path.join(HERE, 'roundtrip', 'camp_member0.mod.aoe2scenario')
with contextlib.redirect_stdout(io.StringIO()):
    sc.write_to_file(mod_path)
mod = open(mod_path, 'rb').read()
p('  modified member: %d B (delta %+d) triggers %d -> %d' % (len(mod), len(mod) - span, n0, n0 + 1))
p('  fits in original span: %s' % (len(mod) <= span))
if len(mod) <= span:
    for padname, pad in (('zero', b'\x00' * (span - len(mod))),):
        cand = b[:off] + mod + pad + b[off + span:]
        cpath = os.path.join(HERE, 'roundtrip', 'xcam1.padded.aoe2campaign')
        open(cpath, 'wb').write(cand)
        p('  wrote %s (%d B, original %d B, delta %+d)' % (os.path.basename(cpath), len(cand), len(b), len(cand) - len(b)))
        # re-parse candidate
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                cms = members(cand)
                p('  re-parse: %d members, member 0 span %d ver %s' % (len(cms), cms[0][2], cms[0][4]))
                m0 = cand[cms[0][0]:cms[0][0] + cms[0][2]]
                tpath = os.path.join(HERE, 'roundtrip', 'xcam1.padded.member0.aoe2scenario')
                open(tpath, 'wb').write(m0)
                sc3 = AoE2DEScenario.from_file(tpath)
                names = [t.name for t in sc3.trigger_manager.triggers]
                p('  re-read member 0: triggers %d ; last = %r ; PROBE present = %s' % (
                    len(names), names[-1] if names else None, 'PROBE ADDED TRIGGER' in names))
            except Exception as ex:
                p('  re-parse FAILED %s: %s' % (type(ex).__name__, str(ex)[:160]))

# ---- determinism: rebuild every member via ASP and compare byte sizes ----
p('\n=== ASP re-serialization of every embedded member of xcam1 ===')
hdr = open(os.path.join(HERE, 'roundtrip', 'xcam1.rebuilt.aoe2campaign'), 'wb')
out = bytearray(b[:ms[0][0]])
for k, (o, hh, sp, ifl, v) in enumerate(ms):
    mp = os.path.join(HERE, 'roundtrip', 'xcm_%d.aoe2scenario' % k)
    open(mp, 'wb').write(b[o:o + sp])
    with contextlib.redirect_stdout(io.StringIO()):
        s = AoE2DEScenario.from_file(mp)
    rp = os.path.join(HERE, 'roundtrip', 'xcm_%d.reser.aoe2scenario' % k)
    with contextlib.redirect_stdout(io.StringIO()):
        s.write_to_file(rp)
    rb = open(rp, 'rb').read()
    p('  member %d v%s: orig span %d -> reserialized %d (delta %+d) triggers %d' % (
        k, v, sp, len(rb), len(rb) - sp, len(s.trigger_manager.triggers)))
    out += rb
    # gap between this member and next
    nxt = ms[k + 1][0] if k + 1 < len(ms) else len(b)
    out += b[o + sp:nxt]
hdr.close()
open(os.path.join(HERE, 'roundtrip', 'xcam1.rebuilt.aoe2campaign'), 'wb').write(out)
p('  rebuilt file %d B vs original %d B (delta %+d)' % (len(out), len(b), len(out) - len(b)))

open(os.path.join(HERE, 'campaign2_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign2_out.txt')
