# -*- coding: utf-8 -*-
"""Compact indented widget tree dumper. Usage: python s10_tree.py <file.json> [...]"""
import os, sys, json

W = r"D:\Games\Steam\steamapps\common\AoE2DE\widgetui"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"


def unwrap(e):
    return e["Widget"] if isinstance(e, dict) and "Widget" in e else e


def vp(v):
    if not v:
        return "-"
    return "(%s,%s %sx%s %s)" % (v.get("xorigin"), v.get("yorigin"),
                                 v.get("width"), v.get("height"), v.get("alignment"))


def mats(w):
    sm = w.get("StateMaterials") or {}
    out = []
    for k, v in sm.items():
        if k == "UserStates":
            continue
        if not isinstance(v, dict):
            continue
        if "Material" in v:
            out.append("%s=%s" % (k, v["Material"]))
        elif "Font" in v:
            f = v["Font"]
            out.append("%s=Font(idx=%s,pt=%s,%s)" % (k, f.get("FontIndex"), f.get("PointSize"), f.get("Style")))
        else:
            out.append("%s=%s" % (k, sorted(v.keys())))
    return " ".join(out)


def walk(w, depth, out):
    ind = "  " * depth
    bits = ["%s%s '%s'" % (ind, w.get("Type"), w.get("Name"))]
    if w.get("ViewPort"):
        bits.append("VP" + vp(w["ViewPort"]))
    if w.get("Anchor"):
        bits.append("ANCH" + vp(w["Anchor"]))
    if w.get("Box"):
        b = w["Box"]
        bits.append("BOX(%s,%s %sx%s %s gs=%s)" % (b.get("xorigin"), b.get("yorigin"), b.get("width"),
                                                   b.get("height"), b.get("alignment"), b.get("gridstep")))
    if w.get("ZPlane") is not None:
        bits.append("Z=%s" % w["ZPlane"])
    if w.get("ZPlaneLocalOffset") is not None:
        bits.append("ZLO=%s" % w["ZPlaneLocalOffset"])
    if w.get("Text") is not None:
        bits.append("Text=%r" % w["Text"])
    if w.get("TextAnchor"):
        bits.append("TA=%s" % w["TextAnchor"])
    if w.get("Wrap"):
        bits.append("Wrap=%s" % w["Wrap"])
    if w.get("Help"):
        bits.append("Help=%s" % w["Help"])
    m = mats(w)
    if m:
        bits.append("{" + m + "}")
    out.append(" ".join(bits))
    for c in (w.get("ChildWidgets") or []):
        walk(unwrap(c), depth + 1, out)


def main():
    lines = []
    for fn in sys.argv[1:]:
        p = fn if os.path.isabs(fn) else os.path.join(W, fn)
        lines.append("=" * 90)
        lines.append("FILE: " + os.path.basename(p))
        d = json.load(open(p, encoding="utf-8-sig"))
        col = d.get("Collection")
        if not col:
            lines.append("  (no Collection; top keys=%s)" % list(d.keys()))
            continue
        lines.append("Collection '%s' VP%s" % (col.get("Name"), vp(col.get("ViewPort"))))
        for e in (col.get("Widgets") or []):
            walk(unwrap(e), 1, lines)
    txt = "\n".join(lines)
    open(os.path.join(OUT, "tree_dump.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


main()
