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

HONESTY BOUNDARY -- read this before quoting the result
------------------------------------------------------
None of the above is an in-game observation.  B proves the PRECONDITION for a
loose-file layout mod (a mod-visible root, markup read from disk, lookup by
path); it does not prove that replacing a .xaml changes what the player sees.
That would need the same kind of one-file mod test the panel experiment used,
and this probe deliberately does not claim it.  What IS proven and relevant:
no amount of reversing makes the game run our code, because there is no code
loader in it -- which is the part of the player's question that has a hard
answer.
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
    bad = [c for c in CHECKS if not c[1]]
    if bad:
        print("UI LAYER: %d OF %d CHECKS FAILED -- %s"
              % (len(bad), len(CHECKS), ", ".join(c[0] for c in bad)))
        return 1
    print("UI LAYER: %d CHECKS PASSED -- native renderer, mod-visible root, "
          "markup on disk, closed class set" % len(CHECKS))
    print("NOT PROVEN HERE: that replacing a .xaml changes what the player sees.")
    print("  B proves the precondition (a root a loose file can land in + markup")
    print("  read from disk + lookup by path).  The in-game override is a separate")
    print("  experiment, of the same shape as the build-panel one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
