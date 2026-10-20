# -*- coding: utf-8 -*-
"""Can the menu layer ever be turned into an editor?  Static answer: no to
"execute our code", yes to "restyle and rearrange the screens that exist".

The question came from the player (m11818): if we reverse-engineered the game,
could we replace it with an editor of our own imagining?  The answer turns on
one fact about the menu layer, and this probe measures it instead of assuming.

WHAT THIS PROBE PROVES, and how
-------------------------------
A. AoE2DE_s.exe is a NATIVE executable with no managed runtime.
   - PE32+ (machine 0x8664, optional magic 0x20b), 16 data directories,
     IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR rva=0 size=0  -> no CLR header.
   - zero occurrences of b"bsjb" (metadata signature), b"mscorlib",
     b"PresentationFramework", b"PresentationCore", b"WindowsBase",
     b"GeneratedInternalTypeHelper", b"Baml", b"coreclr", b"hostfxr";
     zero of "WPFUI/..." other than the game's own name strings.
   - the ONLY managed binaries in the whole install are four unrelated .NET 4
     tools: WebClient.exe, webclient\\winlive-webclient.exe,
     Tools_Builds\\Microsoft.WindowsAPICodePack.dll and .Shell.dll.
   => the .xaml files' <?xml ... x:Class=?  style headers, xmlns:d=blend/2008,
      clr-namespace:aoe2wpfg and all, are a LOOKALIKE dialent parsed by the
      game's own native code.  Nothing loads a CLR assembly, so no mod can add
      a type or a method that the exe would run.

B. But the wpfg tree IS a mod-visible resource root, and the markup is NOT
   embedded in the exe.
   - the engine's resource-root string table contains
       'widgetui\\'  and  'resources\\_common\\wpfg\\'
     as PEERS, in one contiguous block of ~50 root paths.  widgetui's loose-file
     override is already proven in-game (see the aoe2-de-ui-textures skill), so
     a root in this table is a root a loose file can land in.
   - 233 .xaml files, 3,321,293 bytes on disk.  The exe holds only
       21x "xmlns=", 13x "<StackPanel", 4x "<Grid", 1x "<?xml", 13x "Storyboard"
     and ~8 KB of tag names total, so the 3.3 MB markup tree is not in the
     image.  The disk copies are the ones read.
   - the exe names 57 "/WPFUI/...xaml" paths; 54 exist on disk, and the 3 that
     do not are Testbed frames.  So it looks markup up BY PATH.
   => a mod that ships resources/_common/wpfg/<same path> is structurally in
      the same position as a mod that ships a loose PNG: same root table, same
      by-name lookup, markup resident on disk.

C. The set of widget classes is CLOSED and compiled in.
   - 200 distinct "WPFUI::<Namespace>::<Name>" symbols, each Component having a
     "...Base" twin (PhoenixButton / PhoenixButtonBase, DarkGoldFrame /
     DarkGoldFrameBase, ...).  That pairing is a native class-registry
     convention, not .NET reflection output.
   - they are grouped by menu: Common, Palm (DLC pages), Paphos (civ selection,
     campaign, camera view), Paris/Peru/Portland (campaigns), Pine (main menu,
     social), Testbed.
   => an existing class can be restyled and a screen can be rearranged, because
      those are data.  A NEW kind of widget cannot exist, because the class it
      would instantiate is not in the image.

D. A PUBLISHED MOD ALREADY SHIPS INTO THAT ROOT.
   - the player's subscribed theme mod `550412_透明主题整合自用` carries 50 files
     under resources/_common/wpfg/resources/, 49 of which have the exact same
     relative path as a file in the game tree -- i.e. they sit on the same
     lookup, not in a private corner -- and 29 of those 49 DIFFER from the
     game's copy.  So a loose file landing in wpfg is not a hypothesis.
   - This leg is machine state, so a missing theme mod is a SKIP with a printed
     reason, never a silent pass.  It also must pick the account folder the way
     the product does: taking the first alphabetical one found `0` (a leftover
     local mod) and skipped while the mod was right there.

HONESTY BOUNDARY -- read this before quoting the result
------------------------------------------------------
None of the above is an in-game observation.  B proves the PRECONDITION for a
loose-file layout mod (a mod-visible root, markup read from disk, lookup by
path) and D shows a shipped mod already puts real files there; neither proves
that replacing a .xaml changes what the player sees.  That would need the same
kind of one-file mod test the panel experiment used, and this probe
deliberately does not claim it.  What IS proven and relevant: no amount of
reversing makes the game run our code, because there is no code loader in it --
which is the part of the player's question that has a hard answer.
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GAME = os.environ.get("AOE2DE_GAME_ROOT") or r"D:\Games\Steam\steamapps\common\AoE2DE"
EXE = os.path.join(GAME, "AoE2DE_s.exe")
WPFG = os.path.join(GAME, "resources", "_common", "wpfg")

CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok), detail))
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                        ("  :: " + detail) if detail else ""))
    return ok


def pe_facts(path):
    with open(path, "rb") as fh:
        head = fh.read(0x400)
    e = struct.unpack_from("<I", head, 0x3C)[0]
    machine = struct.unpack_from("<H", head, e + 4)[0]
    magic = struct.unpack_from("<H", head, e + 24)[0]
    dd = e + 24 + (112 if magic == 0x20B else 96)
    n_dirs = struct.unpack_from("<I", head, dd - 4)[0]
    rva = size = 0
    if n_dirs > 14:
        rva, size = struct.unpack_from("<II", head, dd + 14 * 8)
    return machine, magic, n_dirs, rva, size


def main():
    print("== A. the exe is native, not managed ==")
    with open(EXE, "rb") as fh:
        head = fh.read(0x400)
    check("PE signature present", head[:2] == b"MZ")
    machine, magic, n_dirs, rva, size = pe_facts(EXE)
    check("PE32+ x86-64", machine == 0x8664 and magic == 0x20B,
          "machine=%#06x magic=%#06x" % (machine, magic))
    check("no CLR header (COM descriptor directory is empty)",
          rva == 0 and size == 0, "rva=%#x size=%d dirs=%d" % (rva, size, n_dirs))

    data = open(EXE, "rb").read()
    for needle in (b"bsjb", b"mscorlib", b"PresentationFramework",
                   b"PresentationCore", b"WindowsBase", b"Baml",
                   b"GeneratedInternalTypeHelper", b"coreclr", b"hostfxr"):
        check("exe does not mention %s" % needle.decode(), data.count(needle) == 0,
              "count=%d" % data.count(needle))

    print()
    print("== B. wpfg is a mod-visible root and its markup lives on disk ==")
    i = data.find(b"resources\\_common\\wpfg\\")
    check("the resource-root table names resources\\_common\\wpfg\\", i >= 0,
          "@%d" % i if i >= 0 else "not found")
    # The root table is one contiguous run of NUL-separated root paths.  Measure
    # that run instead of guessing a window width: a hardcoded +-1200 byte block
    # clipped the last entry and reported a false failure the first time round.
    # Careful: the same prefix also occurs in unrelated strings elsewhere in the
    # image, so cluster by gap rather than taking min/max of every hit.
    hits = [m.start() for m in
            re.finditer(rb"resources\\_common\\[A-Za-z0-9_]+[\\/]?[A-Za-z0-9_]*", data)]
    clusters, cur = [], [hits[0]]
    for a, b in zip(hits, hits[1:]):
        if b - a > 512:
            clusters.append(cur)
            cur = [b]
        else:
            cur.append(b)
    clusters.append(cur)
    run = max(clusters, key=len)
    check("the root table is one contiguous run of NUL-separated roots",
          len(run) >= 20 and run[-1] - run[0] < 4000,
          "%d roots in the largest cluster, spanning %d bytes (@%d..@%d); %d clusters total"
          % (len(run), run[-1] - run[0], run[0], run[-1], len(clusters)))
    check("wpfg sits inside that run, between two other data roots",
          run[0] < i < run[-1])
    # widgetui immediately before it is what makes the comparison meaningful:
    # widgetui's loose-file override is already proven in game.
    j = data.find(b"widgetui\\")
    check("widgetui\\ is its immediate neighbour in the table", 0 <= i - j <= 200,
          "widgetui @%d, wpfg @%d, %+d bytes apart" % (j, i, i - j))

    disk_n = disk_b = 0
    for dirpath, _d, files in os.walk(WPFG):
        for fn in files:
            if fn.lower().endswith(".xaml"):
                disk_n += 1
                disk_b += os.path.getsize(os.path.join(dirpath, fn))
    check("the disk tree has a real markup forest", disk_n >= 200 and disk_b > 2_000_000,
          "%d files / %s bytes" % (disk_n, format(disk_b, ",")))
    embedded = (data.count(b"<StackPanel") + data.count(b"<Grid")
                + data.count(b"<ResourceDictionary") + data.count(b"Storyboard"))
    check("that forest is not embedded in the exe", embedded * 400 < disk_b,
          "%d markup tags vs %s disk bytes" % (embedded, format(disk_b, ",")))
    check("the exe still names .xaml as a file it opens", data.count(b".xaml") >= 20,
          "count=%d" % data.count(b".xaml"))

    named = sorted(set(m.group(0) for m in re.finditer(rb"/WPFUI/[A-Za-z0-9_/\.]+\.xaml", data)))
    on_disk = [p for p in named
               if os.path.exists(os.path.join(WPFG, p.decode().lstrip("/").replace("/", os.sep)))]
    check("every markup path the exe names exists on disk (bar the Testbed frames)",
          len(named) >= 40 and len(on_disk) >= len(named) - 4,
          "%d named, %d on disk" % (len(named), len(on_disk)))
    stray = [p.decode() for p in named if p not in on_disk]
    check("the exceptions are the Testbed frames, which ship only in the exe",
          all("Testbed" in p for p in stray), repr(stray))

    print()
    print("== C. the widget class set is closed ==")
    names = set()
    for m in re.finditer(rb"WPFUI::[A-Za-z0-9_:]+", data):
        names.add(m.group(0).decode("ascii"))
    comps = sorted(n for n in names if "::Components::" in n)
    stems = sorted(set(n.rsplit("::", 1)[-1] for n in comps))
    bases = [s for s in stems if s.endswith("Base")]
    plain = [s for s in stems if not s.endswith("Base")]
    paired = [s for s in plain if s + "Base" in stems]
    unpaired = [s for s in plain if s + "Base" not in stems]
    check("the exe registers a named class per component", len(comps) >= 30,
          "%d component symbols, %d stems (%d plain, %d ...Base)"
          % (len(comps), len(stems), len(plain), len(bases)))
    # MOST, not all: 43 of 51 plain stems have a ...Base twin.  Asserting "every
    # component pairs" is the kind of over-claim this project keeps paying for;
    # the 8 exceptions are recorded below so a future reading cannot drift.
    check("most components come in a Class/ClassBase pair",
          len(paired) >= 40 and len(paired) * 4 >= len(plain) * 3,
          "%d of %d plain stems have a Base twin" % (len(paired), len(plain)))
    check("the unpaired ones are leaf helpers, not mysteriously missing bases",
          len(unpaired) <= 10
          and all(s in ("ButtonKind", "NineSliceBackground", "TextScrollPanel",
                        "UserIconRankBorder", "CustomNavigationScrollViewer",
                        "PineGroupLabel", "PhoenixButton", "PhoenixImageButton")
                  for s in unpaired),
          repr(unpaired))
    groups = set(n.split("::")[1] for n in comps)
    check("the classes are grouped by menu area, i.e. a fixed UI inventory",
          len(groups) >= 3, repr(sorted(groups)))

    print()
    print("== D. a published mod already ships into the wpfg root ==")
    # Suite B argues from the exe's root table that a loose file CAN land in
    # wpfg.  This is the weaker but real-world leg: somebody already did it.
    # The files below are the game's own texture names, so overriding them is
    # overriding the same lookup the base game uses -- not a private copy.
    #
    # These live in the player's profile, which is machine state: a missing
    # theme mod is not a defect of this project.  So it is a SKIP with a printed
    # reason, never a silent pass -- the same rule that keeps install tests from
    # hardcoding a mod list.
    precedent = _theme_mod()
    if precedent is None:
        print("  SKIP  no subscribed mod on this machine ships into wpfg")
        print("        (suite B still stands on the exe's own root table; this")
        print("         leg is a real-world corroboration, not the proof)")
    else:
        name, shipped, theirs, diff, new, same, markup = precedent
        check("a published mod really ships files into resources/_common/wpfg",
              shipped >= 20, "%s :: %d files" % (name, shipped))
        check("those files use the game's own paths, so they override that lookup",
              theirs > 0, "%d of %d exist verbatim in the game tree" % (theirs, shipped))
        # 29 of the 49 differ.  The point is "real overrides, not copies", so the
        # threshold stays loose enough to survive on another machine.
        check("and they are actually different from the game's copies",
              diff >= 10, "%d differ, %d identical, %d new" % (diff, same, new))
        # What is NOT precedented, measured rather than assumed: no installed mod
        # on this machine ships a single .xaml.  This is a NOTE, not a check --
        # "no xaml mod happens to be installed today" is machine state, and a
        # suite that turns red because someone subscribed a layout mod would be
        # crying wolf about something that is not a defect.  It is printed so a
        # later reader can see which half of wpfg has precedent and which half
        # rests on suite B's structural argument alone.
        print("  note  %d .xaml across every installed mod -- the texture half of"
              % markup)
        print("        wpfg has precedent, the MARKUP half has none; that is why")
        print("        the honesty note below still sends .xaml to its own test")

    print()
    bad = [c for c in CHECKS if not c[1]]
    if bad:
        print("UI LAYER: %d OF %d CHECKS FAILED -- %s"
              % (len(bad), len(CHECKS), ", ".join(c[0] for c in bad)))
        return 1
    print("UI LAYER: %d CHECKS PASSED -- native renderer, mod-visible root, "
          "markup on disk, closed class set" % len(CHECKS))
    print("NOT PROVEN HERE: that replacing a .xaml changes what the player sees.")
    print("  B proves the precondition (a root a loose file can land in + markup")
    print("  read from disk + lookup by path).  D shows a published mod already")
    print("  ships into that root with the game's own texture paths.  The .xaml")
    print("  override itself is a separate in-game experiment, of the same shape")
    print("  as the build-panel one.")
    return 0


def _theme_mod():
    """Find a subscribed mod that ships into the wpfg root and measure it.

    Returns (mod_name, shipped, present_in_game, differ, only_in_mod, same,
    markup_across_all_mods) or None when this machine has no such mod.

    The shipped count includes files under wpfg that are NOT under
    wpfg/resources/, so a mod that only ships markup is measured too; the
    present/differ/same tallies stay scoped to the game's own paths, since that
    is the only place a comparison is meaningful.
    """
    import hashlib

    profile = os.environ.get("AOE2DE_PROFILE") or os.path.join(
        os.path.expanduser("~"), "Games", "Age of Empires 2 DE")
    if not os.path.isdir(profile):
        return None
    sub_root = _account(profile)
    if sub_root is None:
        return None
    sub = os.path.join(profile, sub_root, "mods", "subscribed")
    if not os.path.isdir(sub):
        return None
    root_rel = os.path.join("resources", "_common", "wpfg")
    art_rel = os.path.join(root_rel, "resources")

    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    best = None
    for mod in sorted(os.listdir(sub)):
        base = os.path.join(sub, mod, root_rel)
        if not os.path.isdir(base):
            continue
        shipped = present_in_game = differ = new = same = 0
        for dirpath, _d, files in os.walk(base):
            for fn in files:
                p = os.path.join(dirpath, fn)
                shipped += 1
                rel = os.path.relpath(p, base)
                if rel.split(os.sep)[0] != "resources":
                    continue          # markup/other: no base-game twin to compare
                g = os.path.join(os.path.join(GAME, root_rel), rel)
                if not os.path.exists(g):
                    new += 1
                    continue
                present_in_game += 1
                if sha(p) == sha(g):
                    same += 1
                else:
                    differ += 1
        if best is None or shipped > best[1]:
            best = (mod, shipped, present_in_game, differ, new, same,
                    _mods_shipping_markup(sub))
    return best


def _mods_shipping_markup(mods_root):
    """How many .xaml files the installed mods ship, anywhere in their tree."""
    n = 0
    for dirpath, _d, files in os.walk(mods_root):
        for fn in files:
            if fn.lower().endswith(".xaml"):
                n += 1
    return n


def _account(profile_root):
    """Pick the account folder the product would install into.

    Do NOT take the first alphabetical one: this machine has both ``0`` (a
    leftover local mod, no status file) and the SteamID64 (the live profile
    that owns every subscribed mod).  Taking ``0`` made suite D skip while the
    theme mod was sitting right there -- a silent pass caused by picking the
    wrong folder, which is the same trap `pick_account` exists to avoid.
    """
    from aoe2mod.game import locations as L

    try:
        return os.path.basename(L.pick_account(profile_root))
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
