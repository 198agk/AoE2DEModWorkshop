# -*- coding: utf-8 -*-
"""Analyze AoE2DE .rms / .rms2 / .inc random map scripts."""
import os, re, json, collections, sys

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GX   = os.path.join(GAME, r"resources\_common\drs\gamedata_x2")
POMP = os.path.join(GAME, r"modes\Pompeii\resources\_common\drs\gamedata_x2")
OUT  = r"D:\Software\DeepSeek Harness\工作区2\_probe\survey_rms_ai"
os.makedirs(OUT, exist_ok=True)

TARGET_EXT = {".rms", ".rms2", ".inc"}

def find_all():
    files = []
    for root_dir in (GX, POMP):
        for dp, dn, fn in os.walk(root_dir):
            for f in fn:
                if os.path.splitext(f)[1].lower() in TARGET_EXT:
                    files.append(os.path.join(dp, f))
    return sorted(files)

def decode_info(path):
    raw = open(path, "rb").read()
    info = {
        "size": len(raw),
        "bom_utf8": raw.startswith(b"\xef\xbb\xbf"),
        "bom_utf16le": raw.startswith(b"\xff\xfe"),
        "bom_utf16be": raw.startswith(b"\xfe\xff"),
        "crlf": raw.count(b"\r\n"),
        "bare_lf": raw.count(b"\n") - raw.count(b"\r\n"),
        "bare_cr": raw.count(b"\r") - raw.count(b"\r\n"),
    }
    # strip BOM for text
    body = raw
    if info["bom_utf8"]:
        body = raw[3:]
    text = None
    enc_used = None
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = body.decode(enc)
            enc_used = enc
            break
        except UnicodeDecodeError as e:
            info.setdefault("decode_errors", []).append(f"{enc}: {e}")
    if text is None:
        text = body.decode("latin-1")
        enc_used = "latin-1 (fallback)"
    info["encoding"] = enc_used
    non_ascii = [(i, ch, ord(ch)) for i, ch in enumerate(text) if ord(ch) > 127]
    info["non_ascii_count"] = len(non_ascii)
    info["non_ascii_sample"] = non_ascii[:15]
    return raw, text, info

# Section headers look like <PLAYER_SETUP>
SEC_RE = re.compile(r"^\s*<([A-Za-z_][A-Za-z0-9_]*)>")
# A command line: first token
CMD_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\b")

def strip_comments(line):
    # RMS comments are // and /* */
    i = line.find("//")
    if i >= 0:
        line = line[:i]
    return line

def strip_block_comments(text):
    """Remove /* ... */ spans, preserving line count."""
    out = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        if depth == 0 and text.startswith("/*", i):
            depth = 1; i += 2; out.append("  "); continue
        if depth > 0 and text.startswith("*/", i):
            depth = 0; i += 2; out.append("  "); continue
        ch = text[i]
        if depth > 0:
            out.append("\n" if ch == "\n" else " ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)

def main():
    files = find_all()
    sections = collections.Counter()
    commands = collections.Counter()
    cmd_files = collections.defaultdict(set)
    sec_files = collections.defaultdict(set)
    sec_cmds = collections.defaultdict(collections.Counter)
    directives = collections.Counter()
    dir_files = collections.defaultdict(set)
    encodings = collections.Counter()
    per_file = []
    anomalies = []
    string_literals = collections.Counter()

    for path in files:
        raw, text, info = decode_info(path)
        # correct the encoding label: utf-8-sig decodes plain utf-8 too
        if info["bom_utf8"]:
            info["encoding"] = "utf-8 (BOM)"
        elif info["encoding"] == "utf-8-sig":
            info["encoding"] = "utf-8 (no BOM)"
        rel = os.path.relpath(path, GAME)
        encodings[info["encoding"]] += 1
        fsecs, fcmds = set(), set()
        n_sections = n_commands = 0
        cur = "«top-level»"
        text = strip_block_comments(text)
        for ln, rawline in enumerate(text.splitlines(), 1):
            line = strip_comments(rawline)
            if not line.strip():
                continue
            s = line.strip()
            if s.startswith("#"):
                d = s.split()[0]
                directives[d] += 1
                dir_files[d].add(rel)
                continue
            m = SEC_RE.match(line)
            if m:
                sections[m.group(1)] += 1
                fsecs.add(m.group(1)); n_sections += 1
                cur = m.group(1)
                continue
            m = CMD_RE.match(line)
            if m:
                tok = m.group(1).lower()
                commands[tok] += 1
                sec_cmds[cur][tok] += 1
                cmd_files[tok].add(rel); fcmds.add(tok); n_commands += 1
            # string literals (map names, unit names)
            for s2 in re.findall(r'"([^"]{1,60})"', line):
                string_literals[s2] += 1
        for s in fsecs: sec_files[s].add(rel)
        fi = {"rel": rel, "size": info["size"], "encoding": info["encoding"],
              "crlf": info["crlf"], "bare_lf": info["bare_lf"], "bare_cr": info["bare_cr"],
              "sections": sorted(fsecs), "n_sections": n_sections,
              "n_commands": n_commands, "n_cmds_distinct": len(fcmds),
              "lines": text.count("\n") + 1,
              "non_ascii": info["non_ascii_count"]}
        per_file.append(fi)
        if info["bare_cr"] or info["non_ascii_count"] or info.get("bom_utf8"):
            anomalies.append({"rel": rel, "bom_utf8": info["bom_utf8"],
                              "bare_cr": info["bare_cr"], "non_ascii": info["non_ascii_count"],
                              "sample": info["non_ascii_sample"][:6]})
        if info["size"] < 200:
            anomalies.append({"rel": rel, "tiny": info["size"]})

    result = {
        "files_total": len(files),
        "sections": sections.most_common(),
        "section_spread": {k: len(v) for k, v in sorted(sec_files.items(), key=lambda x: -len(x[1]))},
        "commands": commands.most_common(),
        "command_spread": {k: len(v) for k, v in sorted(cmd_files.items(), key=lambda x: -len(x[1]))},
        "encodings": encodings.most_common(),
        "anomalies": anomalies,
        "per_file": per_file,
        "top_strings": string_literals.most_common(80),
        "directives": directives.most_common(),
        "directive_spread": {k: len(v) for k, v in sorted(dir_files.items(), key=lambda x: -len(x[1]))},
        "section_commands": {s: sec_cmds[s].most_common(30) for s in sec_cmds},
    }
    with open(os.path.join(OUT, "rms_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"files scanned: {len(files)}")
    print("\n--- ENCODINGS ---")
    for e, c in encodings.most_common(): print(f"  {c:5d}  {e}")
    print("\n--- SECTIONS (%d distinct) ---" % len(sections))
    for s, c in sections.most_common(): print(f"  {c:6d}  <{s}>   in {len(sec_files[s])} files")
    print("\n--- TOP 70 COMMANDS (%d distinct) ---" % len(commands))
    for k, c in commands.most_common(70): print(f"  {c:6d}  {k:34s} files={len(cmd_files[k])}")
    print("\n--- DIRECTIVES (# ...) ---")
    for k, c in directives.most_common(40): print(f"  {c:6d}  {k:30s} files={len(dir_files[k])}")
    print("\n--- ANOMALIES ---")
    for a in anomalies[:40]: print("  ", a)

if __name__ == "__main__":
    main()
