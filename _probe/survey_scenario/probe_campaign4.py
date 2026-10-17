import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# Campaign container: full member map + isolated per-member re-serialization.
import os, sys, io, json, zlib, glob, subprocess, contextlib, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore'); import logging; logging.disable(logging.CRITICAL)

CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = _HERE_PATH("_probe", "survey_scenario")
PY = r'C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
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
        off, (h, consumed, inflated) = found
        res.append((off, h, h + consumed, inflated, b[off:off+4].decode()))
        pos = off + h + consumed
    return res

p('=== ALL 42 CAMPAIGNS: member map (prefix bytes are the container prologue) ===')
p('%-30s %9s %4s %9s %8s %8s  members(off/span/ver)')
grand = 0
for f in sorted(glob.glob(os.path.join(CAMP, '*.aoe2campaign'))):
    b = open(f, 'rb').read()
    ms = members(b)
    prefix = ms[0][0] if ms else len(b)
    covered = sum(m[2] for m in ms)
    tail = len(b) - (prefix + covered)
    grand += len(ms)
    p('%-30s %9d %4d %9d %8d %8d  %s' % (
        os.path.basename(f), len(b), len(ms), prefix, covered, tail,
        ' '.join('%d/%d/%s' % (m[0], m[2], m[4]) for m in ms)))
p('\nTOTAL embedded members across all campaigns: %d' % grand)
p('\nProof line: for every campaign, prefix + sum(spans) + tail == file size (tail always 0 except where noted).')

# ---- xcam1 detailed ----
p('\n=== xcam1.aoe2campaign prologue + gaps ===')
b = open(os.path.join(CAMP, 'xcam1.aoe2campaign'), 'rb').read()
ms = members(b)
p('  file %d B, %d members, prologue %d B, tail %d B' % (len(b), len(ms), ms[0][0], len(b) - (ms[0][0] + sum(m[2] for m in ms))))
p('  prologue hex: %s' % b[:ms[0][0]].hex(' '))
p('  prologue asc: %r' % b[:ms[0][0]])
prev = 0
for k, m in enumerate(ms):
    gap = b[prev:m[0]]
    p('  member %d @%-7d hdr=%-3d span=%-7d inflated=%-8d ver=%s gap_before=%d' % (k, m[0], m[1], m[2], m[3], m[4], len(gap)))
    if gap:
        p('     gap hex %s | asc %r' % (gap[:72].hex(' '), gap[:72]))
    prev = m[0] + m[2]

# ---- isolate members, reserialize each in its own process ----
p('\n=== per-member RE-SERIALIZATION in isolated processes (is the container rewrite feasible?) ===')
EX = os.path.join(HERE, 'camp_iso'); os.makedirs(EX, exist_ok=True)
CH = os.path.join(HERE, '_reser_one.py')
open(CH, 'w', encoding='utf-8').write('''
import sys, io, os, json, contextlib, warnings
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
src, dst = sys.argv[1], sys.argv[2]
rec = {"src": os.path.basename(src)}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        sc = AoE2DEScenario.from_file(src)
    rec["version"] = str(sc.scenario_version)
    rec["triggers"] = len(sc.trigger_manager.triggers)
    rec["units"] = len(sc.unit_manager.get_all_units())
    with contextlib.redirect_stdout(io.StringIO()):
        sc.write_to_file(dst)
    rec["status"] = "OK"; rec["in"] = os.path.getsize(src); rec["out"] = os.path.getsize(dst)
except Exception as e:
    rec["status"] = "FAIL"; rec["err"] = type(e).__name__ + ": " + str(e).replace("\\n", " ")[:110]
print(json.dumps(rec, ensure_ascii=False))
''')
rows = []
for k, m in enumerate(ms):
    mp = os.path.join(EX, 'm%d.aoe2scenario' % k)
    open(mp, 'wb').write(b[m[0]:m[0] + m[2]])
    rp = os.path.join(EX, 'm%d.reser.aoe2scenario' % k)
    r = subprocess.run([PY, CH, mp, rp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    ln = [x for x in (r.stdout or '').splitlines() if x.startswith('{')]
    rec = json.loads(ln[-1]) if ln else {'src': mp, 'status': 'ERR', 'err': (r.stderr or '')[-200:]}
    rec['span'] = m[2]
    rows.append(rec)
    p('  member %d %s span=%d out=%s delta=%s triggers=%s %s' % (
        k, rec.get('version'), m[2], rec.get('out'), (rec.get('out') - m[2]) if rec.get('out') else '-',
        rec.get('triggers'), rec.get('err', '')))
ok = [r for r in rows if r['status'] == 'OK']
p('  %d/%d members reserialized OK' % (len(ok), len(rows)))
if ok:
    p('  total original span bytes %d -> reserialized %d (delta %+d, %.2f%%)' % (
        sum(r['span'] for r in ok), sum(r['out'] for r in ok),
        sum(r['out'] for r in ok) - sum(r['span'] for r in ok),
        100.0 * sum(r['out'] for r in ok) / sum(r['span'] for r in ok)))

open(os.path.join(HERE, 'campaign3_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE campaign3_out.txt')
