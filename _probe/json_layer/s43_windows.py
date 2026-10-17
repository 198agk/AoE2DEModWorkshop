import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io, json, re, sys
sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
import parse_dat as P

OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
BASE = os.path.join(GAME, "resources", "_common", "dat")
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")
exe = open(os.path.join(GAME, "AoE2DE_s.exe"), "rb").read()

def strings(lo, hi, minlen=4):
    out = []
    for m in re.finditer(rb"[ -~]{%d,}" % minlen, exe[lo:hi]):
        out.append((lo + m.start(), m.group(0).decode("latin-1")))
    return out

w("=" * 78)
w("G. exe window around the CivTechTrees parse site (52827900..52829500)")
w("=" * 78)
for off, s in strings(52827900, 52829500):
    w("  %8d  %s" % (off, s))

w("")
w("=" * 78)
w("H. exe window around buttons.json (52800400..52800800)")
w("=" * 78)
for off, s in strings(52800400, 52800900):
    w("  %8d  %s" % (off, s))

w("")
w("=" * 78)
w("I. buttons.json actual keys vs exe key list")
w("=" * 78)
bj = json.loads(open(os.path.join(BASE, "buttons.json"), "rb").read().decode("utf-8-sig"))
ks = set()
def kk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            ks.add(k); kk(v)
    elif isinstance(o, list):
        for v in o: kk(v)
kk(bj)
w("  file keys: %s" % sorted(ks))
w("  exe-declared: command_button_list, button_action_id, button_shift_action_id, sequence_id,"
  " icon_id, help_string_id, more_help_string_id, NotFromGame")
for k in sorted(ks | {"button_shift_action_id", "NotFromGame"}):
    w("    %-24s file=%-5s exe=%s" % (k, k in ks, k.encode() in exe))

w("")
w("=" * 78)
w("J. .dat sound records: do they have names?  (genieutils Sound.h)")
w("=" * 78)
data, how = P.load_dat(os.path.join(BASE, "empires2_x2_p1.dat"))
p = P.Parser(data); st = p.parse()
snd = st["sounds"]
w("  .dat sounds n=%d" % len(snd))
w("  record keys: %s" % sorted(snd[0].keys()))
named = [s for s in snd if s.get("name")]
w("  records with a non-empty 'name': %d" % len(named))
w("  first 5 records: %s" % json.dumps(snd[:5], ensure_ascii=False)[:400])
sh = _HERE_PATH("_probe", "source", "genieutils", "include", "genie", "dat", "Sound.h")
w("  Sound.h exists=%s" % os.path.exists(sh))
if os.path.exists(sh):
    t = open(sh, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"(std::string\s+\w+[^;]*;|class \w+)", t):
        w("    " + m.group(0).strip())
sj = json.loads(open(os.path.join(BASE, "sounds.json"), "rb").read().decode("utf-8-sig"))["sound_list"]
w("  sounds.json keys: %s" % sorted(sj[0].keys()))
w("  sounds.json n=%d" % len(sj))
w("  overlap of sounds.json 'name' with .dat record names: %d" % len(
    {x.get("name") for x in sj} & {s.get("name") for s in snd if s.get("name")}))
open(os.path.join(OUT, "s43_windows.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
