// Runs the page's script against a stub DOM and prints what it rendered.
//
// Why this exists: index.html is never executed by any test.  Two defects got
// shipped through a green HTTP suite because of that --
//   * `renderClauses` counted `c.intent` as "can build" (a refusal still
//     offered the build button, and took the possible half down with it), and
//   * after the fix it referenced `can` OUTSIDE the loop that declared it, which
//     is a ReferenceError on every render -- the screen would go blank while
//     /api/* answered perfectly.
// Node has no DOM, so everything below is the smallest stand-in that lets the
// real script run unmodified: createElement/querySelector/appendChild/textContent.
"use strict";
const fs = require("fs");
const path = require("path");

const HERO = process.env.DSH_UI_PAGE || path.resolve(__dirname,
  "..", "aoe2mod", "ui", "static", "index.html");
const html = fs.readFileSync(HERO, "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.log("PAGE: no <script> block found"); process.exit(1); }
const src = m[1];

// ---- a DOM just big enough ------------------------------------------------
function node(tag) {
  const n = {
    tagName: (tag || "div").toUpperCase(),
    className: "", textContent: "", innerHTML: "", style: {},
    children: [], value: "", disabled: false, onclick: null, title: "",
    parentNode: null,
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    // The pick-a-picture grid inserts a placeholder at the FRONT of a cell when a
    // declared icon turns out to have no file, and moves focus into the textarea
    // after a pick.  Both are ordinary DOM calls the page really makes.
    insertBefore(c, ref) {
      c.parentNode = this;
      const at = ref ? this.children.indexOf(ref) : -1;
      if (at >= 0) this.children.splice(at, 0, c);
      else this.children.push(c);
      return c;
    },
    focus() { this.focused = true; },
    addEventListener() {},
    setAttribute(k, v) { this[k] = v; },
    // Enough of the real DOM for the page's own "replace, do not stack" logic:
    // find the first descendant with a class, and detach a child.
    querySelector(sel) {
      const want = String(sel).replace(/^\./, "");
      for (const c of this.children) {
        if ((c.className || "").split(/\s+/).indexOf(want) >= 0) return c;
        const deeper = c.querySelector ? c.querySelector(sel) : null;
        if (deeper) return deeper;
      }
      return null;
    },
    remove() {
      const p = this.parentNode;
      if (!p) return;
      const at = p.children.indexOf(this);
      if (at >= 0) p.children.splice(at, 1);
      this.parentNode = null;
    },
    get firstChild() { return this.children[0] || null; },
  };
  // `box.innerHTML = ""` is how the page starts every render.  In a real DOM
  // that detaches the old children; a stub that just stores the string keeps
  // them, so a later assertion sees the PREVIOUS payload's nodes and reports a
  // phantom defect (it said "3 pictures for a 2-clause payload").  Assigning
  // empty HTML must therefore clear the child list, as the browser does.
  let html = "";
  Object.defineProperty(n, "innerHTML", {
    get() { return html; },
    set(v) { html = String(v); if (html === "") n.children.length = 0; },
  });
  return n;
}
const ids = {};
const document = {
  createElement: node,
  querySelector(sel) {
    const key = sel.replace(/^#/, "");
    if (!ids[key]) ids[key] = node(sel);
    return ids[key];
  },
};
// The page's buildnote is a text blob, so its rendering is the string.
function text(n) {
  if (n == null) return "";
  if (typeof n === "string") return n;
  return (n.textContent || "") + n.children.map(text).join("");
}
function walk(n, out) {
  out.push(n);
  (n.children || []).forEach((c) => walk(c, out));
  return out;
}

// ---- the two payloads that matter ---------------------------------------
// Both are real /api/parse answers, captured from the live server.  The first
// is what `buildable` looks like when the plan accepted the edit; the second
// when it refused one that the sentence still understood.
const FIXTURES = {
  mixed: {
    ok: true,
    clauses: [
      { text: "村民血量改成1000", kind: "unit", entity: "村民", entity_id: 83,
        why: null,
        notes: [], candidates: [], intent: { intent: "unit.stat", unit: 83,
        stat: "hit_points", value: 1000 }, buildable: true,
        preview: { ok: true, plan: { description: "村民 生命值 =1000",
          kind: "unit", civ_count: 63, edit_count: 1701, changes_dat: true,
          civ_labels: ["不列颠"], editable: true } } },
      { text: "织布机研究时间加0", kind: "tech", entity: "织布机", entity_id: 22,
        why: null,
        notes: [], candidates: [], intent: { intent: "tech.research_time",
          tech: 22, delta: 0 }, buildable: false,
        preview: { ok: true, plan: {
          description: "织布机 的研究时间已经是这个值了，这样改不会有任何变化",
          kind: "tech", editable: false } } },
    ],
  },
  refusedOnly: {
    ok: true,
    clauses: [
      { text: "织布机研究时间加0", kind: "tech", entity: "织布机", entity_id: 22,
        why: null,
        notes: [], candidates: [], intent: { intent: "tech.research_time",
          tech: 22, delta: 0 }, buildable: false,
        preview: { ok: true, plan: {
          description: "织布机 的研究时间已经是这个值了，这样改不会有任何变化",
          kind: "tech", editable: false } } },
    ],
  },
  notUnderstood: {
    ok: true,
    clauses: [
      { text: "这是什么", kind: null, entity: null, why: "这是在提问，不是在修改",
        notes: [], candidates: [], intent: null, buildable: false },
    ],
  },
  // A real /api/parse answer for "骑兵的血量改成1000".  `class_word` is the word
  // the PLAYER typed; the candidates are members of that class, and none of them
  // is called 骑兵.  Without the exact word the page has to guess which substring
  // to replace, and the guess it used to make was "put the picked name where the
  // number was".
  classRefusal: {
    ok: true,
    clauses: [
      { text: "骑兵的血量改成1000", kind: "unit", entity: null, entity_id: null,
        class_word: "骑兵",
        why: "「骑兵」是一类单位，不是某一个（这一类里有 188 个单位）。说具体名字，或者从下面点一个",
        notes: [],
        candidates: [
          { id: 448, name: "草骑射手" }, { id: 546, name: "草原枪骑兵" },
          { id: 39, name: "骑射手" },
        ],
        // The real answer has NO intent: the gate fires before anything was
        // read as an edit, which is exactly why the page takes the refusal
        // branch rather than the "understood but cannot build" one.
        intent: null, buildable: false },
    ],
  },
};

// Two real /api/describe answers, captured from the live server: one unit (this
// build has no unit prose at all) and one technology (it does have a
// description).  The screen must print both -- a blank where a description goes
// reads as our bug, and printing nothing at all for a refusal loses the reason.
const DESCRIBE = {
  unit: {
    id: 83, kind: "unit", name: "村民 (男性)", en: "Villager (Male)", zh: "村民 (男性)",
    resolved: true, civ_variants: [],
    prose: { ok: false, fields: {}, missing: {}, why: "这个版本没有单位描述：游戏"
      + "的字符串表里没有单位帮助文本（英文和中文都是空的，不是缺翻译）" },
    icon: { ok: true, file: "textures/ingame/units/015_50730.dds" },
  },
  tech: {
    id: 22, kind: "tech", name: "织布机", en: "Loom", zh: "织布机",
    resolved: true, civ_variants: [],
    prose: { ok: true, missing: { help: "帮助文本：记录声明的 107022 在这份字符串表里没有内容" },
      fields: { description: { name_string_id: 7022,
        zh: "研究织布机 (村民的生命值 +15，近战护甲 +1/远程护甲 +2)",
        en: "Research Loom (Villagers +15 HP, +1 melee/+2 pierce armour)" } } },
    icon: { ok: true, file: "textures/ingame/tech/006_loom.dds" },
  },
};

// A real /api/browse answer, captured from the live server: a page of units
// where the third row has no picture at all.  Many of the game's units ship no
// icon, so "no picture" is the ordinary case, not an error -- the grid
// must still offer the cell, labelled, because the name is the only handle the
// player has on it.
const BROWSE = {
  unit: {
    ok: true,
    browse: { ok: true, kind: "unit", total: 1651, offset: 0, limit: 3, rows: [
      { id: 83, kind: "unit", name: "村民 (男性)", zh: "村民 (男性)",
        en: "Villager (Male)", has_icon: true, icon_id: 15 },
      { id: 4, kind: "unit", name: "步弓手", zh: "步弓手", en: "Archer",
        has_icon: true, icon_id: 17 },
      { id: 1258, kind: "unit", name: "攻城锤", zh: "攻城锤", en: "Battering Ram",
        has_icon: false, icon_id: -1 },
    ] },
  },
  tech: {
    ok: true,
    browse: { ok: true, kind: "tech", total: 536, offset: 0, limit: 1, rows: [
      { id: 22, kind: "tech", name: "织布机", zh: "织布机", en: "Loom",
        has_icon: true, icon_id: 6 },
    ] },
  },
};

// A real /api/update-check answer, captured from a live server with an installed
// mod whose build record says the game's .dat has changed since.  Unknown rows
// are in the same payload on purpose: the banner must count ONLY stale ones.
const UPDATE = {
  stale: {
    ok: true, state_dir: "C:\\Users\\x\\AppData\\Local\\aoe2de-mod-workshop",
    dat: { version: "VER 8.9" }, needs_attention: 1,
    banner: "游戏数据在你装这些模组之后更新过：村民血量测试。它们带着旧的一整份 .dat，会把更新盖掉；重建一次就好。",
    rows: [
      { name: "村民血量测试", title: "村民血量测试", kind: "local", enabled: true,
        status: "stale", detail: "游戏数据更新过（版本号还是 VER 8.9，但内容变了）",
        fixable: true, built_at: "2026-10-19T22:00:00", built_version: "VER 8.9" },
      { name: "别人做的模组", title: "别人做的模组", kind: "subscribed", enabled: true,
        status: "unknown", detail: "没有任何构建记录", fixable: false },
    ],
  },
  quiet: {
    ok: true, state_dir: "C:\\Users\\x\\AppData\\Local\\aoe2de-mod-workshop", dat: {},
    needs_attention: 0, banner: null,
    rows: [
      { name: "别人做的模组", title: "别人做的模组", kind: "subscribed", enabled: true,
        status: "unknown", detail: "没有任何构建记录", fixable: false },
    ],
  },
};
let UPDATE_ANSWER = UPDATE.stale;
const rebuilt = [];
// The game-running warning, as a switchable state: the same install route must
// say something when the game is open and NOTHING when it is closed (a warning
// shown always is a warning nobody reads).
let RUNNING = true;
const RUNNING_TEXT = "游戏正开着。它退出时会用自己记得的模组列表覆盖 mod-status.json，"
  + "所以这次写进去的改动可能被盖掉（文件还在，列表里没有）。装完回游戏里看一眼，"
  + "或者关掉游戏再写一次。";
// The build route's answer: {manifest} with a mod_dir, then the install POST.
const BUILD_ANSWER = { ok: true, manifest: { mod_dir: "/tmp/x",
  info: { Title: "x" } } };
// What the stub echoes back as the used Title, and a switch that makes it come
// back SHORTER than it went in -- which is what the engine's 100-byte cap does
// to an auto title made of Chinese sentences.
let BUILT_TITLE = "x";
let TRIM = false;
// Did the page mark the title it sent as one IT wrote (`title_auto`)?  Only such
// a title may be trimmed to the engine's 100-byte limit; one the player typed is
// refused with a sentence instead.
let AUTO_SENT = null;

// ---- run the real script -------------------------------------------------
const posted = [];
const sandbox = {
  document,
  fetch: async (url, opt) => {
    posted.push({ url, body: opt && opt.body ? JSON.parse(opt.body) : null });
    // /api/describe answers with one of the two captured entities.  The page's
    // "what does the game say" button must render BOTH the text and the
    // refusal, so the stub has to answer with the real shapes.
    if (url.indexOf("/api/describe") === 0) {
      const kind = (url.match(/kind=([a-z]+)/) || [])[1];
      return { json: async () => ({ ok: true, entity: DESCRIBE[kind] }) };
    }
    if (url.indexOf("/api/browse") === 0) {
      const kind = (url.match(/kind=([a-z]+)/) || [])[1];
      return { json: async () => BROWSE[kind] };
    }
    // A parse answer is also forwarded to renderClauses, so the stub has to
    // hand back a real one rather than the generic meta-shaped object.
    if (url.indexOf("/api/parse") === 0) {
      return { json: async () => FIXTURES.mixed };
    }
    if (url.indexOf("/api/build") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      AUTO_SENT = body.title_auto;
      // Echo the title back the way the server does.  `TRIM` makes the stub
      // return a SHORTER title than it was given, which is what the engine's
      // 100-byte cap does to an auto title built from Chinese sentences -- the
      // page has to notice and tell the player, not silently show a stale box.
      BUILT_TITLE = body.title || "dsh 未命名";
      if (TRIM) BUILT_TITLE = BUILT_TITLE.slice(0, 8);
      return { json: async () => ({ ok: true, manifest: { mod_dir: "/tmp/x",
        info: { Title: BUILT_TITLE } } }) };
    }
    if (url.indexOf("/api/update-check") === 0) {
      // The route wraps its answer the way the server does ({ok, update}); a stub
      // that returned the bare rows would let a page bug (reading the wrong
      // level) pass here and fail on screen.
      return { json: async () => ({ ok: true, update: UPDATE_ANSWER }) };
    }
    if (url.indexOf("/api/rebuild") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      rebuilt.push(body.title);
      // A rebuild reinstalls, so it carries the same game-running answer.  The
      // stub has to have it or "rebuild is the one button that looks safe"
      // would pass here and be wrong on screen.
      return { json: async () => ({ ok: true, manifest: {}, installed: {
        installed: true, game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null,
      } }) };
    }
    // The install route answers with the game-running answer inside
    // `installed`, because that is the shape `install_mod` returns.  A stub that
    // omitted it would make "the screen warns while the game is open" untestable
    // -- the page would silently read `undefined` and look fine.
    if (url.indexOf("/api/install") === 0) {
      return { json: async () => ({ ok: true, installed: {
        name: "x", title: "x", installed: true,
        game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null,
      } }) };
    }
    return { json: async () => ({ ok: true, version: 54, civs: new Array(63),
      intents: [], mods: [], manifest: { mod_dir: "/tmp/x", info: {} } }) };
  },
  setTimeout: () => 0, clearTimeout: () => {},
  console,
  JSON,
};
const fn = new Function(
  "document", "fetch", "setTimeout", "clearTimeout", "console", "JSON",
  src + "\n;return {renderClauses: renderClauses, buildable: buildable, " +
  "doBuild: doBuild, doParse: doParse, renderDetail: renderDetail, " +
  "loadPick: loadPick, pickCell: pickCell, pickName: pickName, " +
  "setPickKind: setPickKind, PICK: () => PICK, PINS: () => PINS, " +
  "dropOnSay: dropOnSay, DRAGGING: () => DRAGGING, " +
  "checkUpdates: checkUpdates, rebuildAll: rebuildAll, " +
  "setLast: (v) => { LAST = v; }};");
const page = fn(sandbox.document, sandbox.fetch, sandbox.setTimeout,
                sandbox.clearTimeout, sandbox.console, sandbox.JSON);

// ---- assertions ----------------------------------------------------------
const fails = [];
function check(name, ok, detail) {
  if (ok) { console.log("  ok " + name); }
  else { fails.push(name); console.log("FAIL " + name + " :: " + (detail || "")); }
}

try {
  page.renderClauses(FIXTURES.mixed.clauses);
  const note = text(ids.buildnote);
  check("a mixed payload renders instead of throwing (this is the `can` bug)",
        true);
  check("the commit box is shown when at least one clause is possible",
        ids.commit.style.display === "block", ids.commit.style.display);
  check("the note says the refused sentence will be skipped, not fail the build",
        note.indexOf("跳过") >= 0, note);
  check("the auto title names only the buildable sentence",
        ids.title.value.indexOf("织布机") < 0, ids.title.value);
  const all = walk(ids.preview, []);
  check("the possible clause is styled as ok",
        all.some((n) => n.className === "clause ok"));
  check("the refused clause is styled as refused",
        all.some((n) => n.className === "clause bad"));
  check("the refusal text reaches the screen",
        text(ids.preview).indexOf("已经是这个值了") >= 0, text(ids.preview));
  check("the refusal is not described as an unreadable sentence",
        text(ids.preview).indexOf("没读懂") < 0, text(ids.preview));

  page.renderClauses(FIXTURES.refusedOnly.clauses);
  check("nothing possible -> the commit box is hidden",
        ids.commit.style.display === "none", ids.commit.style.display);
  check("nothing possible -> the note says so in words",
        text(ids.buildnote).indexOf("改不了") >= 0, text(ids.buildnote));

  page.renderClauses(FIXTURES.notUnderstood.clauses);
  check("a sentence that was not understood keeps its own reason",
        text(ids.preview).indexOf("这是在提问") >= 0, text(ids.preview));

  // ---- a CLASS name: offer its members, and swap in the picked one --------
  // "骑兵" is a category, not a record.  The server refuses it WITH candidates,
  // and the page must (a) show them, (b) put the picked name where the player
  // wrote the category -- not where the number was, which is what the old
  // candidate renderer did -- and (c) remember the pick as a pin, because names
  // are not unique (城门 is 29 records).
  page.renderClauses(FIXTURES.classRefusal.clauses);
  const clsText = text(ids.preview);
  check("a class refusal reaches the screen with its count",
        clsText.indexOf("一类单位") >= 0 && clsText.indexOf("188") >= 0, clsText);
  const candButtons = walk(ids.preview, []).filter(
    (n) => n.tagName === "BUTTON" && n.className === "chip" &&
           (n.textContent || "").indexOf("(#") >= 0);
  check("the class members are offered as clickable choices",
        candButtons.length === 3, String(candButtons.length));
  if (candButtons.length) {
    ids.say.value = "骑兵的血量改成1000";
    candButtons[0].onclick();
    check("picking one rewrites the CATEGORY word, keeping the rest",
          ids.say.value === "草骑射手的血量改成1000", ids.say.value);
    const pins = page.PINS();
    check("the pick is remembered by id, not just by name",
          pins.length === 1 && pins[0].id === 448 && pins[0].kind === "unit",
          JSON.stringify(pins));
    // PINS is module state shared by every render, so a check below that expects
    // "one pin after one grid click" would see MINE.  Hand the list back empty.
    pins.length = 0;
  }
  page.setLast(FIXTURES.mixed);

  page.setLast(FIXTURES.mixed);
  // Render it again: the two checks above rendered the OTHER payloads, and the
  // preview box holds only the last one.  (Reading it without re-rendering found
  // 0 pictures -- a real answer to the wrong question, not a page defect.)
  page.renderClauses(FIXTURES.mixed.clauses);
  const boxes = walk(ids.preview, []);
  const icos = boxes.filter((n) => n.tagName === "IMG");
  check("each understood clause asks for its own picture",
        icos.length === 2, String(icos.length));
  check("the picture is requested from the real route with the entity id",
        icos.length > 0 && icos[0].src.indexOf("/api/icon?kind=unit&id=83") === 0,
        icos.length ? icos[0].src : "(none)");
  const dets = boxes.filter((n) => n.className === "detailrow");
  check("an understood clause offers the game's own words", dets.length === 2,
        String(dets.length));

  // ---- the detail panel, both shapes -----------------------------------
  // A unit: the product refuses, and the screen must print the REASON.  An empty
  // description area would look like a bug in this product instead of a fact
  // about the build.
  const unitDetail = text(page.renderDetail(DESCRIBE.unit));
  check("a unit with no prose still prints the reason",
        unitDetail.indexOf("没有单位描述") >= 0, unitDetail);
  check("...and the reason is not left as a blank box",
        unitDetail.trim().length > 10, unitDetail);
  // A technology: it has text, and the screen must show it plus the gap.
  const techDetail = text(page.renderDetail(DESCRIBE.tech));
  check("a technology's description reaches the screen",
        techDetail.indexOf("研究织布机") >= 0, techDetail);
  check("...and a field that could not be filled says so",
        techDetail.indexOf("107022") >= 0, techDetail);
  check("the entity's own name heads the panel",
        techDetail.indexOf("织布机") >= 0, techDetail);

  // ---- clicking it twice must replace, not stack ------------------------
  // The button had no memory of its previous answer, so two clicks printed the
  // same paragraph twice.  Exercised through the REAL click handler rather than
  // by calling the renderer, because the bug lived in the handler -- and the
  // handler is async, so counting synchronously after `onclick()` reads zero
  // panels and an assertion written that way would test nothing.
  const rows = boxes.filter((n) => n.className === "detailrow" &&
                                   n.children.some((c) => c.tagName === "BUTTON"));
  check("the detail link is a real button", rows.length === 2,
        boxes.map((n) => n.className).join("|"));
  if (!rows.length) { buildChecks(); return; }
  const row = rows[0];
  const button = row.children.filter((c) => c.tagName === "BUTTON")[0];
  const panels = () => row.children.filter(
    (c) => (c.className || "").split(/\s+/).indexOf("detail") >= 0).length;
  button.onclick().then(() => {
    check("a click puts one answer under the clause", panels() === 1,
          String(panels()));
    button.disabled = false;
    return button.onclick();
  }).then(() => {
    check("clicking again replaces the answer instead of stacking a second copy",
          panels() === 1, String(panels()));
    return buildChecks();
  }).catch((e) => {
    fails.push("the detail click threw: " + e.message);
    console.log("FAIL the detail click threw :: " + e.stack);
    finish();
  });
} catch (e) {
  fails.push("renderClauses threw: " + e.message);
  console.log("FAIL renderClauses threw :: " + e.stack);
  finish();
}

function buildChecks() {
  page.doBuild().then(() => {
    const call = posted.filter((p) => p.url === "/api/build")[0];
    check("build was called", !!call, JSON.stringify(posted.map((p) => p.url)));
    const sent = call ? call.body.intents : [];
    check("build is sent ONLY the buildable intents", sent.length === 1,
          JSON.stringify(sent));
    check("the refusal never reaches /api/build",
          !sent.some((i) => i.intent === "tech.research_time"),
          JSON.stringify(sent));
    // The game rewrites mod-status.json on exit, so an install while it runs can
    // be undone at exit.  The screen must SAY so -- and must say nothing when
    // the game is closed, or the line becomes furniture.
    check("installing while the game runs warns on screen",
          text(ids.buildnote).indexOf("游戏正开着") >= 0, text(ids.buildnote));
    check("the warning is not styled as an error",
          !walk(ids.buildnote, []).some((n) => n.className === "err"),
          JSON.stringify(walk(ids.buildnote, []).map((n) => n.className)));
    RUNNING = false;
    return page.doBuild();
  }).then(() => {
    check("no warning when the game is closed",
          text(ids.buildnote).indexOf("游戏正开着") < 0, text(ids.buildnote));
    // The page's own title is marked as such, so the server may trim it.  Three
    // Chinese characters cost nine bytes, so a few sentences pass the engine's
    // 100-byte cap with nobody typing a long title -- and the build used to fail
    // on a byte count the player never wrote.
    check("the page marks its own title so the server may trim it",
          AUTO_SENT === true, String(AUTO_SENT));
    // ...and a title the player typed is NOT marked, because shortening text
    // someone wrote by hand is a different act (they get a refusal instead).
    ids.title.value = "我自己起的名字";
    return page.doBuild();
  }).then(() => {
    check("a title the player typed is not marked for trimming",
          AUTO_SENT === false, String(AUTO_SENT));
    // A trimmed title must be visible on both surfaces: the box (or it looks
    // like the mod list disagrees) and a line of prose (or the player's name
    // silently changed).
    TRIM = true;
    ids.title.value = "";
    page.renderClauses(FIXTURES.mixed.clauses);   // refill with an AUTO title
    return page.doBuild();
  }).then(() => {
    check("a trimmed title is shown in the box, not the long one",
          ids.title.value === BUILT_TITLE, ids.title.value);
    check("and the screen says the title was shortened",
          text(ids.buildnote).indexOf("标题有点长") >= 0, text(ids.buildnote));
    check("being shortened is not reported as a failure",
          text(ids.buildnote).indexOf("没做成") < 0
          && !walk(ids.buildnote, []).some((n) => n.className === "err"),
          text(ids.buildnote));
    TRIM = false;
    return pickChecks();
  }).catch((e) => { fails.push("doBuild threw: " + e.message);
                    console.log("FAIL doBuild threw :: " + e.stack); finish(); });
}

// ---- pick a picture ------------------------------------------------------
// The grid is the only entry that does not require already knowing the name,
// so it has to survive the ordinary awkward cases: a row with no picture at
// all, and a name that the sentence parser would not have accepted on its own.
function pickChecks() {
  return page.loadPick(false).then(() => {
    const grid = ids.pickgrid;
    const cells = (grid.children || []).filter((n) => n.className
      && n.className.indexOf("cell") >= 0);
    check("the grid asks the browse route for a page of units",
          posted.some((p) => p.url.indexOf("/api/browse?kind=unit") === 0),
          JSON.stringify(posted.map((p) => p.url)));
    check("every row becomes a cell", cells.length === 3, String(cells.length));
    check("a row WITH a picture draws an <img> for that id",
          cells[0].children.some((c) => c.tagName === "IMG"
            && c.src.indexOf("/api/icon?kind=unit&id=83") === 0),
          JSON.stringify(cells[0].children.map((c) => c.tagName)));
    // Many units ship no icon; the cell must still exist and still be usable.
    const blank = cells.filter((c) => c.className.indexOf("noicon") >= 0);
    check("a row with NO picture is still a cell, drawn as a blank",
          blank.length === 1, String(blank.length));
    check("...and it carries no <img> that would render as a broken image",
          blank.length === 1 && !blank[0].children.some((c) => c.tagName === "IMG"),
          JSON.stringify(blank.length ? blank[0].children.map((c) => c.tagName) : []));
    check("...and the name is printed even without a picture",
          text(blank[0] || { textContent: "", children: [] }).indexOf("攻城锤") >= 0,
          text(blank[0] || { textContent: "", children: [] }));
    // Picking must append a usable name to the sentence box, not replace it.
    ids.say.value = "村民血量改成1000\n";
    cells[0].onclick();
    check("picking a cell appends its name to the sentence box",
          ids.say.value.indexOf("村民血量改成1000") === 0
          && ids.say.value.indexOf("村民 (男性)") > 0, ids.say.value);
    // ...and the text it appends has to be one the parser can find again.
    // (A name it cannot read would make the grid a dead end.)
    check("the appended name ends with a space so a number can follow",
          /\s$/.test(ids.say.value), JSON.stringify(ids.say.value));
    // A name is not a key: 靶场 is 10 records, 城门 is 29.  The click has to
    // remember WHICH one, or the sentence comes back pointing at a different
    // record and the player's edit lands on the wrong thing.
    const pins = page.PINS();
    check("picking a cell remembers the id it drew",
          pins.length === 1 && pins[0].id === 83 && pins[0].kind === "unit",
          JSON.stringify(pins));
    // ...and that memory must travel with the sentence.
    ids.say.value = "村民血量改成1000";
    return page.doParse();
  }).then(() => {
    const call = posted.filter((p) => p.url.indexOf("/api/parse") === 0).pop();
    check("the parse request carries the clicked ids",
          call && call.body && Array.isArray(call.body.pins)
          && call.body.pins.length === 1 && call.body.pins[0].id === 83,
          JSON.stringify(call && call.body));
    return Promise.resolve();
  }).then(() => {
    return dragChecks();
  }).then(() => {
    page.setPickKind("tech");
    return page.loadPick(false);
  }).then(() => {
    check("switching to technologies asks for technologies",
          posted.some((p) => p.url.indexOf("/api/browse?kind=tech") === 0),
          JSON.stringify(posted.map((p) => p.url)));
    const cells = (ids.pickgrid.children || []).filter((n) => n.className
      && n.className.indexOf("cell") >= 0);
    check("...and nothing of the previous list survives the switch",
          cells.length === 1, String(cells.length));
    return updateChecks();
  }).catch((e) => { fails.push("the picker threw: " + e.message);
                    console.log("FAIL the picker threw :: " + e.stack); finish(); });
}

// ---- drag a picture onto the sentence box ---------------------------------
// Clicking and dragging must be the SAME pick.  The pin is what keeps a name
// that matches 29 records from editing the wrong one, so a drag path that forgot
// the pin would silently edit the smallest id while showing the dragged picture.
function dragChecks() {
  return page.loadPick(false).then(() => {
    const cells = (ids.pickgrid.children || []).filter((n) => n.className
      && n.className.indexOf("cell") >= 0);
    const cell = cells[0];
    check("a cell can be picked up (draggable)", cell && cell.draggable === true,
          JSON.stringify(cell && cell.draggable));
    // A real browser only hands out dataTransfer contents on drop, so the page
    // has to remember the row for the length of the drag.
    let stored = null;
    const ev = { dataTransfer: { setData: (k, v) => { stored = [k, v]; },
                                 effectAllowed: "" } };
    cell.ondragstart(ev);
    check("dragging a cell carries its name as plain text",
          stored && stored[0] === "text/plain" && stored[1].indexOf("村民") >= 0,
          JSON.stringify(stored));
    const dragging = page.DRAGGING();
    check("dragging remembers WHICH record, not just the name",
          dragging && dragging.id === 83 && dragging.kind === "unit",
          JSON.stringify(dragging));

    // The box must show it can take the drop, or the gesture is a guess.
    ids.say.className = "";
    const over = { preventDefault() { this.seen = true; }, dataTransfer: {} };
    ids.say.ondragover(over);
    check("the sentence box highlights itself as a drop target",
          ids.say.className.indexOf("dragover") >= 0, ids.say.className);
    check("...and the drag is allowed only for our own cells",
          over.seen === true, String(over.seen));

    // Drop it.
    ids.say.value = "";
    let prevented = false;
    page.dropOnSay({ preventDefault: () => { prevented = true; } });
    check("dropping a cell writes it into the sentence box",
          ids.say.value.indexOf("村民 (男性)") >= 0, ids.say.value);
    check("...and the drop is consumed, not left to the browser",
          prevented === true, String(prevented));
    check("...the highlight clears after the drop",
          ids.say.className.indexOf("dragover") < 0, ids.say.className);
    check("...and the drag is finished, so a second drop does nothing",
          page.DRAGGING() === null, JSON.stringify(page.DRAGGING()));
    const pins = page.PINS();
    check("a dropped cell pins its id exactly like a clicked one",
          pins.length >= 1 && pins[0].id === 83 && pins[0].kind === "unit",
          JSON.stringify(pins));

    // Text dragged in from somewhere else must still paste normally: swallowing
    // a foreign drop would be worse than not supporting drag at all.
    let foreignPrevented = false;
    ids.say.ondrop = page.dropOnSay;
    page.dropOnSay({ preventDefault: () => { foreignPrevented = true; } });
    check("a drop that did not start on a cell keeps the browser default",
          foreignPrevented === false, String(foreignPrevented));
    return Promise.resolve();
  }).catch((e) => { fails.push("the drag threw: " + e.message);
                    console.log("FAIL the drag threw :: " + e.stack); });
}

// ---- the update banner ---------------------------------------------------
// A mod we build ships a whole .dat, so a game patch is silently overwritten by
// the installed copy.  The screen has to say so -- and has to say nothing when
// the only rows it does not recognize are ones it could never know about.
function updateChecks() {
  return page.checkUpdates().then(() => {
    check("a stale mod puts a banner on the screen",
          ids.banner.className.indexOf("open") >= 0, ids.banner.className);
    check("the banner names the mod that needs rebuilding",
          text(ids["banner-msg"]).indexOf("村民血量测试") >= 0,
          text(ids["banner-msg"]));
    // The unknown row is in the same payload.  Counting it would put a warning
    // on screen that nobody can act on.
    check("an unknown mod is not counted as needing attention",
          text(ids["banner-note"]).indexOf("别人做的模组") < 0,
          text(ids["banner-note"]));
    check("the banner offers one button, not one per mod",
          typeof ids["btn-rebuild"].onclick === "function");
    // Rebuilding REINSTALLS.  If only the install button carries the
    // game-running warning, "重建并重装" becomes the one path that looks safe
    // while doing the same rewrite of mod-status.json.
    RUNNING = true;
    return ids["btn-rebuild"].onclick();
  }).then(() => {
    check("the button rebuilds the stale mod by name",
          rebuilt.length === 1 && rebuilt[0] === "村民血量测试",
          JSON.stringify(rebuilt));
    check("a rebuild says the game is open too",
          text(ids.toast).indexOf("游戏正开着") >= 0, text(ids.toast));
    check("and says it as a warning, not a failure",
          ids.toast.className.indexOf("warn") >= 0, ids.toast.className);
    RUNNING = false;
    // After the rebuild the guard answers "nothing to do"; the banner has to go
    // away on its own, or the user is told to fix something already fixed.
    UPDATE_ANSWER = UPDATE.quiet;
    return page.checkUpdates();
  }).then(() => {
    check("the banner disappears once nothing is stale",
          ids.banner.className.indexOf("open") < 0, ids.banner.className);
    finish();
  }).catch((e) => { fails.push("the update banner threw: " + e.message);
                    console.log("FAIL the update banner threw :: " + e.stack);
                    finish(); });
}

function finish() {
  console.log();
  if (fails.length) {
    console.log("PAGE SCRIPT: " + fails.length + " CHECK(S) FAILED -> " +
                JSON.stringify(fails));
    process.exit(1);
  }
  console.log("PAGE SCRIPT: THE SCREEN RENDERS EVERY SHAPE, LETS YOU CLICK OR " +
              "DRAG A PICTURE INTO A SENTENCE, AND POSTS ONLY WHAT IT CAN BUILD");
}
