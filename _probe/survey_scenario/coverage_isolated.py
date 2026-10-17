"""Run one file per subprocess so ASP's cross-version contamination cannot affect results.
Emits a TSV: path, version, bytes, ok, seconds, err_type, err_msg
"""
import subprocess
import sys
import os
import glob

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
CHILD = os.path.join(HERE, "_cover_one.py")

open(CHILD, "w", encoding="utf-8").write('''
import sys, os, io, contextlib, time, warnings
warnings.filterwarnings("ignore")
import logging; logging.disable(logging.CRITICAL)
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
p = sys.argv[1]
ver = open(p, "rb").read(4).decode("ascii", "replace")
t0 = time.time()
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sc = AoE2DEScenario.from_file(p)
    dt = time.time() - t0
    print("OK\\t%s\\t%s\\t%f\\t%s\\t-" % (ver, sc.scenario_version, dt, sc.variant))
except Exception as e:
    dt = time.time() - t0
    print("FAIL\\t%s\\t-\\t%f\\t%s\\t%s" % (ver, dt, type(e).__name__, str(e).replace("\\t", " ").replace("\\n", " ")[:110]))
''')

G = r"D:\Games\Steam\steamapps\common\AoE2DE"
U = r"C:\Users\26913\Games\Age of Empires 2 DE"
files = []
files += sorted(glob.glob(os.path.join(G, "resources", "_common", "drs", "gamedata_x2", "*.scx")))
files += sorted(glob.glob(os.path.join(U, "**", "*.aoe2scenario"), recursive=True))
files += sorted(glob.glob(os.path.join(G, "resources", "_common", "campaign", "*.aoe2scenario")))
files += sorted(glob.glob(os.path.join(HERE, "extracted", "*.aoe2scenario")))
files += sorted(glob.glob(os.path.join(HERE, "roundtrip", "*.aoe2scenario")))

rows = []
for p in files:
    try:
        r = subprocess.run([PY, CHILD, p], capture_output=True, text=True, timeout=300)
        line = [l for l in r.stdout.splitlines() if l.startswith(("OK", "FAIL"))]
        parts = line[-1].split("\t") if line else ["FAIL", "?", "-", "0", "NoOutput", r.stderr[-90:]]
    except subprocess.TimeoutExpired:
        parts = ["FAIL", "?", "-", "300", "Timeout", "-"]
    rows.append([p] + parts)

hdr = ["status", "file_version", "reported_version", "seconds", "detail", "err"]
print("path\t" + "\t".join(hdr) + "\tbytes")
for p, *rest in rows:
    print(p + "\t" + "\t".join(rest) + "\t" + str(os.path.getsize(p)))

from collections import Counter
print()
print("=== SUMMARY ===")
print("total:", len(rows))
print("clean read OK :", sum(1 for r in rows if r[1] == "OK"))
print("clean read FAIL:", sum(1 for r in rows if r[1] == "FAIL"))
print("OK  by file-version:", dict(sorted(Counter(r[2] for r in rows if r[1] == "OK").items())))
print("FAIL by file-version:", dict(sorted(Counter(r[2] for r in rows if r[1] == "FAIL").items())))
print("FAIL error types   :", dict(Counter(r[5] for r in rows if r[1] == "FAIL")))
print("variant values     :", dict(Counter(r[5] for r in rows if r[1] == "OK")))
secs = sorted(float(r[4]) for r in rows if r[1] == "OK")
if secs:
    print(f"read seconds: n={len(secs)} min={secs[0]:.3f} median={secs[len(secs)//2]:.3f} max={secs[-1]:.3f}")
big = max((os.path.getsize(r[0]) for r in rows), default=0)
print("largest file attempted:", big, "bytes")
