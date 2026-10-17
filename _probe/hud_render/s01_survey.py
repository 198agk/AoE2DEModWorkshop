# -*- coding: utf-8 -*-
"""Survey widgetui layout JSONs: widget Type census, field usage, viewport/alignment usage.
Widgets are wrapped: "Widgets": [{"Widget": {...}}, ...]
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json, os, sys, collections, io

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
OUT = _HERE_PATH("_probe", "hud_render")

type_counter = collections.Counter()
by_file = {}
top_keys = collections.Counter()
widget_keys = collections.Counter()
align_counter = collections.Counter()
box_align_counter = collections.Counter()
anchor_align_counter = collections.Counter()
sm_keys = collections.Counter()
file_info = []
parse_errors = []
font_records = []
wrapper_keys = collections.Counter()

def unwrap_list(lst):
    """Widgets list entries are {"Widget": {...}} or occasionally bare dicts."""
    out = []
    for e in lst or []:
        if isinstance(e, dict) and "Widget" in e:
            wrapper_keys["Widget"] += 1
            out.append(e["Widget"])
        elif isinstance(e, dict):
            wrapper_keys["<bare>"] += 1
            out.append(e)
    return out

def visit_widget(w, fname, depth=0):
    if not isinstance(w, dict):
        return
    t = w.get("Type")
    type_counter[str(t) if t is not None else "<NO TYPE>"] += 1
    by_file.setdefault(fname, collections.Counter())[str(t) if t is not None else "<NO TYPE>"] += 1
    for k in w.keys():
        widget_keys[k] += 1
    vp = w.get("ViewPort")
    if isinstance(vp, dict) and "alignment" in vp:
        align_counter[str(vp["alignment"])] += 1
    box = w.get("Box")
    if isinstance(box, dict) and "alignment" in box:
        box_align_counter[str(box["alignment"])] += 1
    an = w.get("Anchor")
    if isinstance(an, dict) and "alignment" in an:
        anchor_align_counter[str(an["alignment"])] += 1
    sm = w.get("StateMaterials")
    if isinstance(sm, dict):
        for k, v in sm.items():
            sm_keys[k] += 1
            # Font blocks live under StateMaterials UserStateN / StateNormal etc.
            if isinstance(v, dict):
                f = v.get("Font")
                if isinstance(f, dict):
                    font_records.append({
                        "file": fname, "widget": w.get("Name"), "wtype": t,
                        "FontIndex": f.get("FontIndex"), "PointSize": f.get("PointSize"),
                        "Style": f.get("Style"),
                        "TextColor": f.get("TextColor"),
                        "TextOutlineWidth": f.get("TextOutlineWidth"),
                        "TextOutlineColor": f.get("TextOutlineColor"),
                    })
    # some widgets carry Font at top level
    f = w.get("Font")
    if isinstance(f, dict):
        font_records.append({"file": fname, "widget": w.get("Name"), "wtype": t,
                             "FontIndex": f.get("FontIndex"), "PointSize": f.get("PointSize"),
                             "Style": f.get("Style"), "TextColor": f.get("TextColor"),
                             "TextOutlineWidth": f.get("TextOutlineWidth"),
                             "TextOutlineColor": f.get("TextOutlineColor")})
    for child in unwrap_list(w.get("ChildWidgets")):
        visit_widget(child, fname, depth + 1)

files = []
for root, dirs, fns in os.walk(W):
    for fn in fns:
        if fn.lower().endswith(".json"):
            files.append(os.path.join(root, fn))
files.sort()

for f in files:
    rel = os.path.relpath(f, W)
    try:
        with open(f, "r", encoding="utf-8-sig") as fh:
            d = json.load(fh)
    except Exception as e:
        parse_errors.append((rel, repr(e)))
        continue
    if not isinstance(d, dict):
        parse_errors.append((rel, "top-level %s" % type(d).__name__)); continue
    for k in d.keys():
        top_keys[k] += 1
    cnt = [0]

    def count(w):
        if not isinstance(w, dict):
            return
        cnt[0] += 1
        for c in unwrap_list(w.get("ChildWidgets")):
            count(c)

    colls = []
    for cname, coll in d.items():
        if not isinstance(coll, dict):
            continue
        ws = coll.get("Widgets")
        if not isinstance(ws, list):
            continue
        colls.append(cname)
        for w in unwrap_list(ws):
            visit_widget(w, rel)
            count(w)
    file_info.append({"file": rel, "bytes": os.path.getsize(f), "widgets": cnt[0],
                      "collections": colls})

rep = io.StringIO()
rep.write("=== FILES (%d) with widget counts > 0 ===\n" % len(files))
nz = [fi for fi in file_info if fi["widgets"] > 0]
rep.write("files with widgets: %d / %d\n" % (len(nz), len(file_info)))
for fi in sorted(nz, key=lambda x: -x["bytes"]):
    rep.write("%-60s %10d B  %6d widgets  %s\n" % (fi["file"], fi["bytes"], fi["widgets"], ", ".join(fi["collections"])))
rep.write("\n=== TOTAL WIDGETS: %d ===\n" % sum(f["widgets"] for f in file_info))
rep.write("\n=== WIDGET TYPE FREQUENCY (all files) ===\n")
tot = sum(type_counter.values())
for t, c in type_counter.most_common():
    rep.write("%-28s %7d  %6.2f%%\n" % (t, c, 100.0 * c / tot))
rep.write("\n=== Widget list wrapper keys ===\n")
for k, c in wrapper_keys.most_common():
    rep.write("%-20s %d\n" % (k, c))
rep.write("\n=== TOP-LEVEL KEYS (count of files) ===\n")
for k, c in top_keys.most_common(30):
    rep.write("%-40s %d\n" % (k, c))
rep.write("\n=== WIDGET KEYS (frequency) ===\n")
for k, c in widget_keys.most_common():
    rep.write("%-40s %d\n" % (k, c))
rep.write("\n=== StateMaterials slot keys ===\n")
for k, c in sm_keys.most_common(60):
    rep.write("%-40s %d\n" % (k, c))
rep.write("\n=== ViewPort.alignment ===\n")
for k, c in align_counter.most_common():
    rep.write("%-20s %d\n" % (k, c))
rep.write("\n=== Box.alignment ===\n")
for k, c in box_align_counter.most_common():
    rep.write("%-20s %d\n" % (k, c))
rep.write("\n=== Anchor.alignment ===\n")
for k, c in anchor_align_counter.most_common():
    rep.write("%-20s %d\n" % (k, c))
rep.write("\n=== PARSE ERRORS ===\n")
for r, e in parse_errors:
    rep.write("%s : %s\n" % (r, e))

# FontIndex frequency
fi_counter = collections.Counter()
for r in font_records:
    fi_counter[r["FontIndex"]] += 1
rep.write("\n=== FontIndex frequency (%d Font blocks found) ===\n" % len(font_records))
for k, c in sorted(fi_counter.items(), key=lambda x: (x[0] is None, x[0])):
    rep.write("FontIndex %-8s %6d\n" % (k, c))
rep.write("\n=== distinct (FontIndex, PointSize) pairs ===\n")
ps = collections.Counter((r["FontIndex"], r["PointSize"]) for r in font_records)
for k, c in sorted(ps.items(), key=lambda x: -x[1]):
    rep.write("FontIndex=%-6s PointSize=%-6s %6d\n" % (k[0], k[1], c))
rep.write("\n=== distinct (FontIndex, Style) pairs ===\n")
st = collections.Counter((r["FontIndex"], r["Style"]) for r in font_records)
for k, c in sorted(st.items(), key=lambda x: -x[1]):
    rep.write("FontIndex=%-6s Style=%-24s %6d\n" % (k[0], k[1], c))

open(os.path.join(OUT, "survey_types.txt"), "w", encoding="utf-8").write(rep.getvalue())
json.dump({"type_counter": dict(type_counter), "by_file": {k: dict(v) for k, v in by_file.items()},
           "file_info": file_info, "widget_keys": dict(widget_keys),
           "align": dict(align_counter), "box_align": dict(box_align_counter),
           "anchor_align": dict(anchor_align_counter), "sm_keys": dict(sm_keys),
           "font_records": font_records},
          open(os.path.join(OUT, "survey_types.json"), "w", encoding="utf-8"), indent=1)
print("TOTAL files=%d  files-with-widgets=%d  TOTAL widgets=%d  FontBlocks=%d" %
      (len(files), len(nz), sum(f["widgets"] for f in file_info), len(font_records)))
print("\n=== WIDGET TYPE FREQUENCY ===")
for t, c in type_counter.most_common():
    print("%-28s %7d  %6.2f%%" % (t, c, 100.0 * c / tot))
