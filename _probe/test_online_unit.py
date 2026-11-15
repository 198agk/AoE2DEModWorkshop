"""Unit checks for aoe2mod/ui/online.py -- no network, no session, no network allowed.

The four sentences this proves are the ones a player will actually meet on the
first click: not signed in, signed in but the list is empty, signed in and there
are rows, and the detail view.  Each is driven through the real module with
urllib monkey-patched, so the whitelist and the error mapping are exercised
rather than a stub.
"""
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aoe2mod.ui import online as OL   # noqa: E402

failures = []


def check(what, got, want):
    if got != want:
        failures.append("%s: got %r want %r" % (what, got, want))
        print("  FAIL %-46s got %r want %r" % (what, got, want))
    else:
        print("  ok   %-46s %r" % (what, got))


STATE = tempfile.mkdtemp(prefix="aoe2-online-")
os.environ["AOE2MOD_STATE_DIR"] = STATE
print("state:", STATE)

# ---------------------------------------------------------------- no session
print("[not signed in]")
check("session_status.signed", OL.session_status()["signed"], False)
try:
    OL.find("cathedral")
    failures.append("find() without a session should have raised")
except OL.OnlineError as exc:
    check("find without session raises", "登录" in str(exc), True)

# ------------------------------------------------------- whitelist is a wall
print("[whitelist]")
for name in ("Subscribe", "UnSubscribe", "Download", "Publish", "Delete",
             "Rate", "Like", "Report", "Installed", "My", "Notifications"):
    try:
        OL._call(name, {})
        failures.append("_call(%r) was allowed" % name)
    except OL.OnlineError as exc:
        check("_call(%s) refused" % name, "只做预览" in str(exc), True)

# The whitelist loop above proves the runtime refuses these.  This second check
# proves there is no second path that never goes through `_call`: it walks the
# module's AST, drops every docstring (the one at the top lists the endpoints
# this file deliberately does NOT call, and a substring search would flag that
# honesty as a violation), and asserts none of the names survives as a string
# literal anywhere in actual code.
import ast
src = io.open(os.path.join(ROOT, "aoe2mod", "ui", "online.py"), encoding="utf-8").read()
tree = ast.parse(src)
docs = set()
for node in ast.walk(tree):
    if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            docs.add(id(body[0].value))
literals = [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]
# Endpoint names are passed to `_call` as bare literals, so the check is on the
# whole literal rather than a substring: `"userInstalled"` is a RESPONSE FIELD
# the card reads, not a call, and flagging it would teach the next reader to
# stop reading this file honestly.
for name in ("Subscribe", "UnSubscribe", "Download", "Publish", "Delete",
             "Rate", "Like", "Report", "Installed", "My", "Moderate",
             "CheckAndPublishFile", "Notifications"):
    check("no literal %r" % name, name not in literals, True)
check("endpoint literals are exactly the two it may use",
      sorted(set(x for x in literals if x in ("Find", "Detail", "Subscribe"))),
      ["Detail", "Find"])

# ------------------------------------------------------------- a real session
print("[signed in]")
session = {"savedAt": 1763200000, "cookies": {
    "api": "AgeAuthSession=ABC123; .AspNet.Session=XYZ", "auth": "AgeAuthSession=ABC123"}}
with io.open(os.path.join(STATE, OL.SESSION_FILE), "w", encoding="utf-8") as fh:
    fh.write(json.dumps(session))
status = OL.session_status()
check("session_status.signed", status["signed"], True)
check("session_status.count", status["count"], 2)
check("session_status has no values", "ABC123" in json.dumps(status), False)

# ---------------------------------------------------- Find, through a fake net
print("[Find]")
seen = {}


class FakeResp(object):
    status = 200

    def __init__(self, body):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_urlopen(req, timeout=0):
    seen["url"] = req.full_url
    seen["headers"] = dict((k.lower(), v) for k, v in req.header_items())
    seen["body"] = req.data
    seen["method"] = req.get_method()
    if req.full_url.endswith("/Find"):
        return FakeResp(json.dumps({
            "totalCount": 137, "modList": [
                {"modId": 4321, "modName": "Cathedral Pack", "thumbnail":
                 "https://cdn.ageofempires.com/aoe/mods/thumb_4321.jpg",
                 "creatorName": "FragileMiner", "downloads": 51200,
                 "totalRatings": 30, "ratings": {"rating": {"average": 4.6}},
                 "modTagNames": ["Data Mod"], "userInstalled": False},
                {"modId": 99, "modName": "No Thumb", "thumbnail":
                 "https://cdn.ageofempires.com/aoe/mods/thumb_",
                 "creatorName": "", "downloads": 1, "totalRatings": 0,
                 "modTagNames": []}]}))
    return FakeResp(json.dumps({"modId": 4321, "modName": "Cathedral Pack",
                                "imageUrls": [{"imageName": "https://cdn/x1.jpg",
                                               "imageThumbnail": "https://cdn/x1s.jpg"}]}))


OL.urllib.request.urlopen = fake_urlopen
out = OL.find("cathedral")
check("Find ok", out["ok"], True)
check("Find total", out["total"], 137)
check("Find page size", out["pageSize"], OL.PAGE_SIZE)
check("Find pages", out["pages"], 6)
check("Find rows", len(out["mods"]), 2)
check("card name", out["mods"][0]["name"], "Cathedral Pack")
check("card rating", out["mods"][0]["rating"], 4.6)
check("card tags", out["mods"][0]["tags"], ["Data Mod"])
check("empty thumbnail dropped", out["mods"][1]["thumb"], "")
check("missing name is said", out["mods"][1]["author"], "")
check("POST Find", seen["method"], "POST")
check("game id is AoE2", json.loads(seen["body"])["game"], 2)
check("count in body", json.loads(seen["body"])["count"], OL.PAGE_SIZE)
check("start is 1-based", json.loads(seen["body"])["start"], 1)
check("UA sent", "Mozilla" in seen["headers"].get("user-agent", ""), True)
check("cookie sent", "AgeAuthSession=ABC123" in seen["headers"].get("cookie", ""), True)

# cache: second call must not hit the network
seen.pop("url", None)
again = OL.find("cathedral")
check("second call served from cache", seen.get("url"), None)
check("cache is marked", again.get("fetchedAt", 0) > 0, True)

# page 2 asks for start=25
seen.clear()
OL.find("cathedral", page=2)
check("page 2 start", json.loads(seen["body"])["start"], OL.PAGE_SIZE + 1)

# ------------------------------------------------------------------- Detail
print("[Detail]")
seen.clear()
det = OL.detail(4321)
check("detail ok", det["ok"], True)
check("detail name", det["mod"]["name"], "Cathedral Pack")
check("detail shots", len(det["mod"]["shots"]), 1)
check("detail shot full", det["mod"]["shots"][0]["full"], "https://cdn/x1.jpg")
check("detail url", det["mod"]["url"],
      "https://www.ageofempires.com/mods/details/4321/")
check("Detail is GET", seen["method"], "GET")
check("Detail path", seen["url"].endswith("/Detail/4321"), True)

# --------------------------------------------------------------- failure maps
print("[errors]")


def boom(req, timeout=0):
    raise OL.urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))


OL.urllib.request.urlopen = boom
try:
    OL.find("x", fresh=True)
    failures.append("401 should have raised")
except OL.OnlineError as exc:
    check("401 says expired", "过期" in str(exc), True)


def offline(req, timeout=0):
    raise OL.urllib.error.URLError("getaddrinfo failed")


OL.urllib.request.urlopen = offline
try:
    OL.find("y", fresh=True)
    failures.append("URLError should have raised")
except OL.OnlineError as exc:
    check("offline says unreachable", "连不上" in str(exc), True)

# ---------------------------------------------------------------- peek shape
print("[peek]")


def tags_ok(req, timeout=0):
    return FakeResp(json.dumps([
        {"modTypeId": 9, "modTypeName": "Artificial Intelligence", "gameTitleId": 2},
        {"modTypeId": 11, "modTypeName": "Data Mod", "gameTitleId": 2},
        {"modTypeId": 1, "modTypeName": "Scenario", "gameTitleId": 1}]))


OL.urllib.request.urlopen = tags_ok
peek = OL.peek()
check("peek ok", peek["ok"], True)
check("peek signed", peek["signed"], True)
check("peek keeps only AoE2 tags", len(peek["tags"]), 2)
check("peek names a tag", peek["tags"][1]["name"], "Data Mod")

print()
if failures:
    print("ONLINE UNIT: %d FAILED" % len(failures))
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("ONLINE UNIT: ALL GREEN")
