"""Brute-force ground-truth scan: find EVERY offset where a raw-deflate stream
starts, decodes, and reaches EOF. Used only to establish ground truth for
comparing against the structured algorithm (NOT as a proposed method)."""
import sys, zlib, os

def scan(path, min_out=200, max_off=None):
    b = open(path, 'rb').read()
    if max_off is None:
        max_off = len(b)
    hits = []
    for off in range(0, min(max_off, len(b))):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(b[off:], 1 << 22)
            if not d.eof:
                continue
            out += d.flush()
            if len(out) >= min_out:
                hits.append((off, len(out), len(b) - off))
        except Exception:
            continue
    return b, hits

if __name__ == "__main__":
    for path in sys.argv[1:]:
        max_off = int(os.environ.get("MAXOFF", "0")) or None
        b, hits = scan(path, max_off=max_off)
        print(f"### {os.path.basename(path)} size={len(b)}  valid-stream offsets={len(hits)}")
        for off, outlen, remaining in hits[:40]:
            print(f"    off={off:8d}  out={outlen:9d}  remaining={remaining}")
        if len(hits) > 40:
            print(f"    ... ({len(hits)-40} more)")
