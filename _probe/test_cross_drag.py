# -*- coding: utf-8 -*-
"""Nail: a selection dragged into ANOTHER workshop window really lands there.

WHAT IS BEING PINNED, and how each part could be false:

1. THE BYTES TRAVEL.  The receiving window is a different process with a
   different session buffer, so the only thing that can cross is the record's
   own bytes.  `plan_add_units(images=...)` is that door; a copy that silently
   fell back to a donor id would clone something else in the TARGET file and
   look fine in every count.
2. THE NAMES DO NOT.  A record's name is a string id into the shared language
   file.  Copying it wholesale would be a lie -- the toast says so -- but the
   copy must still keep the donor's name field, because that is what the player
   recognises.  Both halves are asserted.
3. THE GESTURE HAS A SERVER.  The page cannot POST across ports (two origins,
   no CORS header, no OPTIONS answer, HTTP/1.0), so `/api/drop` forwards from
   server to server.  Pinned against a capture socket: the body it sends is what
   the target needs, and the target's answer comes back to the page.
4. THE REFUSALS ARE SENTENCES.  Dragging onto your own window, onto a port that
   is not listening, with nothing selected -- each is a real mistake with a
   different fix, so each gets its own words rather than a traceback.
5. THE SCREEN KNOWS WHEN SOMEBODY ELSE WROTE.  `/api/live` reports a counter
   with no author, so a page that redrew on every bump would rebuild its list
   after its own writes.  `LIVE_SELF` is the discriminator; the pinned part is
   that it is recorded from the answer of every write and compared before a
   foreign bump rebuilds the list.
"""
import base64
import io
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
SRV = os.path.join(ROOT, "aoe2mod", "ui", "server.py")
INS = os.path.join(ROOT, "aoe2mod", "ui", "instances.py")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))
    print(("  ok   " if ok else "  FAIL ") + name + (("  " + str(detail)) if detail else ""))


class _Capture(BaseHTTPRequestHandler):
    """A stand-in for the target window: remembers the POST, answers like one."""

    seen = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        _Capture.seen.append((self.path, json.loads(raw.decode("utf-8"))))
        body = json.dumps({"ok": True, "kind": "unit",
                           "info": {"ids": [30000, 30001], "count": 2}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    page = io.open(PAGE, encoding="utf-8").read()
    srv = io.open(SRV, encoding="utf-8").read()
    ins = io.open(INS, encoding="utf-8").read()

    # ---- 1. the page has a gesture, not a tooltip ------------------------
    check("a picked row is grabbable", "#editor .edrow.picked { cursor: grab" in page)
    check("the row builder arms the gesture", "edDragRow(row, r);" in page)
    check("the bar names the gesture the player asked for",
          "拖到另一个窗口复制" in page)
    check("the drag decides what to carry from the selection, not from one row",
          "if (edPicked(r) && EDPICK.length > 1) return EDPICK.map(p => p.id);" in page)
    check("the drop lands OUTSIDE the document, so the server is asked",
          "/api/drop-at?x=" in page)
    check("a foreign write rebuilds the list; this page's own does not",
          "st.v !== LIVE_SELF" in page and "if (typeof j.v === \"number\") LIVE_SELF = j.v;" in page)
    check("and the rebuild keeps how many rows were on screen",
          "const want = EDROWS.length;" in page and "await loadEditor(true, true);" in page)

    # ---- 2. the server has the forwarding door ---------------------------
    check("/api/drop is a POST route", 'path == "/api/drop"' in srv)
    check("/api/instances lists the other windows", 'path == "/api/instances"' in srv)
    check("/api/drop-at answers with the window under the cursor",
          'path == "/api/drop-at"' in srv)
    check("the window announces itself once the port is real",
          "INS.announce(" in srv and "_real_port," in srv)
    check("and withdraws on exit", "atexit.register(INS.withdraw" in srv)
    check("instances knows where the cursor is, in one coordinate system",
          "def cursor()" in ins and "GetCursorPos" in ins)

    from aoe2mod.dat import records as REC
    from aoe2mod.dat import newunit as NU
    from aoe2mod.ui import server as S

    app = S.App()
    tk = app.tk
    buf = app.session_raw()
    gv = tk._parsed[3]
    civs_start = tk._parsed[2]
    tail = tk._parsed[4]

    # Two records that are definitely not each other.
    rows = tk.browse(kind="unit", limit=400).get("rows") or []
    ids = [r["id"] for r in rows if r.get("name")][:2]
    check("the file has records to drag", len(ids) == 2, ids)
    civ_index = 1 if len(tk._civs) > 1 else 0
    spans = NU.unit_spans(buf, gv, civs_start, civ_index)
    ids = [i for i in ids if i in spans][:2]
    check("both are in the civ the editor defaults to", len(ids) == 2, ids)

    shots = [bytes(buf[spans[i][0]:spans[i][1]]) for i in ids]
    check("the two record images differ (a copy of one is not the other)",
          shots[0] != shots[1], (len(shots[0]), len(shots[1])))

    # ---- 3. what `/api/drop` sends IS the record -------------------------
    httpd = HTTPServer(("127.0.0.1", 0), _Capture)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    port = httpd.server_address[1]
    try:
        got = app.record_drop(port, kind="unit", civ="", ids=list(ids))
    finally:
        httpd.shutdown()
        httpd.server_close()
    check("the drag reports success from the target", got.get("ok"), got.get("error"))
    check("the target heard a record-add, not a stat request",
          bool(_Capture.seen) and _Capture.seen[0][0] == "/api/record-add",
          _Capture.seen and _Capture.seen[0][0])
    body = _Capture.seen[0][1] if _Capture.seen else {}
    sent = [base64.b64decode(x) for x in (body.get("images") or [])]
    check("every selected record was sent, in order", sent == shots,
          [(len(a), len(b)) for a, b in zip(sent, shots)])
    check("the selection travels with the bytes, so the target can say which",
          body.get("picked") == list(ids), body.get("picked"))
    check("and the target's answer comes back to the page",
          got.get("port") == port and got.get("sent") == 2, (got.get("port"), got.get("sent")))

    # ---- 4. the refusals are sentences -----------------------------------
    # `App()` built by hand has no port; the refusal is about the window the
    # gesture started in, so the pin has to tell it which one that is.
    app.port = port
    same = app.record_drop(port, ids=list(ids))
    check("dragging onto your own window is refused in words",
          same.get("ok") is False and "本窗口" in (same.get("error") or ""),
          same.get("error"))
    # Not this window's port: "you dragged nothing" outranks "you dragged
    # onto yourself", and the self-check would answer first otherwise.
    empty = app.record_drop(port + 1, ids=[])
    check("dragging nothing is refused in words",
          empty.get("ok") is False and "没选中" in (empty.get("error") or ""),
          empty.get("error"))
    dead = app.record_drop(1, ids=list(ids), timeout=2.0)
    check("a port nobody is listening on is refused in words",
          dead.get("ok") is False and "失败" in (dead.get("error") or ""),
          dead.get("error"))

    # ---- 5. the RECEIVING side adds the bytes it was given ---------------
    # This is the half that runs in the other window.  `ids` are pre-reserved
    # there by `free_unit_ids`, so the drop lands on fresh numbers above every
    # record the file has -- the only placement a batch may take.
    # A COPY of the session buffer, not the buffer: adding a record moves every
    # offset after it, so writing into the live one would leave the parse model
    # pointing at bytes that are no longer there (this pin did exactly that on
    # its first run and the technology section then read a count of -1).
    keep = bytes(buf)
    work = bytearray(keep)
    want = REC.free_unit_ids(tk._stats, 2)
    steps, info = REC.plan_add_units(work, gv, civs_start, civ_index, None,
                                     ids=want, images=shots, stats=tk._stats)
    REC.apply_steps(work, steps, inplace=True)
    check("a dropped batch takes the numbers it was handed",
          info.get("ids") == want, info.get("ids"))
    check("and says it came from images, not from a donor",
          info.get("dropped") is True and info.get("donor") is None,
          (info.get("dropped"), info.get("donor")))
    after = NU.unit_spans(work, gv, civs_start, civ_index)
    check("both landed in the civ", all(i in after for i in want), want)
    body0 = bytes(work[after[want[0]][0]:after[want[0]][1]])
    body1 = bytes(work[after[want[1]][0]:after[want[1]][1]])
    check("the first copy is as long as the record it came from",
          len(body0) == len(shots[0]), (len(body0), len(shots[0])))
    check("the second copy is NOT a clone of the first (order was kept)",
          body0 != body1, (len(body0), len(body1)))
    # The only bytes allowed to differ are the id (+1) and the name string id
    # (+3).  Everything else -- hp, graphics, costs, buttons -- must be the
    # donor's, which is what 「数值、关联都完美复制过去」 asks for.
    diff = [k for k in range(min(len(body0), len(shots[0])))
            if body0[k] != shots[0][k]]
    check("only the id bytes changed; every number is the donor's",
          set(diff) <= {1, 2, 3, 4}, diff[:10])
    check("the copy carries the donor's NAME (the player has to recognise it)",
          body0[3:5] == shots[0][3:5], (body0[3:5], shots[0][3:5]))

    # ---- 6. a technology travels the same way, by position ---------------
    # ON ITS OWN COPY.  `tail` is the technology section's count offset, and an
    # inserted unit record moves everything after it -- so a tech add has to be
    # measured against a buffer no unit was added to, or the count is read from
    # the middle of a unit record (this pin did exactly that and got -1).
    clean = bytearray(keep)
    try:
        tids = [r["id"] for r in (tk.browse(kind="tech", limit=40).get("rows") or [])][:2]
        tshots = REC.tech_images(clean, gv, tail, tids)
        check("two technology records read back as bytes",
              len(tshots) == 2 and tshots[0] != tshots[1],
              [len(x) for x in tshots])
        steps, tinfo = REC.plan_add_tech(clean, gv, tail, None, images=tshots)
        REC.apply_steps(clean, steps, inplace=True)
        check("they are appended at the end, where new ids live",
              tinfo.get("ids") == list(range(tinfo["ids"][0], tinfo["ids"][0] + 2)),
              tinfo.get("ids"))
        back = REC.tech_images(clean, gv, tail, tinfo.get("ids"))
        check("and read back byte-identical", back == tshots,
              [(len(a), len(b)) for a, b in zip(back, tshots)])
    except Exception as exc:                       # no tech table in this .dat
        check("technology records travel by position", False, "%s: %s" % (type(exc).__name__, exc))
    del work, clean, keep

    # ---- 7. the registry is where both windows agree ---------------------
    import tempfile
    tmp = tempfile.mkdtemp(prefix="inst-")
    os.environ["AOE2MOD_STATE_DIR"] = tmp
    try:
        import importlib
        from aoe2mod.ui import instances as I2
        importlib.reload(I2)
        I2.announce(7811, pid=1, parent=2, game_root="X")
        I2.announce(7812, pid=3, parent=4, game_root="X")
        rows2 = I2.live()
        check("both windows are listed", [r["port"] for r in rows2] == [7811, 7812],
              [r["port"] for r in rows2])
        I2.withdraw(7811)
        check("a closed window leaves the list",
              [r["port"] for r in I2.live()] == [7812],
              [r["port"] for r in I2.live()])
        check("the registry never publishes its own bookkeeping fields",
              not any(k.startswith("_") for k in rows2[0]), sorted(rows2[0]))
    finally:
        os.environ.pop("AOE2MOD_STATE_DIR", None)

    bad = [c for c in CHECKS if not c[1]]
    print("")
    if bad:
        print("CROSS DRAG: %d CHECK(S) FAILED -> %s" % (len(bad), [c[0] for c in bad]))
        return 1
    print("CROSS DRAG: A SELECTION LEAVES THIS WINDOW AS ITS OWN BYTES AND LANDS "
          "IN THE OTHER ONE -- EVERY NUMBER IS THE DONOR'S, THE ID IS NEW, AND A "
          "GESTURE THAT CANNOT WORK SAYS WHY")
    return 0


if __name__ == "__main__":
    sys.exit(main())