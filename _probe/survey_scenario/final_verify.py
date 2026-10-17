import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
# FINAL VERIFICATION
#  A) campaign index (positional) vs physical scan, all 42 campaigns
#  B) ASP readability of EVERY embedded campaign member (isolated processes)
#  C) padded in-place member swap actually re-reads with the modification visible
#  D) difficulty-condition usage across official campaign scenarios
import os, sys, io, zlib, glob, struct, subprocess, json, contextlib, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore'); import logging; logging.disable(logging.CRITICAL)

CAMP = r'D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign'
HERE = _HERE_PATH("_probe", "survey_scenario")
PY = r'C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
EX = os.path.join(HERE, 'camp_all'); os.makedirs(EX, exist_ok=True)
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

def index_entries(pro, n):
    """entries are 64 B: <span><offset><const><name><const><name>, last n*64 B of prologue"""
    start = len(pro) - 64 * n
    out = []
    for k in range(n):
        o = start + 64 * k
        span, off, c1 = struct.unpack_from('<III', pro, o)
        nm1 = pro[o + 12:o + 12 + 24]
        ok = (c1 == struct.unpack_from('<I', pro, o + 12 + 24)[0])
        out.append((span, off, c1, nm1.decode('ascii', 'replace'), ok))
    return start, out

p('=== (A) CAMPAIGN INDEX TABLE vs PHYSICAL SCAN ===')
allm = {}
tot = idx_ok = nm_ok = 0
for f in sorted(glob.glob(os.path.join(CAMP, '*.aoe2campaign'))):
    b = open(f, 'rb').read(); ms = members(b)
    pro = b[:ms[0][0]]
    start, ents = index_entries(pro, len(ms))
    match = sum(1 for k, m in enumerate(ms) if ents[k][0] == m[2] and ents[k][1] == m[0])
    nm = sum(1 for e in ents if e[3].endswith('.aoe2scenario'))
    consts = sorted(set(e[2] for e in ents))
    tot += len(ms); idx_ok += match; nm_ok += nm
    allm[os.path.basename(f)] = (len(b), ms, ents)
    p('  %-28s mem=%-3d idx_match=%-3d names=%-3d const=%s prologue=%-7d entry_start=%-6d' % (
        os.path.basename(f), len(ms), match, nm, consts, len(pro), start))
p('\n  (span,offset) pairs matching physical scan: %d / %d' % (idx_ok, tot))
p('  filename slots present: %d / %d' % (nm_ok, tot))

p('\n=== (C) PADDED IN-PLACE MEMBER SWAP, VERIFIED ===')
cand_path = os.path.join(HERE, 'roundtrip', 'xcam1.padded.aoe2campaign')
if os.path.exists(cand_path):
    c = open(cand_path, 'rb').read()
    orig = open(os.path.join(CAMP, 'xcam1.aoe2campaign'), 'rb').read()
    cm = members(c)
    p('  candidate %d B (original %d B), members found %d' % (len(c), len(orig), len(cm)))
    p('  member offsets: %s (original %s)' % ([m[0] for m in cm], [m[0] for m in members(orig)]))
    p('  member spans  : %s (original %s)' % ([m[2] for m in cm], [m[2] for m in members(orig)]))
    mp = os.path.join(EX, 'padded_m0.aoe2scenario')
    open(mp, 'wb').write(c[cm[0][0]:cm[0][0] + cm[0][2]])
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    with contextlib.redirect_stdout(io.StringIO()):
        s = AoE2DEScenario.from_file(mp)
    names = [t.name for t in s.trigger_manager.triggers]
    p('  re-read member 0: triggers=%d last=%r PROBE_PRESENT=%s' % (
        len(names), names[-1] if names else None, 'PROBE ADDED TRIGGER' in names))
    p('  every other member byte-identical to original: %s' % (
        all(c[cm[k][0]:cm[k][0]+cm[k][2]] == orig[members(orig)[k][0]:members(orig)[k][0]+members(orig)[k][2]] for k in range(1, len(cm)))))
else:
    p('  (candidate missing)')

p('\n=== (B) ASP READABILITY OF ALL 229 EMBEDDED CAMPAIGN MEMBERS (isolated) ===')
CH = os.path.join(HERE, '_read_one.py')
open(CH, 'w', encoding='utf-8').write('''
import sys, io, os, json, contextlib, warnings
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
src = sys.argv[1]; rec = {"file": os.path.basename(src)}
try:
    with contextlib.redirect_stdout(io.StringIO()):
        sc = AoE2DEScenario.from_file(src)
    rec.update(status="OK", version=str(sc.scenario_version),
               triggers=len(sc.trigger_manager.triggers),
               units=len(sc.unit_manager.get_all_units()),
               conds=sum(len(t.conditions) for t in sc.trigger_manager.triggers),
               effects=sum(len(t.effects) for t in sc.trigger_manager.triggers),
               map=sc.map_manager.map_size)
except Exception as e:
    rec.update(status="FAIL", err=type(e).__name__ + ": " + str(e)[:90])
print(json.dumps(rec, ensure_ascii=False))
''')
rows = []
for cf, (sz, ms, ents) in allm.items():
    b = open(os.path.join(CAMP, cf), 'rb').read()
    base = cf.replace('.aoe2campaign', '')
    for k, m in enumerate(ms):
        mp = os.path.join(EX, '%s_%d.aoe2scenario' % (base, k))
        open(mp, 'wb').write(b[m[0]:m[0] + m[2]])
        r = subprocess.run([PY, CH, mp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        ln = [x for x in (r.stdout or '').splitlines() if x.startswith('{')]
        rec = json.loads(ln[-1]) if ln else {'file': mp, 'status': 'ERR', 'err': (r.stderr or '')[-120:]}
        rec['campaign'] = base; rec['member'] = k; rec['ver'] = m[4]; rec['span'] = m[2]
        rows.append(rec)
ok = [r for r in rows if r['status'] == 'OK']
p('  embedded members tested: %d ; readable: %d (%.1f%%) ; failed: %d' % (
    len(rows), len(ok), 100.0 * len(ok) / len(rows), len(rows) - len(ok)))
import collections
p('  readable by version  : %s' % dict(sorted(collections.Counter(r['ver'] for r in ok).items())))
p('  unreadable by version: %s' % dict(sorted(collections.Counter(r['ver'] for r in rows if r['status'] != 'OK').items())))
p('  fail reasons: %s' % dict(collections.Counter((r.get('err') or '')[:55] for r in rows if r['status'] != 'OK')))
p('  trigger totals across readable members: triggers=%d conditions=%d effects=%d units=%d' % (
    sum(r['triggers'] for r in ok), sum(r['conds'] for r in ok), sum(r['effects'] for r in ok), sum(r['units'] for r in ok)))
json.dump(rows, open(os.path.join(HERE, 'campaign_members.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

p('\n=== (D) difficulty-condition usage in readable official scenarios ===')
d18 = 0
for r in ok:
    if r.get('conds'):
        d18 += 1
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
for nm in ('xcam1_0', 'xcam1_1', 'acam1_0', 'cam2_0', 'fcam7_0', 'dcam0_3'):
    mp = os.path.join(EX, nm + '.aoe2scenario')
    if not os.path.exists(mp): continue
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            s = AoE2DEScenario.from_file(mp)
        n18 = sum(1 for t in s.trigger_manager.triggers for c in t.conditions if int(c.condition_type) == 18)
        obj = sum(1 for t in s.trigger_manager.triggers if getattr(t, 'display_as_objective', 0))
        p('  %-10s v%s triggers=%-4d diffcond=%-3d objectives=%-3d units=%-6d map=%d' % (
            nm, s.scenario_version, len(s.trigger_manager.triggers), n18, obj,
            len(s.unit_manager.get_all_units()), s.map_manager.map_size))
    except Exception as ex:
        p('  %-10s !! %s' % (nm, type(ex).__name__))

open(os.path.join(HERE, 'final_verify_out.txt'), 'w', encoding='utf-8').write(buf.getvalue())
print('WROTE final_verify_out.txt')
