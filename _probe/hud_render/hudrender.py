# -*- coding: utf-8 -*-
"""Offline AoE2 DE HUD renderer prototype.

Renders a widgetui layout JSON onto a 3840x2160 canvas using only files the
game ships (no atlas DDS decode: atlas UV rects are 1:1 with the unpacked PNG
source tree, proven in s09_nineslice.py).

Usage:
    python hudrender.py resourcepanel.json scorepanel.json
"""
import os, sys, json, struct, math, collections, argparse
from PIL import Image, ImageDraw, ImageFilter, ImageChops

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
UIDIR = os.path.join(GAME, "widgetui")
FONTDIR = os.path.join(GAME, "resources", "_common", "fonts")
SCRATCH = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
OUTDIR = os.path.join(SCRATCH, "out")
CANVAS_W, CANVAS_H = 3840, 2160

# Loose-file mod overlay roots. A mod that ships widgetui/<same relative path>
# OVERRIDES the shipped art (proven in this workspace: a mod with zero .dds files
# replaces HUD art and the game renders it). Populated by --mods / MOD_ROOTS.
MOD_ROOTS = []

LR = Image.Resampling.LANCZOS

# ---------------------------------------------------------------- alignment

def split_align(a):
    """'BottomRight' -> ('Bottom','Right'); tolerant of Centre/Center/Middle."""
    if not a:
        return ("Top", "Left")
    s = a.replace("Center", "Centre").replace("Middle", "Centre")
    for v in ("Top", "Bottom", "Centre"):
        if s.startswith(v):
            rest = s[len(v):]
            if rest == "":
                return (v, "Centre")
            for h in ("Left", "Centre", "Right"):
                if rest == h:
                    return (v, h)
            return (v, "Centre")
    return ("Top", "Left")


def align_rect(x, y, w, h, alignment):
    """Place a w x h rect so that the point (x,y) lands on the corner/edge/centre
    of the rect named by `alignment`, in parent top-left-relative space.

    Evidence (resourcepanel.json): Wood VP(57,57 84x84 CentreCentre) must sit
    left of Food VP(257,57...) near the canvas' left edge -> centre at (57,57)."""
    v, hz = split_align(alignment)
    if hz == "Left":
        dx = 0.0
    elif hz == "Centre":
        dx = -w / 2.0
    else:
        dx = -w
    if v == "Top":
        dy = 0.0
    elif v == "Centre":
        dy = -h / 2.0
    else:
        dy = -h
    return (x + dx, y + dy, w, h)


# ------------------------------------------------------------------ assets

class Assets(object):
    def __init__(self):
        with open(os.path.join(UIDIR, "materials.json"), encoding="utf-8-sig") as f:
            mj = json.load(f)
        self.mats = {}
        for e in mj["Materials"]:
            d = e["MaterialDef"]
            self.mats[d["Name"]] = d
        self.atlases = {}
        for e in mj["AtlasTextures"]:
            d = e["AtlasDef"]
            self.atlases[d["Name"]] = d
        self.globals = {}
        for e in mj["GlobalTextures"]:
            d = e["TextureDef"]
            self.globals[d["Name"]] = d
        self._img = {}

    def img(self, rel):
        rel = rel.replace("\\", "/")
        # Loose-file mod override: a mod shipping widgetui/<rel> wins over the
        # shipped tree, exactly as the game does it.
        for mr in MOD_ROOTS:
            q = os.path.join(mr, rel)
            if os.path.exists(q):
                p = q
                break
        else:
            p = os.path.join(UIDIR, rel)
        if p in self._img:
            return self._img[p]
        im = None
        if os.path.exists(p):
            try:
                im = Image.open(p).convert("RGBA")
            except Exception:
                im = None
        if im is None:
            alt = os.path.splitext(p)[0] + ".dds"
            if os.path.exists(alt):
                try:
                    im = Image.open(alt).convert("RGBA")
                except Exception:
                    im = None
        self._img[p] = im
        return im

    def resolve(self, name):
        """-> (image|None, rgba_color|None, status, detail, blend)"""
        if name in (None, "", "None", "Null"):
            return (None, None, "NOOP", "material:%s" % name, None)
        d = self.mats.get(name)
        if d is None:
            return (None, None, "MATERIAL_NOT_FOUND", name, None)
        blend = d.get("Blend")
        t = d.get("Type")
        if t == "Color":
            c = d.get("Color") or {}
            col = tuple(int(round(255 * _f(c.get(k, 1)))) for k in ("r", "g", "b", "a"))
            return (None, col, "OK_COLOR", "Color%s" % (col,), blend)
        if t == "Atlas":
            a = self.atlases.get(d.get("AtlasRef"))
            if a is None:
                return (None, None, "ATLAS_NOT_FOUND", str(d.get("AtlasRef")), blend)
            tx = None
            for e in a["Textures"]:
                if e["RefName"] == d.get("TextureRef"):
                    tx = e
                    break
            if tx is None:
                return (None, None, "ATLAS_ENTRY_NOT_FOUND",
                        "%s/%s" % (d.get("AtlasRef"), d.get("TextureRef")), blend)
            im = self.img(tx.get("FileName") or "")
            if im is None:
                return (None, None, "GLOBAL_FILE_MISSING", str(tx.get("FileName")), blend)
            # The normalized UV rect is a position INSIDE the packed atlas, but the
            # FileName target is the unpacked standalone source PNG. s09_nineslice.py
            # proved for all 4354 atlas materials that the uv rect EXTENT
            # ((BRX-TLX)*MaxWidth, (BRY-TLY)*MaxHeight) equals the PNG's pixel size
            # (within a 1px pack gutter). So the PNG is used WHOLE; the uv OFFSET is
            # meaningless against the standalone file.
            try:
                aw, ah = float(a["MaxWidth"]), float(a["MaxHeight"])
                ew = (float(tx["imageBRX"]) - float(tx["imageTLX"])) * aw
                eh = (float(tx["imageBRY"]) - float(tx["imageTLY"])) * ah
                if abs(ew - im.width) <= 1.5 and abs(eh - im.height) <= 1.5:
                    return (im, None, "OK_ATLAS_STANDALONE_PNG",
                            "%s (%dx%d)" % (os.path.basename(tx["FileName"]), im.width, im.height), blend)
                x0 = int(round(float(tx["imageTLX"]) * aw)); y0 = int(round(float(tx["imageTLY"]) * ah))
                x1 = int(round(float(tx["imageBRX"]) * aw)); y1 = int(round(float(tx["imageBRY"]) * ah))
                if x1 > im.width or y1 > im.height:
                    return (im.crop((0, 0, min(x1 - x0, im.width), min(y1 - y0, im.height))), None,
                            "OK_ATLAS_EXTENT_MISMATCH_CLIPPED",
                            "%s png=%dx%d uvExtent=%.1fx%.1f" % (os.path.basename(tx["FileName"]),
                                                                 im.width, im.height, ew, eh), blend)
                return (im.crop((x0, y0, x1, y1)), None, "OK_ATLAS_CROP",
                        "%s uv=%d,%d,%d,%d" % (os.path.basename(tx["FileName"]), x0, y0, x1, y1), blend)
            except Exception as e:
                return (im, None, "UV_PARSE_ERROR", "%s %s" % (tx.get("FileName"), e), blend)
        if t == "Texture":
            tr = d.get("TextureRef") or ""
            g = self.globals.get(tr)
            rel = (g or {}).get("FileName") or tr
            im = self.img(rel)
            if im is None:
                return (None, None, "GLOBAL_FILE_MISSING", str(rel), blend)
            return (im, None, "OK_TEXTURE", "%s (%dx%d)" % (os.path.basename(rel), im.width, im.height), blend)
        return (None, None, "MATERIAL_TYPE_UNKNOWN", str(t), blend)


def _f(v):
    try:
        return float(v)
    except Exception:
        return 0.0


# -------------------------------------------------------------------- font

FONT_TABLE = {0: "combined", 1: "basic_bold_16", 2: "combined_sansserif"}
FONT_FALLBACK = {3: "combined", -1: "combined"}


class GlyphFont(object):
    def __init__(self, name):
        self.name = name
        data = open(os.path.join(FONTDIR, name + ".box"), "rb").read()
        ver, cnt, pages, srcpx = struct.unpack_from("<IIIf", data, 0)
        self.count, self.pages, self.srcpx = cnt, pages, srcpx
        self.recs = []
        off = 16
        for _ in range(cnt):
            self.recs.append(struct.unpack_from("<6fI3f", data, off))
            off += 40
        self.cmap = {}
        for _ in range(cnt):
            cp, gi = struct.unpack_from("<HH", data, off)
            off += 4
            self.cmap[cp] = gi
        self._p = {}

    def page(self, i):
        if i not in self._p:
            self._p[i] = Image.open(os.path.join(FONTDIR, "%s_%04d.png" % (self.name, i))).convert("RGB")
        return self._p[i]

    def glyph_alpha(self, gi):
        W, H, u0, u1, v0, v1, pg = self.recs[gi][:7]
        im = self.page(pg)
        x0 = int(round(u0 * im.width)); y0 = int(round(v0 * im.height))
        x1 = int(round(u1 * im.width)); y1 = int(round(v1 * im.height))
        if not (x1 > x0 and y1 > y0):
            x1, y1 = x0 + max(1, int(W)), y0 + max(1, int(H))
        c = im.crop((x0, y0, x1, y1))
        r, g, b = c.split()
        # ALPHA HEURISTIC -- must be min(), not max(). The atlas pages pack the
        # WHITE latin glyphs used by the HUD right next to saturated RED/GREEN/
        # BLUE/MAGENTA/CYAN/YELLOW copies of CJK and other scripts (verified by
        # viewing combined_0005.png). max(R,G,B) therefore picks up a coloured
        # neighbour and floods the entire crop to ~255 -> solid black blocks for
        # every digit. The latin glyphs are NEUTRAL (R~=G~=B) on black, while the
        # coloured neighbours always have one channel near zero, so min(R,G,B)
        # isolates exactly the neutral glyph. Verified visually: s12_alphacmp.py
        # writes glyph_alpha_min.png / glyph_line_min.png ("10000" legible).
        # Residual artefact: a glyph that abuts a coloured neighbour can pick up
        # a faint smudge (see '4'); it is minor and confined to the glyph edge.
        a = ImageChops.darker(ImageChops.darker(r, g), b)
        return a, self.recs[gi]


class Fonts(object):
    def __init__(self):
        self._f = {}

    def get(self, name):
        if name not in self._f:
            self._f[name] = GlyphFont(name)
        return self._f[name]


def norm_color(c):
    """Handle the alpha/byte scale trap: some blocks are 0..1 floats, others 0..255."""
    if not isinstance(c, dict):
        return (255, 255, 255, 255)
    r, g, b, a = _f(c.get("r", 1)), _f(c.get("g", 1)), _f(c.get("b", 1)), _f(c.get("a", 1))
    if max(r, g, b) > 1.0:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
    if a > 1.0:
        a = a / 255.0
    return tuple(max(0, min(255, int(round(v * 255)))) for v in (r, g, b, a))


# ------------------------------------------------------------------ render

SLOTS = ["TL", "TC", "TR", "CL", "CC", "CR", "BL", "BC", "BR"]
VPOS, HPOS = ("Top", "Centre", "Bottom"), ("Left", "Centre", "Right")


class Renderer(object):
    def __init__(self):
        self.assets = Assets()
        self.fonts = Fonts()
        self.log = []
        self.stats = collections.Counter()
        self.node = None

    # -- StateMaterials selection -------------------------------------
    def pick_state(self, w):
        sm = w.get("StateMaterials") or {}
        if isinstance(sm, dict) and "StateNormal" in sm:
            return ("StateNormal", sm["StateNormal"], sm)
        nine = [k for k in sm
                if len(k) == 13 and k.startswith("State") and k[5:7] in SLOTS
                and k[7:] in ("Normal", "Disabled")]
        nine += [k for k in sm
                 if len(k) == 15 and k.startswith("State") and k[5:7] in SLOTS
                 and k[7:] in ("Normal", "Disabled")]
        if nine:
            return ("NineSlice", None, sm)
        if "UserState0" in sm:
            return ("UserState0", sm["UserState0"], sm)
        for k in sm:
            if k != "UserStates" and isinstance(sm[k], dict):
                return (k, sm[k], sm)
        return (None, None, sm)

    def widget_font(self, w, st):
        f = w.get("Font")
        if not f and isinstance(st, dict):
            f = st.get("Font")
        return f

    # -- draw primitives ---------------------------------------------
    def blit(self, canvas, im, rect, blend, tag):
        x, y, w, h = [int(round(v)) for v in rect]
        if w <= 0 or h <= 0 or im is None:
            return
        src = im
        if (src.width, src.height) != (w, h):
            src = src.resize((w, h), LR)
        rx0, ry0 = max(0, x), max(0, y)
        rx1, ry1 = min(CANVAS_W, x + w), min(CANVAS_H, y + h)
        if rx1 <= rx0 or ry1 <= ry0:
            self.stats["draw_clipped_offcanvas"] += 1
            return
        if (rx0, ry0, rx1, ry1) != (x, y, x + w, y + h):
            self.stats["draw_partially_clipped"] += 1
            src = src.crop((rx0 - x, ry0 - y, rx1 - x, ry1 - y))
        if blend == "None":
            canvas.paste(src.convert("RGB"), (rx0, ry0))
        else:
            layer = Image.new("RGBA", (rx1 - rx0, ry1 - ry0), (0, 0, 0, 0))
            layer.paste(src, (0, 0))
            canvas.alpha_composite(layer, (rx0, ry0))
        if blend == "AlphaPlayerColor":
            self.stats["blend_alphaplayercolor_untinted"] += 1

    def solid(self, canvas, color, rect, blend):
        x, y, w, h = [int(round(v)) for v in rect]
        if w <= 0 or h <= 0:
            return
        rx0, ry0 = max(0, x), max(0, y)
        rx1, ry1 = min(CANVAS_W, x + w), min(CANVAS_H, y + h)
        if rx1 <= rx0 or ry1 <= ry0:
            return
        tile = Image.new("RGBA", (rx1 - rx0, ry1 - ry0), color)
        if blend == "None":
            canvas.paste(tile.convert("RGB"), (rx0, ry0))
        else:
            canvas.alpha_composite(tile, (rx0, ry0))

    def draw_text(self, canvas, text, rect, font, anchor, tag):
        if not text:
            return False
        scale = _f(font.get("PointSize", 32)) / font_scale_base(font)
        fi = int(_f(font.get("FontIndex", 0)))
        fname = FONT_TABLE.get(fi) or FONT_FALLBACK.get(fi)
        fb = fi not in FONT_TABLE
        if fname is None:
            self.stats["text_font_unresolved"] += 1
            fname = "combined"; fb = True
        gf = self.fonts.get(fname)
        col = norm_color(font.get("TextColor"))
        ocol = norm_color(font.get("TextOutlineColor"))
        ow = _f(font.get("TextOutlineWidth", 0))
        glyphs = []
        pen = 0.0
        for ch in text:
            gi = gf.cmap.get(ord(ch))
            if gi is None:
                self.stats["text_missing_glyph"] += 1
                continue
            g = gf.recs[gi]
            glyphs.append((pen, gi, g))
            pen += g[9] * scale
        if not glyphs:
            return False
        total_w = pen
        # VERTICAL METRICS -- derived from the .box records, not assumed.
        # s11_glyphdiag.py measured YO+H for baseline-resting glyphs:
        #   'A' 42.689  '0' 43.689  'a' 43.592  '.' 43.555
        # i.e. YO+H is CONSTANT (~43.6 px at the 64 px master) for every glyph
        # that sits on the baseline, and LARGER only for descenders (',' 52.581).
        # So YO is the glyph TOP offset measured down from the line origin, and
        # YO+H is the baseline offset. Glyphs must therefore be placed by their
        # own YO -- bottom-aligning them (the first implementation) would drag a
        # comma's ink up to the baseline instead of letting it hang below.
        asc = max((g[8] + g[1]) for _, _, g in glyphs) * scale
        top_min = min(g[8] for _, _, g in glyphs) * scale
        x, y, w, h = rect
        v, hz = split_align(anchor)
        if hz == "Left":
            ox = x
        elif hz == "Centre":
            ox = x + w / 2.0 - total_w / 2.0
        else:
            ox = x + w - total_w
        # oy = the line origin that YO is measured from. The anchor positions the
        # line box; [I] the line box height is taken as the observed ascent.
        if v == "Top":
            oy = y
        elif v == "Centre":
            oy = y + h / 2.0 - asc / 2.0
        else:
            oy = y + h - asc
        pad = int(math.ceil(ow * _f(font.get("PointSize", 32)))) + 2
        bw = int(math.ceil(total_w)) + 2 * pad + 4
        bh = int(math.ceil(asc - top_min)) + 2 * pad + 4
        mask = Image.new("L", (bw, bh), 0)
        for px, gi, g in glyphs:
            a, rec = gf.glyph_alpha(gi)
            gw = max(1, int(round(rec[0] * scale)))
            gh = max(1, int(round(rec[1] * scale)))
            a = a.resize((gw, gh), LR)
            gx = pad + 1 + int(round(px))
            gy = pad + 1 + int(round((rec[8] - top_min) * scale))
            if gy + gh > bh or gx + gw > bw or gx < 0 or gy < 0:
                continue
            tmp = Image.new("L", (bw, bh), 0)
            tmp.paste(a, (gx, gy), a)
            mask = ImageChops.lighter(mask, tmp)
        rgba = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        if ow > 0:
            om = mask.filter(ImageFilter.MaxFilter(2 * pad + 1))
            rgba.paste(Image.new("RGBA", (bw, bh), (ocol[0], ocol[1], ocol[2], 255)), (0, 0), om)
        fill = Image.new("RGBA", (bw, bh), (col[0], col[1], col[2], col[3]))
        rgba.paste(fill, (0, 0), mask)
        tx = int(round(ox - pad - 1))
        ty = int(round(oy + top_min - pad - 1))
        self.alpha_paste(canvas, rgba, tx, ty)
        if fb:
            self.stats["text_font_fallback_used"] += 1
        self.stats["text_rendered"] += 1
        return True

    def alpha_paste(self, canvas, im, x, y):
        rx0, ry0 = max(0, x), max(0, y)
        rx1, ry1 = min(CANVAS_W, x + im.width), min(CANVAS_H, y + im.height)
        if rx1 <= rx0 or ry1 <= ry0:
            self.stats["text_clipped_offcanvas"] += 1
            return
        sub = im.crop((rx0 - x, ry0 - y, rx1 - x, ry1 - y))
        canvas.alpha_composite(sub, (rx0, ry0))

    # -- widgets ------------------------------------------------------
    def draw_base(self, canvas, w, rect, st, tag):
        # `st` is already the picked state value, e.g. {"Material": "ResourceWood"}
        if not isinstance(st, dict):
            st = None
        mat = (st or {}).get("Material")
        override = (st or {}).get("Color")
        im, col, status, detail, blend = self.assets.resolve(mat)
        self.stats["art_widgets"] += 1
        self.stats["art_" + status] += 1
        if blend:
            self.stats["blend_" + str(blend)] += 1
        ok = status.startswith("OK")
        if status == "NOOP":
            self.stats["art_NOOP_not_a_failure"] += 1
            return
        if not ok:
            self.stats["art_FAIL"] += 1
            self.log.append(dict(widget=tag, name=w.get("Name"), type=w.get("Type"),
                                 material=mat, status=status, detail=detail, rect=rect))
            return
        if col is not None:
            if isinstance(override, dict):
                col = norm_color(override)
            self.solid(canvas, col, rect, blend)
        elif im is not None:
            self.blit(canvas, im, rect, blend, tag)
        if status == "NOOP":
            pass

    def draw_surround(self, canvas, w, rect, sm, tag):
        box = w.get("Box")
        brect = rect
        if box:
            brect = align_rect(_f(box.get("xorigin")), _f(box.get("yorigin")),
                               _f(box.get("width")), _f(box.get("height")), box.get("alignment"))
        pieces = {}
        for s in SLOTS:
            v = sm.get("State%sNormal" % s) or sm.get("State%sDisabled" % s)
            mat = (v or {}).get("Material")
            im, col, status, detail, blend = self.assets.resolve(mat)
            self.stats["art_widgets"] += 1
            self.stats["art_" + status] += 1
            if blend:
                self.stats["blend_" + str(blend)] += 1
            if not status.startswith("OK"):
                self.stats["art_FAIL"] += 1
                self.log.append(dict(widget=tag, name=w.get("Name"), type="Surround:" + s,
                                     material=mat, status=status, detail=detail, rect=brect))
                pieces[s] = None
                continue
            pieces[s] = (im, col, blend)
        x, y, wd, ht = brect
        if not any(pieces.values()):
            return
        nw = max((p[0].width for p in pieces.values() if p and p[0]), default=0)
        nh = max((p[0].height for p in pieces.values() if p and p[0]), default=0)
        TLw = pieces["TL"][0].width if pieces["TL"] and pieces["TL"][0] else nw
        TLh = pieces["TL"][0].height if pieces["TL"] and pieces["TL"][0] else nh
        TRw = pieces["TR"][0].width if pieces["TR"] and pieces["TR"][0] else nw
        BLh = pieces["BL"][0].height if pieces["BL"] and pieces["BL"][0] else nh
        midw = wd - TLw - TRw
        midh = ht - TLh - BLh
        plan = [
            ("TL", (x, y, TLw, TLh)),
            ("TC", (x + TLw, y, midw, TLh)),
            ("TR", (x + wd - TRw, y, TRw, TLh)),
            ("CL", (x, y + TLh, TLw, midh)),
            ("CC", (x + TLw, y + TLh, midw, midh)),
            ("CR", (x + wd - TRw, y + TLh, TRw, midh)),
            ("BL", (x, y + ht - BLh, TLw, BLh)),
            ("BC", (x + TLw, y + ht - BLh, midw, BLh)),
            ("BR", (x + wd - TRw, y + ht - BLh, TRw, BLh)),
        ]
        for s, r in plan:
            p = pieces.get(s)
            if not p or (p[0] is None and p[1] is None):
                continue
            if p[1] is not None:
                self.solid(canvas, p[1], r, p[2])
            else:
                self.blit(canvas, p[0], r, p[2], tag + ":" + s)

    def draw_widget(self, canvas, w, origin, depth, path):
        t = w.get("Type")
        name = w.get("Name")
        tag = "%s/%s" % (path, name)
        self.stats["widgets"] += 1
        self.stats["type_" + str(t)] += 1
        ox, oy = origin
        rect = None
        if w.get("ViewPort"):
            v = w["ViewPort"]
            r = align_rect(_f(v.get("xorigin")), _f(v.get("yorigin")),
                           _f(v.get("width")), _f(v.get("height")), v.get("alignment"))
            rect = (ox + r[0], oy + r[1], r[2], r[3])
            self.stats["has_viewport"] += 1
        elif w.get("Anchor"):
            a = w["Anchor"]
            r = align_rect(_f(a.get("xorigin")), _f(a.get("yorigin")), 0, 0, a.get("alignment"))
            rect = (ox + r[0], oy + r[1], 0, 0)
            self.stats["anchor_only"] += 1
        else:
            self.stats["no_geometry"] += 1
            rect = (ox, oy, 0, 0)
        kind, state, sm = self.pick_state(w)
        self.stats["state_" + str(kind)] += 1
        if t == "Surround" and kind == "NineSlice":
            self.draw_surround(canvas, w, rect, sm, tag)
        elif t in ("Base", "Button", "ProgressBar", "CheckBox", "UserIcon", "RotatingImage",
                   "CommandButton", "CampaignButton", "TechTreeButton", "OptionsPanel",
                   "Bar", "MapView", "TimeLine", "RotateableBase", "Carousel"):
            if t in ("Bar", "MapView", "TimeLine", "RotateableBase", "Carousel", "OptionsPanel"):
                self.stats["type_approximated_as_base_" + str(t)] += 1
            self.draw_base(canvas, w, rect, state if isinstance(state, dict) else sm, tag)
        elif t == "Anchor":
            self.stats["anchor_no_art"] += 1
        elif t == "Label":
            self.stats["text_widgets"] += 1
            f = self.widget_font(w, state)
            txt = w.get("Text")
            if txt is None:
                self.stats["text_no_text_field"] += 1
                self.log.append(dict(widget=tag, name=name, type=t, material=None,
                                     status="TEXT_NO_TEXT_FIELD",
                                     detail="Font present=%s, text runtime-supplied" % bool(f),
                                     rect=rect))
            elif f is None:
                self.stats["text_no_font"] += 1
                self.log.append(dict(widget=tag, name=name, type=t, material=None,
                                     status="TEXT_NO_FONT", detail="Text=%r" % txt, rect=rect))
            else:
                self.stats["text_widgets_with_text"] += 1
                if self.draw_text(canvas, txt, rect, f, w.get("TextAnchor", "TopLeft"), tag):
                    self.stats["text_OK"] += 1
                else:
                    self.stats["text_FAIL"] += 1
        else:
            self.stats["type_UNSUPPORTED_" + str(t)] += 1
            self.log.append(dict(widget=tag, name=name, type=str(t), material=None,
                                 status="TYPE_UNSUPPORTED", detail="", rect=rect))
        # children
        kids = w.get("ChildWidgets") or []
        if kids:
            unwrapped = []
            for i, e in enumerate(kids):
                c = e["Widget"] if isinstance(e, dict) and "Widget" in e else e
                z = _f(c.get("ZPlane", 0)) + _f(c.get("ZPlaneLocalOffset", 0))
                unwrapped.append((z, i, c))
            unwrapped.sort(key=lambda p: (p[0], p[1]))
            for z, i, c in unwrapped:
                self.draw_widget(canvas, c, (rect[0], rect[1]), depth + 1, tag)

    def render(self, layout_path):
        with open(layout_path, encoding="utf-8-sig") as f:
            d = json.load(f)
        col = d.get("Collection")
        canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        v = col.get("ViewPort") or {}
        r = align_rect(_f(v.get("xorigin")), _f(v.get("yorigin")),
                       _f(v.get("width")), _f(v.get("height")), v.get("alignment"))
        self.node = dict(name=col.get("Name"), rect=r)
        for e in (col.get("Widgets") or []):
            w = e["Widget"] if isinstance(e, dict) and "Widget" in e else e
            self.draw_widget(canvas, w, (r[0], r[1]), 1, col.get("Name"))
        return canvas


def font_scale_base(font):
    return 64.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("layouts", nargs="+")
    ap.add_argument("--dbgboxes", action="store_true")
    ap.add_argument("--mod", action="append", default=[],
                    help="mod widgetui dir (or mod root containing widgetui/) to overlay")
    ap.add_argument("--suffix", default="", help="output filename suffix")
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    for m in a.mod:
        root = m
        if os.path.basename(root.rstrip("\\/")) != "widgetui":
            alt = os.path.join(root, "widgetui")
            if os.path.isdir(alt):
                root = alt
        if os.path.isdir(root):
            MOD_ROOTS.append(root)
            print("[mod] overlay root: %s" % root)
        else:
            print("[mod] WARNING not a directory: %s" % m)
    summary = []
    for lay in a.layouts:
        p = lay if os.path.isabs(lay) else os.path.join(UIDIR, lay)
        r = Renderer()
        canvas = r.render(p)
        base = os.path.splitext(os.path.basename(p))[0] + a.suffix
        out = os.path.join(OUTDIR, base + "_4k.png")
        canvas.save(out)
        dbgd = None
        if a.dbgboxes:
            dbgd = canvas.copy()
            dr = ImageDraw.Draw(dbgd)
            for e in r.log:
                if e.get("rect"):
                    x, y, w, h = e["rect"]
                    dr.rectangle([x, y, x + w, y + h], outline=(255, 0, 0, 255), width=2)
            dbgd.save(os.path.join(OUTDIR, base + "_4k_failloc.png"))
        with open(os.path.join(OUTDIR, base + "_fidelity.json"), "w", encoding="utf-8") as f:
            json.dump(dict(layout=os.path.basename(p), node=r.node,
                           stats=dict(r.stats), failures=r.log), f, indent=1, ensure_ascii=False)
        lines = ["=== %s -> %s" % (os.path.basename(p), out)]
        for k in sorted(r.stats):
            lines.append("  %-42s %d" % (k, r.stats[k]))
        lines.append("  --- failure/detail log (%d) ---" % len(r.log))
        for e in r.log:
            lines.append("  %-18s %-22s %-26s %s" % (e["type"], e["name"], e["status"], e["detail"]))
        txt = "\n".join(lines)
        open(os.path.join(OUTDIR, base + "_fidelity.txt"), "w", encoding="utf-8").write(txt)
        print(txt)
        summary.append(txt)
    return summary


if __name__ == "__main__":
    main()
