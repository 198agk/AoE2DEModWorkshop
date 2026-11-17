"""The workshop's tag words read in Chinese, switch or no switch.

What this proves: the filter chips above the grid and the pills under a mod's
name are the app's own vocabulary -- seventeen names from /Tags plus the couple
a listing adds ("Official", "Scenario").  They are labels, not authors' prose,
so they must not wait for 译成中文; that switch is about the names and
descriptions people wrote, and it stays opt-in.

Read 2026-11-16: the page showed "Artificial Intelligence / Campaign / Data Mod
..." until the switch was pressed, then English again for "Official", because
the table only held what /Tags returns.  Both are fixed here.
"""
import io
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aoe2mod.ui import online as OL          # noqa: E402
from aoe2mod.ui import translate as TR       # noqa: E402

failures = []


def check(what, got, want):
    if got != want:
        failures.append("%s: got %r want %r" % (what, got, want))
        print("  FAIL %-52s got %r want %r" % (what, got, want))
    else:
        print("  ok   %-52s %r" % (what, got))


STATE = tempfile.mkdtemp(prefix="aoe2-tagzh-")
os.environ["AOE2MOD_STATE_DIR"] = STATE

print("[the seventeen]")
EXPECT = {
    "Artificial Intelligence": "人工智能",
    "Campaign": "战役",
    "Data Mod": "数据模组",
    "Graphics": "图像",
    "Movie": "影片",
    "Music": "音乐",
    "Random Maps": "随机地图",
    "Scenarios": "场景",
    "Sounds": "音效",
    "Speech": "语音",
    "Taunt": "嘲讽语音",
    "Terrain": "地形",
    "Menu Background": "菜单背景",
    "User Interface": "用户界面",
    "Text": "文本",
    "Other": "其他",
    "Return of Rome": "罗马复兴",
}
for name, zh in EXPECT.items():
    check("tag_zh(%s)" % name, TR.tag_zh(name), zh)

print("[names a listing carries that /Tags does not]")
check("tag_zh(Official)", TR.tag_zh("Official"), "官方")
check("tag_zh(Scenario)", TR.tag_zh("Scenario"), "场景")
check("case does not matter", TR.tag_zh("official"), "官方")
check("a blank name is not a tag", TR.tag_zh(""), "")
check("an unknown word has no Chinese", TR.tag_zh("Bogus"), "")

print("[peek ships the table]")
_TAGS = [
    {"modTypeId": 12, "modTypeName": "Graphics", "gameTitleId": 2},
    {"modTypeId": 15, "modTypeName": "Random Maps", "gameTitleId": 2},
]


class FakeResp(object):
    def __init__(self, body):
        self._body = body.encode("utf-8")
        self.status = 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


OL.urllib.request.urlopen = lambda req, timeout=0: FakeResp(json.dumps(_TAGS))
peek = OL.peek()
check("peek ok", peek["ok"], True)
check("peek still lists the tags", len(peek["tags"]), 2)
check("a tag carries its own Chinese", peek["tags"][0]["zh"], "图像")
check("peek ships the whole table", peek["tagZh"].get("graphics"), "图像")
check("the table covers Official", peek["tagZh"].get("official"), "官方")
check("the table is keyed lowercase",
      all(k == k.lower() for k in peek["tagZh"]), True)

print("[the page draws them without waiting for the switch]")
PAGE = io.open(os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html"),
               encoding="utf-8").read()


def digest(pattern, what):
    """The matched text, whitespace flattened so a re-wrap cannot hide a change."""
    hit = re.search(pattern, PAGE, re.S)
    if not hit:
        failures.append("%s: not found in index.html" % (what,))
        print("  FAIL %-52s not found" % (what,))
        return ""
    return re.sub(r"\s+", " ", hit.group(0))


chips = digest(r"function ogRenderTags\(\) \{.*?\n\}", "ogRenderTags")
check("chips build their label from the table", "t.zh || ogTagZh(t.name)" in chips, True)
check("chips do not gate on OG.zh", "OG.zh" in chips, False)
check("chips keep the English in a title", "b.title = t.name" in chips, True)

card = digest(r"for \(const t of m\.tags\.slice\(0, 3\)\) \{.*?\n    \}", "card pills")
check("card pills ask for Chinese first", "ogTagZh(t) || t" in card, True)
check("card pills do not gate on OG.zh", "OG.zh" in card, False)
check("card pills keep the English in a title", "pill.title = en" in card, True)

detail = digest(r"for \(const t of m\.tags\) \{.*?row\.appendChild\(pill\);.*?\n    \}", "detail pills")
check("detail pills read the same way", 'el("span", "ogpill", ogTagZh(t) || t)' in detail, True)
check("detail pills do not gate on OG.zh", "OG.zh" in detail, False)
check("detail pills keep the English in a title", "pill.title = t" in detail, True)

table = digest(r"function ogTagZh\(name\) \{.*?\n\}", "ogTagZh")
check("the page reads the shipped table", "OG.tagZh" in table, True)
check("and falls back to the per-tag field", "for (const t of OG.tags)" in table, True)
check("state has the table", re.search(r"tagZh: \{\}", PAGE) is not None, True)
check("peek fills it", "OG.tagZh = j.tagZh || {}" in PAGE, True)

print()
if failures:
    print("TAG ZH: %d FAILURE(S)" % len(failures))
    raise SystemExit(1)
print("TAG ZH: THE WORKSHOP'S TAG WORDS READ IN CHINESE -- THE FILTER CHIPS AND "
      "THE PILLS ON EVERY CARD, WITHOUT WAITING FOR THE 译成中文 SWITCH, WHICH "
      "KEEPS ITS JOB OF TRANSLATING THE AUTHORS' OWN WORDS.")
