"""The handoff page's info table, checked by structure rather than by eye.

Why this exists: twice in three days this table broke and only a human noticed.
On 2026-10-25 the `| git |` row was split across two physical lines -- GFM ends a
table at the first non-row line, so the five rows after it stopped being a table
and became a paragraph.  On 2026-10-26 an edit prepended a section to that row and
kept the old one, so the same history read twice inside one cell.  Neither
failure was caught by any suite, because no suite reads this file's structure.

The four things that go wrong, and how each is caught here:

  A  the table is interrupted  -- a blank or prose line between the header and the
     last row.  Found by walking from the header and requiring contiguity, NOT by
     hardcoding line numbers: the numbers move whenever a section is added above,
     and a gate that demands the wrong range reports a healthy file as broken.
  B  the history row is not one line -- it becomes two, and only the first is a
     row, so all history below it silently leaves the table.
  C  the same story twice -- a stamp appearing twice in the cell (the shape a
     "prepend and keep the old" edit produces), or any 60-character window of the
     row appearing twice.
  D  the row lost what it is for -- no sha, no demoted older commit, no date.

Cheap on purpose: reads bytes and regexes, imports nothing from the product.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, "_交接说明.md")

STAMP = re.compile(r"（20\d\d-\d\d-\d\d [0-9]{1,2}:[0-9]{1,2}x：")
SHA = re.compile(r"\*\*`([0-9a-f]{7,40})`\*\*")

FAILED = []
OK = [0]


def check(name, cond, detail=""):
    if cond:
        OK[0] += 1
        print("  ok   %s" % name)
    else:
        FAILED.append(name)
        print("  FAIL %s%s" % (name, (" :: " + str(detail)) if detail else ""))


def windows(text, n=60):
    return [text[i:i + n] for i in range(0, max(0, len(text) - n + 1))]


def main():
    raw = io.open(PAGE, "rb").read()
    text = raw.decode("utf-8")
    lines = text.split("\n")

    check("the page is LF and has no BOM",
          raw.count(b"\r\n") == 0 and not raw.startswith(b"\xef\xbb\xbf"),
          "crlf=%d bom=%s" % (raw.count(b"\r\n"), raw.startswith(b"\xef\xbb\xbf")))

    # ---- A. find the table by its header, then require contiguity
    header = next((i for i, ln in enumerate(lines)
                   if ln.startswith("| 项 |") or ln.startswith("| 项 | 值 |")), None)
    check("the info table has a header row", header is not None,
          "no line starts with `| 项 |`")
    if header is None:
        return _report()

    end = header
    while end + 1 < len(lines) and lines[end + 1].startswith("|"):
        end += 1
    body = lines[header:end + 1]
    check("the table has a header, a separator and some rows",
          len(body) >= 4 and body[1].startswith("|---"), len(body))
    check("no blank or prose line inside the table",
          all(ln.startswith("|") for ln in body),
          [ln[:30] for ln in body if not ln.startswith("|")][:3])
    check("the line after the table is not a row",
          end + 1 >= len(lines) or not lines[end + 1].startswith("|"),
          lines[end + 1][:40] if end + 1 < len(lines) else "(end of file)")
    print("       table spans lines %d..%d (1-based %d..%d), %d rows"
          % (header + 1, end + 1, header + 1, end + 1, len(body)))

    # ---- B. the history row is exactly one row
    git_rows = [i for i, ln in enumerate(lines) if ln.startswith("| git | ")]
    check("exactly one `| git |` row", len(git_rows) == 1, len(git_rows))
    if len(git_rows) != 1:
        return _report()
    g = git_rows[0]
    row = lines[g]
    check("the history row sits inside the table",
          header <= g <= end, "row at line %d, table %d..%d" % (g + 1, header + 1, end + 1))
    nxt = lines[g + 1] if g + 1 < len(lines) else ""
    check("the line under it is another row, not history prose",
          nxt.startswith("|"), nxt[:60])
    check("the history row names a commit", bool(SHA.search(row)),
          SHA.search(row).group(1) if SHA.search(row) else "no `**`sha`**`")

    # ---- C. the same story must not appear twice inside the cell
    # A history row legitimately carries SEVERAL stamps -- one per demoted entry.
    # What must not happen is the newest one appearing twice, which is the shape a
    # "prepend and keep the old" edit produces.  Asserting "exactly one stamp"
    # (the first version of this check) called a correct row broken.
    stamps = STAMP.findall(row)
    check("the cell carries at least one timestamp", len(stamps) >= 1, stamps)
    if stamps:
        check("the newest timestamp appears exactly once",
              stamps.count(stamps[0]) == 1,
              "%s x%d" % (stamps[0], stamps.count(stamps[0])))
    doubled = re.search(r"（(20\d\d-\d\d-\d\d [0-9]{1,2}:[0-9]{1,2}x：)\1", row)
    check("and no timestamp is immediately repeated", doubled is None,
          doubled.group(0) if doubled else "")
    wins = windows(row)
    dupes = sorted(set(w for w in wins if wins.count(w) > 1))
    check("no 60-character window of the cell appears twice", not dupes,
          dupes[:2])

    # ---- D. the row still does its job
    shas = SHA.findall(row)
    check("it names the current commit and at least one older one",
          len(shas) >= 2, shas[:4])
    check("the older commit is marked as older rather than dropped",
          "更早的" in row, row.count("更早的"))
    check("it carries a date", bool(re.search(r"20\d\d-\d\d-\d\d", row)), "")

    return _report()


def _report():
    print()
    if FAILED:
        print("HANDOFF TABLE: %d CHECK(S) FAILED -> %s" % (len(FAILED), FAILED))
        return 1
    print("HANDOFF TABLE: %d CHECKS PASSED -- THE INFO TABLE IS UNBROKEN, THE "
          "HISTORY ROW IS ONE LINE, AND NO STORY IS TOLD TWICE" % OK[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
