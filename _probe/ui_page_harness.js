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
// where the third row has no picture at all.  1,349 of the game's 2,693 units
// ship no icon, so "no picture" is the ordinary case, not an error -- the grid
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
    // 1,349 units ship no icon; the cell must still exist and still be usable.
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
    finish();
  }).catch((e) => { fails.push("the picker threw: " + e.message);
                    console.log("FAIL the picker threw :: " + e.stack); finish(); });
}

function finish() {
  console.log();
  if (fails.length) {
    console.log("PAGE SCRIPT: " + fails.length + " CHECK(S) FAILED -> " +
                JSON.stringify(fails));
    process.exit(1);
  }
  console.log("PAGE SCRIPT: THE SCREEN RENDERS EVERY SHAPE, LETS YOU PICK A " +
              "PICTURE, AND POSTS ONLY WHAT IT CAN BUILD");
}
