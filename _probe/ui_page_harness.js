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
  return {
    tagName: (tag || "div").toUpperCase(),
    className: "", textContent: "", innerHTML: "", style: {},
    children: [], value: "", disabled: false, onclick: null, title: "",
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {},
    setAttribute(k, v) { this[k] = v; },
  };
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
      { text: "村民血量改成1000", kind: "unit", entity: "村民", why: null,
        notes: [], candidates: [], intent: { intent: "unit.stat", unit: 83,
        stat: "hit_points", value: 1000 }, buildable: true,
        preview: { ok: true, plan: { description: "村民 生命值 =1000",
          kind: "unit", civ_count: 63, edit_count: 1701, changes_dat: true,
          civ_labels: ["不列颠"], editable: true } } },
      { text: "织布机研究时间加0", kind: "tech", entity: "织布机", why: null,
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
      { text: "织布机研究时间加0", kind: "tech", entity: "织布机", why: null,
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

// ---- run the real script -------------------------------------------------
const posted = [];
const sandbox = {
  document,
  fetch: async (url, opt) => {
    posted.push({ url, body: opt && opt.body ? JSON.parse(opt.body) : null });
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
  "doBuild: doBuild, setLast: (v) => { LAST = v; }};");
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
  page.doBuild().then(() => {
    const call = posted.filter((p) => p.url === "/api/build")[0];
    check("build was called", !!call, JSON.stringify(posted.map((p) => p.url)));
    const sent = call ? call.body.intents : [];
    check("build is sent ONLY the buildable intents", sent.length === 1,
          JSON.stringify(sent));
    check("the refusal never reaches /api/build",
          !sent.some((i) => i.intent === "tech.research_time"),
          JSON.stringify(sent));
    finish();
  }).catch((e) => { fails.push("doBuild threw: " + e.message);
                    console.log("FAIL doBuild threw :: " + e.stack); finish(); });
} catch (e) {
  fails.push("renderClauses threw: " + e.message);
  console.log("FAIL renderClauses threw :: " + e.stack);
  finish();
}

function finish() {
  console.log();
  if (fails.length) {
    console.log("PAGE SCRIPT: " + fails.length + " CHECK(S) FAILED -> " +
                JSON.stringify(fails));
    process.exit(1);
  }
  console.log("PAGE SCRIPT: THE SCREEN RENDERS EVERY SHAPE AND POSTS ONLY WHAT IT CAN BUILD");
}
