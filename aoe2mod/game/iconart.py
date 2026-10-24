# -*- coding: utf-8 -*-
"""Write the bytes for a unit's own icon, in the shape the game actually draws.

**Read this before trusting the module, including the correction at the end.**
2026-10-24, twenty-odd builds, each one opening a real match and looking at the
command card.  What they looked like at the time:

    v64  icons.json Units["015"] -> a material only the mod defines   empty box
    v71  icons.json Units["015"] -> a SHIPPED material                draws fine
    v69  the same slot -> a Type "Texture" material (the published
         UI mod's exact shape)                                        empty box
    v70  the same slot -> a brand-new atlas we contribute              empty box
    v72  the material in `morematerials.json`                          empty box

That looked like "the engine resolves slot names against the install directory's
material table only, so a material a mod contributes can never be drawn".  **It
was wrong, and the fault was mine.**  Every one of those builds shipped a DDS
whose header set `DDSD_MIPMAPCOUNT` and then wrote a mip count of zero.  Four
single-variable runs on 2026-10-24 separated the two halves:

    flags 0x00081007 (MIPMAPCOUNT set), mip count 0  -> empty box
    flags 0x00081007,                   mip count 1   -> drawn
    flags 0x0000100F (the shipped word), mip count 0  -> drawn
    flags 0x0000100F,                   mip count 1   -> drawn

So it is not "mips are required" and not "that one flag bit is wrong": declaring a
level count and shipping none is the contradiction the engine refuses.  The mod's
own material name **is** resolved and drawn.  `aoe2mod.game.ddstex.encode_bgra`
now writes `0x0000100F` with one level, and the caveat lives there.

The lesson is worth more than the fix: ten identical failures are one experiment
repeated, not ten pieces of evidence.  Every one of them shared the header, so the
header was never a variable until it was made one.

Still unmeasured, and it must stay written down: a new unit carrying its own icon
has never been looked at in a running match.  The data layer (v26..v33) and the
icon layer (v73/v73b/v73c/v73d, which drew a checkerboard on the shipped villager
slot) were each verified on their own; the run that does both has not happened.

Why the earlier belief felt supported, since it is instructive: the published UI
mod (`[UI]7V1_Three Kingdoms`) widens Units to 2149 keys with 127 real material
names, each a Texture-type material backed by its own DDS.  Everything about it
reads like the route works -- and it does.  What it could not tell us is whether
*our* files were well-formed, because "a shipped mod does X" says nothing about
whether *our* X is byte-correct.

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

# Two sections behave the same way but live in different folders, and the only
# shipped example of an extended one used a different FILE FORMAT per section --
# measured 2026-10-23 on `[UI]7V1_Three Kingdoms`:
#   * its 127 added UNIT icons are `textures/ingame/units/lt_soldier_unit_NNN.dds`
#   * its 49 added TECH icons are `textures/ingame/tech/lt_tech_NNN.png`
# So the shape is copied per section rather than generalised: a unit icon is an
# uncompressed DDS (which this project can encode), a tech icon is a PNG (which
# it can also encode, via `ddstex.encode_png`).  Neither has been watched being
# drawn by the game -- that boundary is stated where the build reports.
SECTIONS = {
    "unit": {"section": "Units", "texture_dir": "textures/ingame/units",
             "ext": ".dds"},
    "tech": {"section": "Techs", "texture_dir": "textures/ingame/tech",
             "ext": ".png"},
}
TEXTURE_DIR = SECTIONS["unit"]["texture_dir"]

# The game draws icons at 256x256; so does every shipped icon and so does the
# UI mod above (`lt_soldier_unit_000.dds` is 262272 B = 128 + 256*256*4).
SIDE = 256

# Units keys are zero-padded to three digits in the shipped table, then keep
# growing as plain numbers past 999 (the mod above ends at "2148").  The Techs
# floor is 500 because that is where the only shipped precedent starts; Units
# keep 1000 because the shipped table ends at 999.
FIRST_FREE = {"unit": 1000, "tech": 500}
MAX_SLOT = 32767            # both the unit record's and the tech record's icon
                            # field are i16 -- read out of parser.py, not assumed


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


def _slots(icons_doc, kind="unit"):
    section = SECTIONS[kind]["section"]
    return {int(k) for k in (icons_doc.get(section) or {}) if str(k).isdigit()}


def next_slot(icons_doc, kind="unit"):
    """The first key in that section at or above this project's own floor.

    The floor is a choice, not a rule of the engine: 1000 for units because the
    shipped table stops at 999, 500 for techs because that is where the only
    shipped precedent (`[UI]7V1_Three Kingdoms`: keys 500..548) put its own.  A
    lower free key exists in both sections and using it would be legal, but then
    a future official patch adding a tech could collide with a number that looked
    safe when it was chosen -- the same reason `tech.create` says its id may move.
    """
    used = _slots(icons_doc, kind)
    slot = FIRST_FREE[kind]
    while slot in used:
        slot += 1
    if slot > MAX_SLOT:
        raise IconError("图标槽已经用到 %d，超过记录里那个字段能存的上限 %d"
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


def _clean_stem(name, slot=None, kind=None):
    """A file-safe stem for the material, texture and file name.

    The SLOT NUMBER goes into the name, and that is load-bearing rather than
    cosmetic.  Every character of a Chinese name is stripped by the filter
    below, so 画师学徒 and 血祭 both cleaned down to the empty string and both
    fell back to the same placeholder -- measured 2026-10-23 on a real
    `build_bundle` with one new unit and one new technology: both got the
    material name `newicon`, the second `TextureDef` replaced the first, the
    unit's slot 1000 resolved to the TECHNOLOGY's png, and the unit's own dds
    was shipped but unreachable while both previews said the icon was fine.

    The KIND goes in as well, because the two tables have different floors
    (units free at 1000, technologies at 500) so the same number is reachable
    from both, while `materials.json` is SHARED by both sections.
    """
    stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", name or "icon").strip("_")
    if not stem:
        stem = "icon"
    if not stem[0].isalpha():
        stem = "icon_" + stem
    if kind:
        # STRIP the prefix, then add it back: that is idempotent for every input,
        # including a stem that came from `plan` and already carries it.
        # Without this the second pass turned `tech_icon_500` into
        # `tech_tech_icon_500` -- the tables then named a material `emit` never
        # created, which `_probe/test_tech_create.py` caught as "the new key
        # points at the new material".
        prefix = "%s_" % kind
        while stem.startswith(prefix):
            stem = stem[len(prefix):]
        stem = prefix + stem
    if slot is not None:
        suffix = "_%d" % int(slot)
        # IDEMPOTENT on purpose: the caller feeds `plan`'s material name back
        # into `emit`, so cleaning twice must not produce `icon_1000_1000`.
        if not stem.endswith(suffix):
            stem = stem[:48 - len(suffix)] + suffix
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


def plan(icons_doc, materials_doc, picture, stem=None, slot=None, kind="unit"):
    """-> what the build will do, without doing it.

    Returns the slot, the material name, the two file paths and the picture's
    own pixel size, so the preview can say exactly which numbers change.
    `kind` picks the section: units and techs are separate tables AND separate
    texture folders, and the one shipped precedent used a different file format
    for each, so a single "icon" shape would be wrong for one of them.
    """
    spec = SECTIONS[kind]
    if slot is None:
        slot = next_slot(icons_doc, kind)
    slot = int(slot)
    floor = FIRST_FREE[kind]
    if slot < floor or slot > MAX_SLOT:
        raise IconError("图标槽只能取 %d..%d，拿到的是 %d" % (floor, MAX_SLOT, slot))
    table = icons_doc.get(spec["section"]) or {}
    if str(slot) in table and table[str(slot)] not in (None, "None"):
        raise IconError("第 %d 号图标槽已经被「%s」占了，换一个号"
                        % (slot, table[str(slot)]))
    by_name, textures = _materials(materials_doc)
    material = _clean_stem(stem, slot, kind)
    if material in by_name:
        raise IconError("材质表里已经有叫「%s」的材质了，换个名字" % material)
    if material in textures:
        raise IconError("贴图表里已经有叫「%s」的贴图了，换个名字" % material)
    side = SIDE
    file_rel = "%s/%s%s" % (spec["texture_dir"], material, spec["ext"])
    return {"slot": slot, "key": _key(slot), "material": material,
            "file_rel": file_rel, "side": side, "kind": kind,
            "section": spec["section"],
            "icons_rel": ICONS_REL, "materials_rel": MATERIALS_REL}


def _key(slot):
    """How the tables spell this key: zero-padded below their own first free."""
    return str(slot).zfill(3)


def emit(icons_doc, materials_doc, label, rgba, side=SIDE, slot=None,
         stem=None, kind="unit"):
    """-> {relative_path: bytes} for the whole icon layer.

    `label` is the slot key as the table spells it; `rgba` is `side*side*4` bytes.
    Both JSON files come back as the full merged table -- see the module
    docstring for why a patch would not work.

    A unit icon is written as uncompressed BGRA DDS and a tech icon as PNG,
    because those are the shapes the only shipped precedent used per section.
    Nothing in the engine requires that split -- it is copied from a mod that
    works, which is the strongest evidence available without another run.
    """
    import copy

    spec = SECTIONS[kind]
    icons = copy.deepcopy(icons_doc)
    materials = copy.deepcopy(materials_doc)
    if slot is None:
        slot = next_slot(icons, kind)
    slot = int(slot)
    material = _clean_stem(stem, slot, kind)
    file_rel = "%s/%s%s" % (spec["texture_dir"], material, spec["ext"])
    key = _key(slot)

    table = icons.setdefault(spec["section"], {})
    if key in table and table[key] not in (None, "None"):
        raise IconError("第 %d 号图标槽已经被「%s」占了" % (slot, table[key]))
    table[key] = material

    materials.setdefault("Materials", []).append(
        {"MaterialDef": {"Name": material, "Type": "Texture",
                         "TextureRef": material, "Blend": "AlphaPlayerColor"}})
    # The texture entry is keyed by the MATERIAL's name, because that is the name
    # a Texture-type MaterialDef resolves through `TextureRef` (measured on the
    # 三国 mod: all 127 of its added icon materials have a TextureDef of exactly
    # the same name; a "-tex" suffix would resolve to nothing).
    materials.setdefault("GlobalTextures", []).append(
        {"TextureDef": {"Name": material, "FileName": file_rel,
                        "Cached": "none"}})

    blob = (D.encode_bgra(side, side, rgba) if spec["ext"] == ".dds"
            else D.encode_png(side, side, rgba))
    # TWO different paths on purpose.  `TextureDef.FileName` is resolved
    # relative to `widgetui/`, so it says `textures/ingame/units/x.dds`; the
    # file inside the MOD folder must therefore sit one level deeper.  Shipping
    # it at the bare relative path put the picture at the mod root, where the
    # texture lookup never finds it -- measured 2026-10-23 on a real build: the
    # JSON named `textures/ingame/units/newicon.dds` and that is where the file
    # landed, next to `info.json` rather than under `widgetui/`.
    return {_mod_rel(file_rel): blob,
            ICONS_REL.replace(os.sep, "/"): _dump(icons),
            MATERIALS_REL.replace(os.sep, "/"): _dump(materials)}


def _mod_rel(file_name):
    """Where a texture's file goes INSIDE the mod, given its `FileName`."""
    return os.path.join("widgetui", file_name).replace(os.sep, "/")


def _dump(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
