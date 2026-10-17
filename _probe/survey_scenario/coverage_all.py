# Definitive coverage over EVERY scenario file on this machine (game + user profile),
# plus write-determinism / idempotency test.
import os, sys, subprocess, json, csv
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = r'D:\Software\DeepSeek Harness\工作区2\_probe\survey_scenario'
PY = r'C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
CHILD = os.path.join(HERE, '_cover_json.py')
ROOTS = [r'D:\Games\Steam\steamapps\common\AoE2DE',
         r'C:\Users\26913\Games\Age of Empires 2 DE']

files = []
for root in ROOTS:
    for r, d, f in os.walk(root):
        for n in f:
            if n.lower().endswith(('.scx', '.aoe2scenario')):
                files.append(os.path.join(r, n))
files.sort()
print('scenario files on machine (excl. campaigns):', len(files))

rows = []
for i, p in enumerate(files, 1):
    r = subprocess.run([PY, CHILD, p], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=180)
    out = (r.stdout or '').strip().splitlines()
    rec = json.loads(out[-1]) if out and out[-1].startswith('{') else {'path': p, 'status': 'ERR', 'err': (r.stderr or '')[-300:]}
    rec['bytes'] = os.path.getsize(p)
    rec['name'] = os.path.basename(p)
    rows.append(rec)
    print('%3d/%d %-52s %-6s v%-5s %8d B %6ss %s' % (
        i, len(files), rec['name'][:52], rec.get('status'), rec.get('file_version'),
        rec['bytes'], rec.get('seconds'), (rec.get('err') or '')[:70]))

tsv = os.path.join(HERE, 'coverage_all.tsv')
with open(tsv, 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['name', 'path', 'status', 'file_version',
                                       'reported_version', 'bytes', 'seconds', 'err'], delimiter='\t')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k) for k in w.fieldnames})

ok = [r for r in rows if r.get('status') == 'OK']
bad = [r for r in rows if r.get('status') != 'OK']
print('\n=== SUMMARY (all %d scenario files on machine) ===' % len(rows))
print('readable  : %d  (%.1f%%)' % (len(ok), 100.0 * len(ok) / len(rows)))
print('unreadable: %d  (%.1f%%)' % (len(bad), 100.0 * len(bad) / len(rows)))
import collections
print('OK  by version:', dict(sorted(collections.Counter(r.get('file_version') for r in ok).items())))
print('FAIL by version:', dict(sorted(collections.Counter(r.get('file_version') for r in bad).items())))
print('FAIL reasons:', dict(collections.Counter((r.get('err') or '')[:60] for r in bad)))
print('WROTE', tsv)

# ---- write determinism / idempotency ----
print('\n=== WRITE DETERMINISM (2nd generation) ===')
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
src = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario'
gen = {}
cur = src
for g in range(4):
    s = AoE2DEScenario.from_file(cur)
    dst = os.path.join(HERE, 'roundtrip', 'gen%d.aoe2scenario' % (g + 1))
    s.write_to_file(dst)
    gen[g + 1] = (os.path.getsize(cur), os.path.getsize(dst))
    print('  gen%d: in=%d out=%d delta=%+d ratio=%.5f  triggers=%d units=%d' % (
        g + 1, gen[g + 1][0], gen[g + 1][1], gen[g + 1][1] - gen[g + 1][0],
        gen[g + 1][1] / gen[g + 1][0],
        len(s.trigger_manager.triggers), len(s.unit_manager.get_all_units())))
    cur = dst
h = [open(os.path.join(HERE, 'roundtrip', 'gen%d.aoe2scenario' % k), 'rb').read(8).hex(' ') for k in (1, 2, 3, 4)]
print('  headers:', h)
print('  gen3 == gen4 byte-identical:', open(os.path.join(HERE, 'roundtrip', 'gen3.aoe2scenario'), 'rb').read() == open(os.path.join(HERE, 'roundtrip', 'gen4.aoe2scenario'), 'rb').read())
