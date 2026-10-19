# -*- coding: utf-8 -*-
"""The local UI server: plain HTTP + JSON over the Toolkit, one screen.

Why not Electron / Tauri
------------------------
The project's constraint is a single entry point, plugins as folders, and no
requirement to squeeze everything into one .exe.  An HTTP server over the
existing `Toolkit` keeps the product's only state (the .dat, the mod folder, the
profile) exactly where it already lives, and the screen is a static folder --
replaceable, themeable, and inspectable without a build step.

What this server is NOT
-----------------------
It is not a general-purpose API.  It binds 127.0.0.1, it has no auth, and it
exposes five calls.  Anything that needs a decision (which of three archers, is
this edit safe) is answered by the CLIENT asking the user, not by the server
guessing -- the refusals carry reasons precisely so the screen can show them.

Design notes that are load-bearing
----------------------------------
* The Toolkit is expensive to build (parses 93 MB of .dat) and cheap to reuse,
  so it is built once, lazily, behind a lock.  Two concurrent first requests must
  not both parse.
* `plan()` is the preview.  The server never writes on a GET-like call, and
  `build()`/`install()` are separate, explicit POSTs -- a screen that previews
  on every keystroke cannot be allowed to emit mods.
* Errors are returned as `{"error": "..."} ` with HTTP 200 so the static client
  can render the message without special-casing fetch failures; a 500 would look
  like a network problem, which is exactly what it is not.
"""
import json
import os
import threading
import traceback

from aoe2mod import api as A
from aoe2mod.game import civnames as CN
from aoe2mod.ui import nl

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class App(object):
    """Everything the routes touch, with the Toolkit built once."""

    def __init__(self, game_root=None):
        self.game_root = game_root
        self._tk = None
        self._vocab = None
        self._lock = threading.Lock()

    @property
    def tk(self):
        if self._tk is None:
            with self._lock:
                if self._tk is None:
                    self._tk = A.open_toolkit(game_root=self.game_root)
        return self._tk

    def vocab(self):
        if self._vocab is None:
            ix = self.tk  # building the toolkit also builds the index
            from aoe2mod.semantic import index as SI
            idx = SI.index()
            self._vocab = nl.Vocabulary(idx.units, idx.techs)
        return self._vocab

    # ---- routes ---------------------------------------------------------
    def home(self):
        return self.meta()

    def meta(self):
        """Cheap facts a screen needs once: civs, intents, mods, versions."""
        tk = self.tk
        intents, _bindings = _load_schema()
        return {
            "ok": True,
            "version": tk.version,
            "civs": tk.civ_names,
            "intents": [{"id": k,
                         "title": v.get("title") or v.get("title_en") or k,
                         "fields": list((v.get("fields") or {})),
                         "strategy": (v.get("compile") or {}).get("strategy")}
                        for k, v in intents["intents"].items()],
            "mods": _mods_brief(tk),
        }

    def search(self, q, kind="unit", limit=25):
        return {"ok": True, "hits": self.tk.search(q, kind=kind, limit=limit)}

    def describe(self, kind, entity_id):
        return {"ok": True, "entity": self.tk.describe(int(entity_id), kind=kind)}

    def parse(self, text):
        """Sentence -> {intents, refusals}.  No bytes touched."""
        intents, clauses = nl.read(text, self.vocab(),
                                   civ_names=self.tk.civ_names,
                                   civ_zh=nl.CIV_ZH)
        out = []
        for cl in clauses:
            row = {"text": cl.text, "kind": cl.kind,
                   "entity": (cl.entity.display if cl.entity is not None
                              and not isinstance(cl.entity, dict)
                              else (cl.entity.get("name") if isinstance(cl.entity, dict) else None)),
                   "why": cl.why, "notes": cl.notes,
                   "candidates": [{"id": c.id if not isinstance(c, dict) else c["id"],
                                   "name": c.display if not isinstance(c, dict) else c.get("name")}
                                  for c in (cl.candidates or [])],
                   "intent": cl.intent}
            if cl.intent is not None:
                row["preview"] = self._safe_plan(cl.intent)
            out.append(row)
        return {"ok": True, "clauses": out, "intents": intents}

    def plan(self, intent):
        return {"ok": True, "plan": self._decorate(self.tk.plan(intent))}

    def build(self, intents, title=None, author="", description="", out_dir=None):
        """One mod from one or more intents.

        A bundle is the right shape for "these three related edits land together",
        not a convenience loop: two separate mods touching the same .dat is how
        the profile ends up with one silently overriding the other.
        """
        if not intents:
            return {"ok": False, "error": "没有可构建的改动"}
        out_dir = out_dir or os.path.join(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "_mods_out")
        if len(intents) == 1:
            r = self.tk.build(intents[0], out_dir, title=title, author=author,
                              description=description, overwrite=True)
        else:
            r = self.tk.build_bundle(intents, out_dir, title=title, author=author,
                                     description=description, overwrite=True)
        return {"ok": True, "manifest": r}

    def install(self, mod_dir, name=None, enabled=True, position=0,
                profile_root=None):
        """Copy a built mod into the profile.

        `profile_root` exists so the tests can point at a throwaway folder: the
        one thing a test must never do is edit the player's real mod list, which
        is the mistake that made `_probe/test_install.py` fail for reasons that
        had nothing to do with installing.
        """
        r = self.tk.install(mod_dir, name=name, title=name, enabled=enabled,
                            position=position, overwrite=True,
                            profile_root=profile_root)
        return {"ok": True, "installed": r}

    def mods(self):
        return {"ok": True, "mods": _mods_brief(self.tk)}

    def set_mod(self, name, enabled):
        return {"ok": True, "mods": self.tk.set_mod_enabled(name, enabled)}

    def uninstall(self, name):
        return {"ok": True, "mods": self.tk.uninstall(name)}

    # ---- helpers --------------------------------------------------------
    def _decorate(self, plan):
        """Turn the plan's civilization scope into names the screen can print.

        Two shapes arrive here, and that is a wart in the product rather than a
        choice made here: `unit.stat` reports `.dat` INDICES in `civs` while
        `unit.availability` reports NAMES.  The screen used to join whichever it
        got straight into "范围 ...", so a stat edit printed "范围 1、2、3".  Both
        shapes are accepted, the raw `civs` is left untouched for callers that
        want it, and a parallel `civ_labels` always carries printable Chinese.
        """
        if not isinstance(plan, dict):
            return plan
        scope = plan.get("civs")
        if not isinstance(scope, (list, tuple)) or not scope:
            return plan
        names = list(self.tk.civ_names or ())
        labels = []
        for item in scope:
            if isinstance(item, int):
                en = names[item] if 0 <= item < len(names) else str(item)
            else:
                en = item
            # `civnames.chinese` resolves all three spellings the game uses
            # (the .dat's `British`, the tree stem `BRITONS`, lower case) --
            # folding alone would leave `BRITONS` untranslated, which is what
            # the first version of this did.
            labels.append(CN.chinese(en))
        return dict(plan, civ_labels=labels)

    def _safe_plan(self, intent):
        """A preview that turns a refusal into data instead of a 500."""
        try:
            return {"ok": True, "plan": self._decorate(self.tk.plan(intent))}
        except Exception as exc:                       # noqa: BLE001
            return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}


def _load_schema():
    from aoe2mod.intent import compiler as C
    return C.load_schema()


def _mods_brief(tk):
    """Mods, with the fields a screen shows and nothing that leaks a path."""
    out = []
    for m in tk.mods():
        out.append({"name": m.get("name"), "title": m.get("title") or m.get("name"),
                    "enabled": bool(m.get("enabled")), "kind": m.get("kind"),
                    "priority": m.get("priority")})
    return out


# ---- HTTP wiring --------------------------------------------------------
def _json(handler, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _file(handler, path, ctype):
    with open(path, "rb") as fh:
        body = fh.read()
    handler.send_response(200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


_CTYPES = {".html": "text/html; charset=utf-8",
           ".css": "text/css; charset=utf-8",
           ".js": "application/javascript; charset=utf-8",
           ".svg": "image/svg+xml",
           ".png": "image/png",
           ".json": "application/json; charset=utf-8"}


def make_handler(app):
    """A `http.server.BaseHTTPRequestHandler` subclass bound to one App."""
    try:
        from http.server import BaseHTTPRequestHandler
    except ImportError:                                # pragma: no cover
        from BaseHTTPServer import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        server_version = "aoe2mod-ui"

        def log_message(self, fmt, *args):
            # The default writes every request to stderr; a screen that previews
            # on each keystroke would bury a real traceback in it.
            pass

        # ---- static ----
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return _file(self, os.path.join(STATIC_DIR, "index.html"),
                             _CTYPES[".html"])
            if path.startswith("/static/"):
                rel = path[len("/static/"):].replace("\\", "/")
                full = os.path.normpath(os.path.join(STATIC_DIR, rel))
                if not full.startswith(os.path.normpath(STATIC_DIR)):
                    return _json(self, {"ok": False, "error": "bad path"}, 400)
                if os.path.isfile(full):
                    ext = os.path.splitext(full)[1].lower()
                    return _file(self, full, _CTYPES.get(ext, "application/octet-stream"))
                return _json(self, {"ok": False, "error": "no such file"}, 404)
            if path == "/api/meta":
                return self._guard(lambda: app.meta())
            if path == "/api/mods":
                return self._guard(lambda: app.mods())
            if path == "/api/search":
                q = _query(self.path).get("q", [""])[0]
                kind = _query(self.path).get("kind", ["unit"])[0]
                return self._guard(lambda: app.search(q, kind=kind))
            if path == "/api/describe":
                q = _query(self.path)
                return self._guard(lambda: app.describe(
                    q.get("kind", ["unit"])[0], q.get("id", ["0"])[0]))
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        # ---- actions ----
        def do_POST(self):
            path = self.path.split("?", 1)[0]
            try:
                length = int(self.headers.get("Content-Length") or 0)
                payload = json.loads(self.rfile.read(length).decode("utf-8")
                                     if length else "{}")
            except ValueError as exc:
                return _json(self, {"ok": False, "error": "bad json: %s" % exc})
            if path == "/api/parse":
                return self._guard(lambda: app.parse(payload.get("text") or ""))
            if path == "/api/plan":
                return self._guard(lambda: app.plan(payload["intent"]))
            if path == "/api/build":
                return self._guard(lambda: app.build(
                    payload.get("intents") or [],
                    title=payload.get("title"),
                    author=payload.get("author") or "",
                    description=payload.get("description") or ""))
            if path == "/api/install":
                return self._guard(lambda: app.install(
                    payload["mod_dir"], name=payload.get("name"),
                    enabled=payload.get("enabled", True),
                    position=int(payload.get("position") or 0)))
            if path == "/api/mod":
                return self._guard(lambda: app.set_mod(
                    payload["name"], bool(payload.get("enabled"))))
            if path == "/api/uninstall":
                return self._guard(lambda: app.uninstall(payload["name"]))
            return _json(self, {"ok": False, "error": "no such route"}, 404)

        def _guard(self, fn):
            """One place where an exception becomes a readable sentence."""
            try:
                return _json(self, fn())
            except Exception as exc:                   # noqa: BLE001
                tb = traceback.format_exc(limit=4)
                return _json(self, {"ok": False,
                                    "error": "%s: %s" % (type(exc).__name__, exc),
                                    "where": tb})

    return Handler


def _query(path):
    try:
        from urllib.parse import parse_qs
    except ImportError:                                # pragma: no cover
        from urlparse import parse_qs
    return parse_qs(path.split("?", 1)[1] if "?" in path else "")


def serve(port=0, game_root=None, host="127.0.0.1"):
    """Start the server; returns (httpd, app, url).  Caller calls `serve_forever`."""
    try:
        from http.server import ThreadingHTTPServer
    except ImportError:                                # pragma: no cover
        from socketserver import ThreadingMixIn
        from http.server import HTTPServer

        class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True

    app = App(game_root=game_root)
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    url = "http://%s:%d" % (host, httpd.server_address[1])
    return httpd, app, url
