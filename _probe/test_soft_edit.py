# -*- coding: utf-8 -*-
"""Probe: does the SHIPPED bundle actually let a human edit a shared column?

Reads /api/fields for the record the owner was staring at (5066 Mule cart) out
of the bundle's own exe, then drives the real page and counts rows that carry
ro, soft and seen, and how many rows render an input at all.
"""
import json, os, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _paths as P

BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, 'AoE2 DE Mod Workshop.exe')
PORT = 7813
UNIT = 74


def start():
    subprocess.run(['taskkill', '/IM', 'AoE2 DE Mod Workshop.exe', '/F'], capture_output=True)
    time.sleep(1)
    p = subprocess.Popen([EXE, '--port', str(PORT)], cwd=BUNDLE,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(180):
        time.sleep(0.5)
        try:
            j = json.loads(urllib.request.urlopen(
                'http://127.0.0.1:%d/api/progress' % PORT, timeout=5).read())
            if (j.get('progress') or {}).get('ready'):
                return p
        except Exception:
            pass
    raise SystemExit('bundle never became ready')


FAILED = []


def check(ok, what, detail=''):
    print(('  ok   ' if ok else '  FAIL ') + what + ('  ' + str(detail) if detail else ''))
    if not ok:
        FAILED.append(what)


p = start()
try:
    raw = urllib.request.urlopen(
        'http://127.0.0.1:%d/api/fields?unit=%d&civ=*' % (PORT, UNIT), timeout=300).read()
    d = json.loads(raw)
    rows = d.get('fields') or d.get('rows') or []
    ro = [r for r in rows if r.get('ro')]
    soft = [r for r in rows if r.get('soft')]
    seen = [r for r in rows if r.get('seen')]
    print('  %d rows | ro %d | soft %d | seen %d' % (len(rows), len(ro), len(soft), len(seen)))
    print('  ro names: ' + ', '.join(r['name'] for r in ro[:10]))
    print('  soft names: ' + ', '.join(r['name'] for r in soft[:10]))

    check(len(soft) >= 8, 'shared integers are marked soft, not ro', len(soft))
    check(not any(r['name'] == 'LanguageDLLName' for r in ro),
          'a text id is editable (it is a normal integer)')
    check(len(seen) > 300, 'the value census reaches most columns', len(seen))

    body = json.dumps({'kind': 'unit', 'unit': UNIT, 'field': 'ScenarioTrigger2',
                       'value': '7', 'civ': '*', 'dry': True}).encode()
    req = urllib.request.Request('http://127.0.0.1:%d/api/field-set' % PORT, data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        w = json.loads(urllib.request.urlopen(req, timeout=120).read())
        check(w.get('ok'), 'a soft column accepts a write (dry run)', json.dumps(w, ensure_ascii=False)[:150])
        check(bool(w.get('warn')), 'and it warns that the value is shared', (w.get('warn') or '')[:60])
    except Exception as e:
        check(False, 'a soft column accepts a write (dry run)', str(e)[:120])

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1237, 'height': 880})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://127.0.0.1:%d/' % PORT, wait_until='domcontentloaded', timeout=60000)
        pg.wait_for_function("document.querySelectorAll('#edlist .edrow').length >= 50",
                             timeout=240000)
        # The editor renders into #edpane, which only exists once the view is
        # the active one -- opening a record from the home view leaves the
        # screenshot on the home page.
        pg.evaluate("() => { location.hash = 'editor'; }")
        pg.wait_for_timeout(1500)
        pg.evaluate('async (u) => { await openEditor({kind: "unit", id: u}); }', UNIT)
        pg.wait_for_timeout(3000)
        ui = pg.evaluate("""() => {
            const body = document.getElementById('fbody');
            // The hint lines are rows too (tr.fhint, one per field that carries a
            // hint). They hold prose, not a field, so they have no input and no
            // ro tag -- counting them here invented 434 dead rows. Field rows are
            // what this probe is about.
            const rows = [...body.querySelectorAll('table.f tr:not(.fhint)')].slice(1);
            const withInput = rows.filter(tr => tr.querySelector('td.e input'));
            const roTags = body.querySelectorAll('span.ro').length;
            const softTags = body.querySelectorAll('span.soft').length;
            // .evdead is reused for "另有 N 份不同", so a dead row is one with
            // NEITHER an input NOR the hard read-only tag.
            const dead = rows.filter(tr => !tr.querySelector('td.e input')
                                        && !tr.querySelector('span.ro')).length;
            const selects = body.querySelectorAll('select.ev').length;
            return { rows: rows.length, withInput: withInput.length,
                     roTags: roTags, softTags: softTags, dead: dead, selects: selects,
                     sample: withInput.slice(0, 3).map(tr => tr.querySelector('td.fl').textContent) };
        }""")
        print('  UI: ' + json.dumps(ui, ensure_ascii=False))
        check(ui['withInput'] >= ui['rows'] - ui['roTags'] - 2,
              'every row that is not hard-read-only has an input box',
              '%d of %d rows carry an input' % (ui['withInput'], ui['rows']))
        check(ui['dead'] == 0, 'no row is replaced by a dead only-one-value label', ui['dead'])
        check(ui['softTags'] > 0, 'shared columns wear a 共用 tag', ui['softTags'])
        check(not errs, 'no uncaught exception while drawing', errs[:2])
        # The field table starts below the fold; the shot has to show the rows,
        # which is the whole point of this probe.
        pg.evaluate("() => { const t = document.querySelector('#fbody table.f'); if (t) t.scrollIntoView({block: 'start'}); }")
        pg.wait_for_timeout(600)
        shot = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_shots', 'soft_field_editor.png')
        pg.screenshot(path=shot)
        print('  shot ' + shot)
        b.close()
finally:
    subprocess.run(['taskkill', '/IM', 'AoE2 DE Mod Workshop.exe', '/F'], capture_output=True)

print()
print('SOFT EDIT PROBE: ' + ('ALL GREEN' if not FAILED else 'FAILURES: ' + '; '.join(FAILED)))
# The verdict line was the whole output and the exit code was always 0, so a
# runner would have recorded a red probe as OK.  A gate whose failure is
# invisible to the runner is not a gate.
if FAILED:
    sys.exit(1)
