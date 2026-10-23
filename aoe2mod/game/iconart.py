# -*- coding: utf-8 -*-
"""Give a new unit an icon that is not the donor's.

The warning this module retires said the icon layer was "not implemented": the
game's own `icons.json` Units section already carries keys 000..999, and a new
unit has no key of its own.  That was true as a statement about this toolkit and
false as a statement about the game -- measured 2026-10-23 on a shipped,
subscribed UI mod (`[UI]7V1_Three Kingdoms`): it widens Units to 2149 keys, of
which 127 point at real material names (`lt_soldier_unit_000` …), and every one
of those materials is a *Texture*-type material backed by its own `.dds` under
`widgetui/textures/ingame/units/`.

The three pieces, each measured rather than assumed:

1. **A picture file.**  The game reads uncompressed 32-bit BGRA DDS
   (`aoe2mod.game.ddstex.encode_bgra` writes one and `decode` reads it back
   pixel-for-pixel).  539 of the 794 shipped unit icons are exactly that shape;
   the other 255 are DXT5, which this project cannot encode -- so a picture is
   always emitted uncompressed, which is the majority shape, not a workaround.
2. **A material.**  `widgetui/materials.json` holds `Materials` (each wrapped in
   `{"MaterialDef": …}`) and `GlobalTextures` (each wrapped in
   `{"TextureDef": …}`, keys `Name`/`FileName`/`Cached`).  A Texture-type
   material names itself in `TextureRef`, and the `TextureDef` of the same name
   supplies `FileName`.  No atlas is involved, so nothing has to be re-sliced.
3. **A slot.**  `widgetui/icons.json` Units keys are three-digit strings; the
   engine accepts beyond 999 (the mod above reaches 2148) and the unit record's
   icon field is an `i16`, so the ceiling is 32767, not 999.

Two shapes are load-bearing and easy to get wrong:

* Both files must be the **whole merged table**, not a patch.  The mod above
  keeps every base key (`mod keeps base: True` for both files) because the
  engine reads the file the mod ships, in place of the one on disk.
* `FileName` is relative to `widgetui/`, so the DDS goes to
  `widgetui/textures/ingame/units/<stem>.dds` and the entry says
  `textures/ingame/units/<stem>.dds`.

Nothing here writes into the game folder.  Every function returns bytes.
"""
import io
import json
import os
import re

from . import ddstex as D

ICONS_REL = os.path.join("widgetui", "icons.json")
MATERIALS_REL = os.path.join("widgetui", "materials.json")
TEXTURE_DIR = "textures/ingame/units"

# The game draws icons at 256x256; so does every shipped icon and so does the
# UI mod above (`lt_soldier_unit_000.dds` is 262272 B = 128 + 256*256*4).
SIDE = 256

# Units keys are zero-padded to three digits in the shipped table, then keep
# growing as plain numbers past 999 (the mod above ends at "2148").
FIRST_FREE = 1000
MAX_SLOT = 32767            # the unit record's icon field is an i16


class IconError(Exception):
    """A picture, a table or a slot cannot be used, with a reason in Chinese."""


def _load_json(path):
    raw = io.open(path, "rb").read()
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except ValueError as exc:
        raise IconError("读不出 %s：它不是有效的 JSON（%s）" % (path, exc))


def shipped(game_root):
    """-> (icons_doc, materials_doc) as the game ships them."""
    return (_load_json(os.path.join(game_root, ICONS_REL)),
            _load_json(os.path.join(game_root, MATERIALS_REL)))


def _slots(icons_doc):
    return {int(k) for k in (icons_doc.get("Units") or {}) if str(k).isdigit()}


def next_slot(icons_doc):
    """The first Units key at or above 1000 that the table does not already use."""
    used = _slots(icons_doc)
    slot = FIRST_FREE
    while slot in used:
        slot += 1
    if slot > MAX_SLOT:
        raise IconError("图标槽已经用到 %d，超过单位记录能存的上限 %d"
                        % (slot, MAX_SLOT))
    return slot


def _materials(materials_doc):
    by_name = {}
    for entry in materials_doc.get("Materials") or []:
        d = entry.get("MaterialDef") or {}
        if d.get("Name"):
            by_name[d["Name"]] = d
    textures = {}
    for entry in materials_doc.get("GlobalTextures") or []:
        d = entry.get("TextureDef") or {}
        if d.get("Name"):
            textures[d["Name"]] = d
    return by_name, textures


def _slice_uv(tex_entry):
    """The UV rect of an atlas slice, kept so a reskin does not lose the frame."""
    return {k: tex_entry.get(k) for k in ("imageTLX", "imageTLY",
                                         "imageBRX", "imageBRY")}


def atlas_source(materials_doc, material_name):
    """-> dict(file, uv, atlas) for an Atlas-type material, or None.

    Needed because the shipped unit icons are atlas slices of one big sheet; the
    loose FileName under the slice IS the whole icon (measured: uv * atlas size
    equals the file's own pixel size for 1,211 of 1,211 entries), so reading that
    file gives the picture without needing to crop anything.
    """
    by_name, _textures = _materials(materials_doc)
    d = by_name.get(material_name)
    if not d or d.get("Type") != "Atlas":
        return None
    wanted = d.get("TextureRef") or material_name
    for entry in materials_doc.get("AtlasTextures") or []:
        at = entry.get("AtlasDef") or {}
        for tex in at.get("Textures") or []:
            if tex.get("RefName") == wanted:
                return {"file": tex.get("FileName"),
                        "uv": _slice_uv(tex),
                        "atlas": at.get("Name")}
    return None


def _clean_stem(name):
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", name or "newicon").strip("_")
    if not stem:
        stem = "newicon"
    if not stem[0].isalpha():
        stem = "icon_" + stem
    return stem[:48]


def _open_picture(path):
    """-> a PIL image whose header has been read, or raise IconError in Chinese.

    Only the header is parsed here (`Image.open` is lazy), which is what makes it
    affordable on the preview path -- the page plans on every keystroke.  The
    full decode still happens in `_rgba_from_picture`, because a file can pass the
    header check and still be truncated.
    """
    try:
        from PIL import Image
    except ImportError:                             # pragma: no cover
        raise IconError("这个版本装不了图片读取组件（Pillow），没法读你给的图片")
    if not os.path.isfile(path):
        raise IconError("找不到这张图片：%s" % path)
    try:
        return Image.open(path)
    except Exception:                               # noqa: BLE001
        # Measured 2026-10-23: a text file named .png reached the build, which
        # answered with PIL's own English sentence.  The type name is the only
        # part a player could act on, and even that only means "this is not a
        # picture", so say that plainly instead of pasting the exception.
        raise IconError("这张图片打不开：%s 不是一张能识别的图片"
                        "（支持 PNG、JPG、BMP、GIF）" % os.path.basename(path))


def check_picture(path):
    """-> (width, height) of the source picture, or raise IconError.

    Exists so the PREVIEW can refuse what the BUILD would refuse.  The plan used
    to allocate a slot and report `editable: True` for any path that existed,
    and the build then died decoding it -- measured 2026-10-23 with a text file
    named `not_a_picture.png`: plan said edit_count=3, build raised.
    """
    img = _open_picture(path)
    try:
        size = img.size
    finally:
        try:
            img.close()
        except Exception:                           # noqa: BLE001
            pass
    w, h = size
    if w <= 0 or h <= 0:
        raise IconError("这张图片是空的（%dx%d）" % (w, h))
    return w, h


def _rgba_from_picture(path, side=SIDE):
    """Any picture PIL can open -> (side, side, RGBA bytes), letterboxed on alpha 0.

    The letterbox is deliberate: a 200x100 logo squashed to a square would look
    wrong on a square button, and silently cropping it would hide most of the
    picture.  Fitting keeps the whole thing and leaves transparent margins.
    """
    from PIL import Image
    img = _open_picture(path)
    try:
        img.load()
    except Exception:                               # noqa: BLE001
        raise IconError("这张图片读到一半失败，文件可能是坏的：%s"
                        % os.path.basename(path))
    img = img.convert("RGBA")
    w, h = img.size
    if w <= 0 or h <= 0:
        raise IconError("这张图片是空的（%dx%d）" % (w, h))
    scale = min(float(side) / w, float(side) / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    img = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - nw) // 2, (side - nh) // 2))
    return side, side, canvas.tobytes()


def plan(icons_doc, materials_doc, picture, stem=None, slot=None):
    """-> what the build will do, without doing it.

    Returns the slot, the material name, the two file paths and the picture's
    own pixel size, so the preview can say exactly which numbers change.
    """
    if slot is None:
        slot = next_slot(icons_doc)
    slot = int(slot)
    if slot < FIRST_FREE or slot > MAX_SLOT:
        raise IconError("图标槽只能取 %d..%d，拿到的是 %d"
                        % (FIRST_FREE, MAX_SLOT, slot))
    units = icons_doc.get("Units") or {}
    if str(slot) in units and units[str(slot)] not in (None, "None"):
        raise IconError("第 %d 号图标槽已经被「%s」占了，换一个号"
                        % (slot, units[str(slot)]))
    by_name, textures = _materials(materials_doc)
    material = _clean_stem(stem)
    if material in by_name:
        raise IconError("材质表里已经有叫「%s」的材质了，换个名字" % material)
    if material in textures:
        raise IconError("贴图表里已经有叫「%s」的贴图了，换个名字" % material)
    side = SIDE
    file_rel = "%s/%s.dds" % (TEXTURE_DIR, material)
    return {"slot": slot, "key": str(slot).zfill(3) if slot < 1000 else str(slot),
            "material": material, "file_rel": file_rel, "side": side,
            "icons_rel": ICONS_REL, "materials_rel": MATERIALS_REL}


def emit(icons_doc, materials_doc, label, rgba, side=SIDE, slot=None,
         stem=None):
    """-> {relative_path: bytes} for the whole icon layer.

    `label` is the slot key as the table spells it; `rgba` is `side*side*4` bytes.
    Both JSON files come back as the full merged table -- see the module
    docstring for why a patch would not work.
    """
    import copy

    icons = copy.deepcopy(icons_doc)
    materials = copy.deepcopy(materials_doc)
    if slot is None:
        slot = next_slot(icons)
    slot = int(slot)
    material = _clean_stem(stem)
    dds_rel = "%s/%s.dds" % (TEXTURE_DIR, material)
    key = str(slot).zfill(3) if slot < 1000 else str(slot)

    units = icons.setdefault("Units", {})
    if key in units and units[key] not in (None, "None"):
        raise IconError("第 %d 号图标槽已经被「%s」占了" % (slot, units[key]))
    units[key] = material

    materials.setdefault("Materials", []).append(
        {"MaterialDef": {"Name": material, "Type": "Texture",
                         "TextureRef": material, "Blend": "AlphaPlayerColor"}})
    # The texture entry is keyed by the MATERIAL's name, because that is the name
    # a Texture-type MaterialDef resolves through `TextureRef` (measured on the
    # 三国 mod: all 127 of its added icon materials have a TextureDef of exactly
    # the same name; a "-tex" suffix would resolve to nothing).
    materials.setdefault("GlobalTextures", []).append(
        {"TextureDef": {"Name": material, "FileName": dds_rel,
                        "Cached": "none"}})

    blob = D.encode_bgra(side, side, rgba)
    # TWO different paths on purpose.  `TextureDef.FileName` is resolved
    # relative to `widgetui/`, so it says `textures/ingame/units/x.dds`; the
    # file inside the MOD folder must therefore sit one level deeper.  Shipping
    # it at the bare relative path put the picture at the mod root, where the
    # texture lookup never finds it -- measured 2026-10-23 on a real build: the
    # JSON named `textures/ingame/units/newicon.dds` and that is where the file
    # landed, next to `info.json` rather than under `widgetui/`.
    return {_mod_rel(dds_rel): blob,
            ICONS_REL.replace(os.sep, "/"): _dump(icons),
            MATERIALS_REL.replace(os.sep, "/"): _dump(materials)}


def _mod_rel(file_name):
    """Where a texture's file goes INSIDE the mod, given its `FileName`."""
    return os.path.join("widgetui", file_name).replace(os.sep, "/")


def _dump(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
