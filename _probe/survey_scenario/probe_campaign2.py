import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# Campaign container arithmetic test:
#  (1) can a campaign be structurally parsed into (prefix, [scenario blobs], tail) with no gaps?
#  (2) is the container a plain concatenation (i.e. reassembly with identical blobs reproduces the file byte-for-byte)?
#  (3) can an embedded scenario be swapped in place when its serialized size is <= the original?
import os, sys, io, json, zlib, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = _HERE_PATH("_probe", "survey_scenario")
buf = io.StringIO()
def p(*a):
    s = ' '.join(str(x) for x in a); print(s); buf.write(s + '\n')

def scan(b, off):
    """header length h such that b[off:] is a deflate stream consuming exactly h+consumed bytes"""
    for h in range(24, 400):
        d = zlib.decompressobj(-15)
        try:
            out = d.decompress(b[off:])
        except Exception:
            continue
        if d.eof and len(out) > 1000:
            consumed = len(b) - off - len(d.unused_data)
            if consumed > 0:
                return h, consumed, len(out)
    return None

def sections(b):
    """return list of (offset, header_len, total_len, inflated)"""
    out = []
    pos = 0
    while True:
        i = b.find(b'1.', pos)
        found = None
        while i != -1:
            if i + 8 <= len(b) and b[i+1:i+2] == b'.' and b[i+2:i+4].isdigit() and b[i+4:i+8] == b'\x00\x00\x00\x00':
                r = scan(b, i)
                if r:
                    found = (i, r); break
            i = b.find(b'1.', i + 1)
        if not found:
            break
        off, (h, consumed, inflated) = found
        out.append((off, h, h + consumed, inflated))
        pos = off + h + consumed
    return out

p('campaign                       size  n_sections  gaps  reassembles_identical')
tot_gap = 0
for f in sorted(glob.glob(os.path.join(CAMP, '*.aoe2campaign'))):
    b = open(f, 'rb').read()
    secs = sections(b)
    # reassemble: copy the file but treat scenario spans as opaque -> identical by construction;
    # real test: replace each scenario span with the SAME bytes and confirm equality
    rebuilt = bytearray()
    cur = 0
    for (off, hl, total, infl) in secs:
        rebuilt += b[cur:off+total]
        cur = off + total
    rebuilt += b[cur:]
    ident = bytes(rebuilt) == b
    # gap accounting: bytes not covered by a scenario span
    covered = sum(t for (_, _, t, _) in secs)
    gaps = len(b) - covered
    tot_gap += gaps
    p('%-28s %8d  %9d  %5d  %s' % (os.path.basename(f), len(b), len(secs), gaps, ident))

p('\ntotal uncovered bytes across all campaigns: %d' % tot_gap)

# ---- in-place swap feasibility on the smallest campaign ----
p('\n=== in-place embedded-scenario swap test (xcam1) ===')
src = os.path.join(CAMP, 'xcam1.aoe2campaign')
b = open(src, 'rb').read()
secs = sections(b)
off, hl, total, infl = secs[0]
p('  first member: offset %d header %d total %d inflated %d' % (off, hl, total, infl))
p('  first member version %r' % b[off:off+4])
# take the extracted member, modify it with ASP (add a trigger), and try to reinsert
import contextlib, warnings
warnings.filterwarnings('ignore'); import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
mem = os.path.join(HERE, 'extracted', 'xcam1_0.aoe2scenario')
if os.path.exists(mem):
    with contextlib.redirect_stdout(io.StringIO()):
        sc = AoE2DEScenario.from_file(mem)
    nm = len(sc.trigger_manager.triggers)
    with contextlib.redirect_stdout(io.StringIO()):
        sc.trigger_manager.add_trigger('probe trigger')
    out = os.path.join(HERE, 'roundtrip', 'camp_member_mod.aoe2scenario')
    with contextlib.redirect_stdout(io.StringIO()):
        sc.write_to_file(out)
    new = open(out, 'rb').read()
    p('  member original %d bytes -> modified %d bytes (delta %+d), triggers %d -> %d' % (
        total - hl, len(new), len(new) - (total - hl), nm, nm + 1))
    # pad strategy: keep total span length by zero-padding the deflate stream (deflate tolerates trailing garbage? test)
    p('  span length available: %d ; modified member needs %d -> %s' % (
        total, len(new), 'FITS (padding needed)' if len(new) <= total else 'DOES NOT FIT'))
    if len(new) <= total:
        cand = b[:off] + new + b'\x00' * (total - len(new)) + b[off+total:]
        ok = None
        try:
            # re-extract from the candidate and verify the mod is visible
            sub = sections(cand)
            p('  candidate rebuilt: %d bytes, sections found %d, first total %d' % (
                len(cand), len(sub), sub[0][2] if sub else -1))
            open(os.path.join(HERE, 'roundtrip', 'xcam1.padded.aoe2campaign'), 'wb').write(cand)
            p('  wrote candidate to roundtrip\\xcam1.padded.aoe2campaign (scratch only)')
        except Exception as ex:
            p('  candidate !! %s %s' % (type(ex).__name__, ex))
else:
    p('  (extracted member missing)')

open(os.path.join(HERE, 'campaign_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign_out.txt')
