"""Survey all scenario/campaign files: version strings, header sizes, streams.

Outputs CSV-ish lines plus campaign embedded-scenario discovery.
"""
import os
import re
import sys
import zlib
import glob

VER_RE = re.compile(rb"1\.\d\d\x00")


def find_exact_stream(data, limit=8192):
    hits = []
    for off in range(0, min(limit, len(data) - 2)):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(data[off:])
            out += d.flush()
            if d.eof and len(d.unused_data) == 0 and len(out) > 500:
                hits.append((off, len(out)))
        except Exception:
            pass
    return hits


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith((".aoe2scenario", ".aoe2campaign", ".scx", ".scn")):
                yield os.path.join(dirpath, fn)


def main():
    roots = sys.argv[1:]
    rows = []
    for root in roots:
        for path in sorted(walk(root)):
            size = os.path.getsize(path)
            with open(path, "rb") as f:
                data = f.read()
            head4 = data[:4]
            ver_str = head4.decode("ascii", "replace")
            hits = find_exact_stream(data)
            rows.append((path, size, ver_str, hits))
            hs = ",".join(f"{o}({l})" for o, l in hits) or "NONE"
            print(f"{ver_str!r:8s} size={size:<9d} stream={hs:<28s} {path}")

    print("\n\n=== SUMMARY: version string -> count ===")
    from collections import Counter
    c = Counter(r[2] for r in rows)
    for k, v in sorted(c.items()):
        print(f"  {k!r}: {v}")

    print("\n=== SUMMARY: extension -> count ===")
    c2 = Counter(os.path.splitext(r[0])[1].lower() for r in rows)
    for k, v in sorted(c2.items()):
        print(f"  {k}: {v}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_survey.tsv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("path\tsize\tversion\tstream_offsets\tstream_outlens\n")
        for path, size, ver, hits in rows:
            f.write(f"{path}\t{size}\t{ver}\t"
                    f"{','.join(str(o) for o, _ in hits)}\t"
                    f"{','.join(str(l) for _, l in hits)}\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
