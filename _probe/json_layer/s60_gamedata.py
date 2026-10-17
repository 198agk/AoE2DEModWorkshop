import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import os, io
OUT = _HERE_PATH("_probe", "json_layer")
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
rep = io.StringIO()
def w(s=""):
    rep.write(str(s) + "\n")

w("=== do the GameDataSet files referenced by the exe exist anywhere? ===")
targets = ["gamedata_x1", "gamedata_x2", "random-map-base.txt", "random-map-dlc.txt",
           "gamedata_x1_p1.dat", "gamedata_x2_p1.dat"]
found = {t: [] for t in targets}
for root, dirs, files in os.walk(GAME):
    for n in list(dirs) + files:
        if n in found:
            found[n].append(os.path.relpath(os.path.join(root, n), GAME))
for t in targets:
    w("  %-24s hits=%d %s" % (t, len(found[t]), found[t][:5]))

w("")
w("=== every *.dat under resources (which .dat files ship?) ===")
for root, dirs, files in os.walk(os.path.join(GAME, "resources")):
    for f in files:
        if f.lower().endswith(".dat"):
            fp = os.path.join(root, f)
            w("  %-72s %10d B  %s" % (os.path.relpath(fp, GAME), os.path.getsize(fp),
                                       __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").localtime(os.path.getmtime(fp)))))

w("")
w("=== 'File not found in data set resource' semantics: what paths does GameDataSet try? ===")
w("  exe literals nearby (from s56): '%s\\%s' @53017528, 'empires2_x2_p1.dat' @53017672,")
w("  'gamedata_x1' @53017696, 'random-map-base.txt' @53017800, 'gamedata_x2' @53017824,")
w("  'random-map-dlc.txt' @53017920, '.dat' @53018044, then civilizations.json @53018872")
open(os.path.join(OUT, "s60_gamedata.txt"), "w", encoding="utf-8").write(rep.getvalue())
print(rep.getvalue())
