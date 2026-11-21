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
    className: "", innerHTML: "",
    // `#pet-vid` 是 `<video>`：宠物球借用动画片时读 `paused`、调 `play()` / `pause()`。
    // 替身的节点都长一样，缺这三个就会在 `petWalkStop()` 里抛
    // "vid.pause is not a function" —— 而那读起来像页面坏了。 play() 必须返回
    // 带 catch 的 promise，页面就是这么接的（自动播放被拒是常态）。
    paused: true,
    play() { this.paused = false; return Promise.resolve(); },
    pause() { this.paused = true; },
    // 偏好设置里那几项（背景、模糊、字号）落到 :root 的自定义属性上，页面用的是
    // `root.style.setProperty("--bgimg", …)`。 一个空的 `{}` 会让整页在加载时
    // 抛 TypeError，而那看起来像页面坏了，其实是替身缺了一个方法。
    style: {
      setProperty(k, v) { this[k] = String(v); },
      removeProperty(k) { delete this[k]; },
      getPropertyValue(k) { return k in this ? this[k] : ""; },
    },
    children: [], value: "", disabled: false, onclick: null, title: "",
    parentNode: null,
    // The form panel labels each control with the slot it fills (`data-slot`),
    // which is how the value reader and the renderer agree on what is on screen.
    dataset: {},
    // Tags applied by the page markup (`data-i18n="key"`).  `applyLocale()`
    // reads these with `getAttribute`, so the stand-in has to answer the same
    // way -- a node that returned undefined for everything would make the whole
    // translation pass look like a no-op and still be green.
    attrs: {},
    getAttribute(k) {
      if (k in this.attrs) return this.attrs[k];
      if (k === "data-slot") return this.dataset.slot;
      if (k === "placeholder") return this.placeholder;
      return null;
    },
    setAttribute(k, v) {
      if (k === "data-slot") { this.dataset.slot = v; return; }
      if (k === "placeholder") { this.placeholder = v; return; }
      this.attrs[k] = v;
    },
    // The pager clears a tooltip when the two counts agree.  Without this the
    // fake DOM would report a page that every browser runs fine.
    removeAttribute(k) {
      this.attrs = this.attrs || {};
      delete this.attrs[k];
    },
    appendChild(c) {
      c.parentNode = this;
      this.children.push(c);
      // A real <select> picks its first <option> by itself, so `select.value`
      // is readable right after the options are added.  A stub that left it ""
      // would make the page look broken in the harness only -- the page is
      // allowed to rely on the browser here, because every browser does this.
      if (this.tagName === "SELECT" && c.tagName === "OPTION" && !this.value) {
        this.value = c.value;
      }
      return c;
    },
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
    // The mods list marks the interface half of a split build with a class.  Real
    // `classList` is what the page calls, so the fake DOM has to have it too --
    // otherwise the harness would be testing a page nobody can ship.
    // A real classList edits className; the page now uses it to show and hide
    // panels (`classList.toggle("hide", …)`) instead of writing inline styles.
    // A stub with no `toggle` made the harness report `classList.toggle is not
    // a function` while every browser was fine -- the fake DOM was the defect.
    classList: null,   // wired below, because it needs `this` to be the node

    // The page moved off HTML5 drag and onto pointer events (the desktop host
    // owns the webview's drop target and swallows `dragstart`), so a no-op
    // `addEventListener` would make every pointer assertion below vacuous.
    // Handlers are kept per type and fired by the harness through `fire`.
    _ev: null,
    // The pointer gesture asks "which row is under this point" by walking up from
    // the node a real `elementFromPoint` returned.  A stand-in without `closest`
    // would make every hit test throw, and the throw would read as a page defect.
    closest(sel) {
      const parts = String(sel).trim().split(/\s+/);
      const last = parts[parts.length - 1];
      const hit = (n) => {
        if (last.charAt(0) === ".") {
          return (n.className || "").split(/\s+/).indexOf(last.slice(1)) >= 0;
        }
        if (last.charAt(0) === "#") {
          return n.id === last.slice(1) || ids[last.slice(1)] === n;
        }
        return true;
      };
      let n = this;
      while (n) { if (hit(n)) return n; n = n.parentNode; }
      return null;
    },
    addEventListener(type, fn) {
      if (!this._ev) this._ev = {};
      (this._ev[type] = this._ev[type] || []).push(fn);
    },
    removeEventListener(type, fn) {
      if (!this._ev || !this._ev[type]) return;
      this._ev[type] = this._ev[type].filter((f) => f !== fn);
    },
    fire(type, ev) {
      const list = (this._ev && this._ev[type]) || [];
      list.slice().forEach((f) => f(ev || {}));
      return list.length;
    },
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
    // The other half of `remove()`: the parent detaches a child it holds.  The
    // page uses it to take back its own placeholder (`_reading`) once `/api/meta`
    // answers, because clearing the whole `#preview` there was measured to wipe
    // a card the player had already parsed.  A stub without it reported
    // `_reading.parentNode.removeChild is not a function` while every browser
    // was fine -- the fake DOM being wrong again.
    removeChild(c) {
      const at = this.children.indexOf(c);
      if (at >= 0) this.children.splice(at, 1);
      if (c) c.parentNode = null;
      return c;
    },
    // Class selectors only, and descendants only -- that is all the page asks
    // for (`drawPager` counts `.edrow`).  Added when the pager started counting
    // rows: without it the harness died with `querySelectorAll is not a
    // function` while every browser was fine, which is the fake DOM being wrong.
    querySelectorAll(sel) {
      const want = String(sel).replace(/^\./, "");
      const out = [];
      const walk = (n) => {
        for (const c of n.children || []) {
          if ((c.className || "").split(/\s+/).indexOf(want) >= 0) out.push(c);
          walk(c);
        }
      };
      walk(this);
      return out;
    },
    get firstChild() { return this.children[0] || null; },
  };
  // A real classList edits className; the page now uses it to show and hide
  // panels (`classList.toggle("hide", …)`) instead of writing inline styles.
  // A stub with no `toggle` made the harness report `classList.toggle is not a
  // function` while every browser was fine -- the fake DOM was the defect.
  Object.defineProperty(n, "classList", {
    value: {
      _set() { return (n.className || "").split(/\s+/).filter(Boolean); },
      _put(list) { n.className = list.join(" "); },
      add(c) { const s = this._set(); if (s.indexOf(c) < 0) s.push(c); this._put(s); },
      remove(c) { this._put(this._set().filter((x) => x !== c)); },
      contains(c) { return this._set().indexOf(c) >= 0; },
      toggle(c, force) {
        const want = force === undefined ? !this.contains(c) : !!force;
        if (want) this.add(c); else this.remove(c);
        return want;
      },
    },
  });

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
  // `textContent` is an accessor in the real DOM too, and writing it replaces
  // every child with one text node.  The page leans on that to empty a list
  // before filling it (`box.textContent = ""`); a plain field kept the old rows,
  // so the second fill drew eight rows where a browser shows four and the
  // duplicate read as a page that forgot to clear.  `innerHTML` already did
  // this -- `textContent` was the other half of the same rule.
  let _text = "";
  Object.defineProperty(n, "textContent", {
    get() { return _text; },
    set(v) {
      _text = (v === null || v === undefined) ? "" : String(v);
      n.children.length = 0;
    },
    enumerable: true,
    configurable: true,
  });
  return n;
}
const ids = {};
// The page adds `dragging-row` to `document.body` for the length of a gesture
// (it changes the cursor for the whole window), so the stand-in needs a body.
let DOC_HIT = null;
const document = {
  body: node("body"),
  // 偏好设置的开关把自定义属性写在文档根上（`applyBg()`），diagnostics 还读
  // `documentElement.clientWidth` 判断有没有横向滚动。 真浏览器里它一直在。
  documentElement: node("html"),
  createElement: node,
  // The tech-tree legend puts the label beside a colour swatch with
  // `createTextNode`, because `textContent` on the span would replace the
  // swatch it just appended.  A stub without this crashed the whole script
  // at load time -- every check in the file then reported the same TypeError.
  createTextNode(text) {
    const n = node("#text");
    n.textContent = String(text);
    return n;
  },
  // The page reaches for two things by id: `#railbar` (it inserts its own
  // "which file" row before it on a re-render) and a preview row it names
  // itself (`ufx-note-<tech>-<command>`).  A stub without this crashed the whole
  // boot path the moment the fixture carried a `dat` block, which reads as
  // "the page is broken" rather than "the stand-in is".
  // The pointer drag listens on the DOCUMENT with capture, because the pointer
  // leaves the row on the first pixel of the gesture.  A stand-in that dropped
  // those listeners would test a page nobody can ship -- the same class of defect
  // as the missing `textContent` setter.
  _ev: null,
  addEventListener(type, fn) {
    if (!this._ev) this._ev = {};
    (this._ev[type] = this._ev[type] || []).push(fn);
  },
  removeEventListener(type, fn) {
    if (!this._ev || !this._ev[type]) return;
    this._ev[type] = this._ev[type].filter((f) => f !== fn);
  },
  fire(type, ev) {
    const list = (this._ev && this._ev[type]) || [];
    return Promise.all(list.slice().map((f) => f(ev || {})));
  },
  // `document.elementFromPoint` is how the page decides which row the pointer is
  // over.  A headless run has no layout, so the harness sets the answer for the
  // length of one gesture -- and resets it, so a check that leaks cannot pass.
  elementFromPoint(x, y) {
    return (typeof DOC_HIT === "function") ? DOC_HIT(x, y) : null;
  },
  getElementById(id) {
    const k = String(id);
    if (!ids[k]) ids[k] = node(k);
    return ids[k];
  },
  querySelector(sel) {
    const key = sel.replace(/^#/, "");
    if (!ids[key]) ids[key] = node(sel);
    return ids[key];
  },
  // `applyLocale()` walks every tagged node, so the stand-in needs the same
  // shape.  It deliberately returns a real array rather than a NodeList: the
  // page calls `.forEach` on it, and a live NodeList would hide the case where
  // a node is tagged twice (both would come back, and the second would win
  // silently).
  querySelectorAll(sel) {
    const attr = String(sel).replace(/^\[|\]$/g, "");
    const out = [];
    const walk = (n) => {
      if (n.attrs && n.attrs[attr] !== undefined) out.push(n);
      for (const c of n.children || []) walk(c);
    };
    for (const k of Object.keys(ids)) walk(ids[k]);
    return out;
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
  // A real /api/parse answer for "不列颠照村民做一个新单位，叫铁匠学徒，放在第5格".
  // `free_buttons` is trimmed to a few numbers so the assertions can name them;
  // everything else is the server's own text.  The donor resolves to 1810
  // (村民), not 83 (村民 (男性)) -- that is the real resolution, and the card it
  // trains from is 修道院 (104), whose box 14 already holds five units.
  newUnit: {
    ok: true,
    clauses: [
      { text: "不列颠照村民做一个新单位，叫铁匠学徒，放在第5格",
        kind: "unit", entity: "村民", entity_id: 1810, why: "",
        notes: ["放在命令卡的第 5 格", "照「村民」做，名字是「铁匠学徒」"],
        class_word: null, candidates: [],
        intent: { intent: "unit.create", donor: 1810, civ: "British",
          name: "铁匠学徒", button: 5 },
        buildable: true,
        preview: { ok: true, plan: {
          description: "照 村民 在 不列颠 做一个新单位「铁匠学徒」，放在 修道院 的第 5 格",
          entity_id: 1810, entity_name: "村民", kind: "unit", shape: "new_unit",
          donor_id: 1810, donor_name: "村民", new_name: "铁匠学徒",
          changes_dat: true, civ: "British", editable: true, new_id: 382,
          string_id: 30030002, creation_string_id: 30030003,
          creation_text: "生产铁匠学徒", record_bytes: 2378, edit_count: 2,
          buttons: [14], builder_ids: [104], builder_names: ["修道院"],
          free_buttons: { "104": [0, 2, 3, 7] },
          warnings: ["新单位的图标是照着做的那个单位的（图标的号 0..999 已满，"
            + "这个工具不会去改图标那层）"] } } },
    ],
  },
  // The same sentence without a box: the picker must still appear, because the
  // choice exists whether or not the player has typed it yet.
  newUnitNoBox: {
    ok: true,
    clauses: [
      { text: "不列颠照村民做一个新单位，叫铁匠学徒",
        kind: "unit", entity: "村民", entity_id: 1810, why: "",
        notes: ["照「村民」做，名字是「铁匠学徒」"],
        class_word: null, candidates: [],
        intent: { intent: "unit.create", donor: 1810, civ: "British",
          name: "铁匠学徒" },
        buildable: true,
        preview: { ok: true, plan: {
          description: "照 村民 在 不列颠 做一个新单位「铁匠学徒」",
          entity_id: 1810, entity_name: "村民", kind: "unit", shape: "new_unit",
          donor_id: 1810, donor_name: "村民", new_name: "铁匠学徒",
          changes_dat: true, civ: "British", editable: true, new_id: 382,
          buttons: [14], builder_ids: [104], builder_names: ["修道院"],
          free_buttons: { "104": [0, 2, 3, 7] }, warnings: [] } } },
    ],
  },
  // A donor whose training entry points at no building: there is no card, so the
  // picker must NOT appear -- offering boxes for a card that does not exist is
  // the page promising something the product already refused.
  newUnitNoCard: {
    ok: true,
    clauses: [
      { text: "不列颠照斯托尔特贝克做一个新单位，叫测试兵，放在第3格",
        kind: "unit", entity: "斯托尔特贝克", entity_id: 114, why: "",
        notes: [], class_word: null, candidates: [],
        intent: { intent: "unit.create", donor: 114, civ: "British",
          name: "测试兵", button: 3 },
        buildable: false,
        preview: { ok: true, plan: {
          description: "照 斯托尔特贝克 在 不列颠 做一个新单位「测试兵」",
          entity_id: 114, entity_name: "斯托尔特贝克", kind: "unit",
          shape: "new_unit", donor_id: 114, donor_name: "斯托尔特贝克",
          changes_dat: true, civ: "British", editable: false,
          reason: "「斯托尔特贝克」的建造位置没有指向任何建筑（记录里的建筑编号是 "
            + "-1），所以第 3 格没有一块命令卡可以放",
          buttons: [7], builder_ids: [], builder_names: [],
          free_buttons: {}, warnings: [] } } },
    ],
  },
  // A class edit: one sentence, 28 records, the same value written into every
  // civilization's copy.  The preview says "1,764 处改动" either way, so without
  // the member count the screen cannot tell a 28-record edit from a 1,764-record
  // one -- and those are different promises.
  classEdit: {
    ok: true,
    clauses: [
      { text: "所有步兵血量加10", kind: "unit", entity: null, entity_id: null,
        why: null, notes: ["这一句改的是「步兵」整类，不是某一个单位"],
        class_word: "步兵", candidates: [],
        intent: { intent: "unit.stat", unit_class: 6, stat: "hit_points",
          delta: 10 },
        buildable: true,
        preview: { ok: true, plan: { description: "所有步兵 生命值 +10",
          kind: "unit", civ_count: 63, edit_count: 13671, member_count: 217,
          changes_dat: true, editable: true, entity_id: null } } },
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
// A real /api/locale answer, captured from the shipped table
// (`aoe2mod/schema/locales/zh.json`).  Only the keys the assertions below name
// are pasted in; the rest of the table is wording no assertion reads, and a
// fixture nobody can scan is a fixture nobody checks.
const LOCALE = {ok: true, locale: "zh", strings: {
  "page.heading": "帝国时代 2 DE · 模组工坊",
  "page.version": "游戏版本 {version}",
  "page.ready": "{civs} 个文明",
  "btn.parse": "读一下",
  "btn.build": "生成并安装",
  "mods.heading": "已安装的模组",
  "preview.heading": "预览 —— 还没动任何文件",
  "say.heading": "你想要什么改动？用中文说就行",
  "status.stale": "游戏更新过了，要重建",
  "update.banner": "游戏数据在你装这些模组之后更新过：{names}。"
    + "它们带着旧的一整份 .dat，会把更新盖掉；重建一次就好。",
  // 检查更新那五句。和上面的 update.banner 是两条不同的消息：一个说模组要
  // 重建，一个说工具有没有新版。表里少一句，`T()` 就会把键名原样印到屏幕上。
  "update.checking": "正在问 GitHub…",
  "update.version_ahead": "远端只有 {version}，比这一份还旧，不用管",
  "update.version_behind": "远端有 {version}：按「下载并装好」，它自己会换掉这一份，装完重新打开",
  "update.version_offline": "连不上 GitHub，这一份是不是最新就不知道了；过一会儿再按一次",
  "update.version_same": "{version} 已经是最新的",
  "btn.form": "✎ 填表",
  "pick.unit": "单位",
  "pick.search": "在这个列表里找…"
}};

const FORMS = {
  ok: true,
  forms: [
    { intent: "unit.stat", intent_label: "改单位属性", id: "value",
      label: "把某一项设成某个数", template: "{unit} {stat} 改成 {n}",
      slots: [
        { name: "unit", kind: "unit", label: "单位", sample: "村民" },
        { name: "stat", kind: "stat", label: "属性", required: true, sample: "血量" },
        { name: "n", kind: "number", label: "改成", sample: "1000" },
      ] },
    { intent: "unit.stat", intent_label: "改单位属性", id: "delta",
      label: "加减一点", template: "{unit} {stat} {op}{n}",
      slots: [
        { name: "unit", kind: "unit", label: "单位", sample: "村民" },
        { name: "stat", kind: "stat", label: "属性", required: true, sample: "血量" },
        { name: "op", kind: "op", label: "怎么改", required: true, default: "加" },
        { name: "n", kind: "number", label: "数值", sample: "10" },
      ] },
    { intent: "unit.create", intent_label: "做一个新单位", id: "clone",
      label: "照着现成的单位做一个",
      template: "{civ}照{donor}做一个新单位，叫{name}",
      slots: [
        // No `sample` on the civ on purpose: that is how the real table ships it,
        // and the page must put a closed list there rather than a text box.
        { name: "civ", kind: "civ", label: "给哪个文明", required: true },
        { name: "donor", kind: "unit", label: "照着谁做", sample: "村民" },
        { name: "name", kind: "text", label: "新单位叫什么", required: true,
          sample: "铁匠学徒" },
      ] },
  ],
  op_choices: ["改成", "加", "减"],
};
// Saved sentences.  Two entries on purpose: one that the reader accepts and one
// whose sentence is nonsense, because the list must show what is STORED, not what
// the reader would accept -- a list that quietly hid the second one would look
// tidier and would be lying about what the file holds.
const RECIPES = {ok: true, file: "C:\\Users\\x\\AppData\\Local\\aoe2de-mod-workshop\\recipes.json",
  recipes: [
    { name: "我的伐木场", sentences: ["波兰的伐木场木材成本减少 10", "村民血量改成1000"],
      count: 2, saved_at: "2026-10-26 10:31", note: "" },
    { name: "旧的写法", sentences: ["把村民血量变成很多"], count: 1,
      saved_at: "2026-10-20 08:02", note: "" },
  ]};

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

// /api/version-check 的三种答案。它不是 /api/update-check 的别名：那个问的是
// 磁盘上游戏的 .dat 变没变，这个问的是远端仓库里这一份工具自己有没有新版。
// behind 是唯一会让人去下载的状态，所以它必须点名远端版本号。
const VERSIONS = {
  behind: { ok: true, reachable: true, cached: false, current: "1.0",
            remote: "1.1", behind: true, same: false, can_update: true,
            changes: ["远端说这一版多了什么", "第二行"],
            mine: ["这一份自己写了什么"],
            source: "raw", url: "https://raw.githubusercontent.com/x/appversion.py",
            project_url: "https://github.com/198agk/aoe2-mod-workshop",
            checked_at: "2026-11-17 20:00", notes: [] },
  same: { ok: true, reachable: true, cached: true, current: "1.0",
          remote: "1.0", behind: false, same: true, source: "cache",
          can_update: true,
          changes: ["这一份自己写了什么"], mine: ["这一份自己写了什么"],
          url: "", project_url: "https://github.com/198agk/aoe2-mod-workshop",
          checked_at: "2026-11-17 20:00", notes: [] },
  offline: { ok: true, reachable: false, cached: false, current: "1.0",
             remote: "", behind: false, same: false, source: "", url: "",
             changes: ["这一份自己写了什么"], mine: ["这一份自己写了什么"],
             project_url: "https://github.com/198agk/aoe2-mod-workshop",
             checked_at: "", notes: ["连不上"] },
};
let VERSION_ANSWER = VERSIONS.behind;
// /api/version-changelog 的答案：GitHub 的发布记录，最新的在上。 关于页要能
// 翻到以前每一版改了什么，所以这一份是好几条，而不是一条。
let CHANGELOG_ANSWER = { ok: true, reachable: true, cached: false,
  rows: [
    { version: "1.0004", name: "模组工坊 1.0004", date: "2026-11-18",
      notes: ["关于页加了完整更新日志", "日志只写改了什么"], url: "" },
    { version: "1.0003", name: "模组工坊 1.0003", date: "2026-11-17",
      notes: ["下载新版的网络慢，现在快多了"], url: "" },
    { version: "1.0002", name: "模组工坊 1.0002", date: "2026-11-16",
      notes: ["有新版时可以直接按按钮装好"], url: "" },
  ] };
const changelogAsked = [];
// 这一份是不是装好的副本（`/api/meta` 的 `app_can_update`）。 源码目录里跑的那
// 一份是 false：没有可以替换的 app/，按钮不该出现。
let CAN_UPDATE = true;
// 按下「下载并装好」之后服务端的回答，和进度槽里现在这一轮的答案。
const INSTALL_ANSWER = { ok: true, key: "update", started: true, root: "C:\\x" };
let JOB_ANSWER = { key: "update", label: "正在下载新版", percent: 0, done: 0,
  total: 100, elapsed: 0, running: false, error: null, known: false, seq: 0 };
const installAsked = [];
const rebuilt = [];
// The game-running warning, as a switchable state: the same install route must
// say something when the game is open and NOTHING when it is closed (a warning
// shown always is a warning nobody reads).
let RUNNING = true;
// Whether `/api/locale` answers.  `false` reproduces the case the page's inline
// Chinese exists for: the fetch failed, and stale wording beats blank headings.
let LOCALE_FAIL = false;
let STR_BEFORE = 0;
// The second folder a split build installs (null = this build is one mod).
let UI_HALF = null;
const RUNNING_TEXT = "游戏正开着。它退出时会用自己记得的模组列表覆盖 mod-status.json，"
  + "所以这次写进去的改动可能被盖掉（文件还在，列表里没有）。装完回游戏里看一眼，"
  + "或者关掉游戏再写一次。";
// The build route's answer: {manifest} with a mod_dir, then the install POST.
const BUILD_ANSWER = { ok: true, manifest: { mod_dir: "/tmp/x",
  info: { Title: "x" } } };// What the stub echoes back as the used Title, and a switch that makes it come
// back SHORTER than it went in -- which is what the engine's 100-byte cap does
// to an auto title made of Chinese sentences.
let BUILT_TITLE = "x";
let TRIM = false;
// Did the page mark the title it sent as one IT wrote (`title_auto`)?  Only such
// a title may be trimmed to the engine's 100-byte limit; one the player typed is
// refused with a sentence instead.
let AUTO_SENT = null;
// Refusals the bundle reports in its own manifest: a build can succeed and still
// drop a sentence (two reskin sentences want one file to hold two pictures).
// The page must say so -- shipping 21 files while the screen says "已生成并安装"
// is a silent half-done job.
let DROPPED = [];
// Warnings the manifest carries back from a SUCCESSFUL build.  They are learned
// at write time, so the preview cannot have them: a JSON override that is
// byte-identical to the shipped file would pin it to today's content, and one
// folder carrying several layers changes which data mod the player must pick.
// Measured 2026-10-23: a real grant build returned 8 warnings with
// `verification.ok` true and the page rendered none of them.
let BUILD_WARNINGS = [];

// What /api/upgrade-check answers: four installed mods that ship their own .dat,
// one per verdict that can be acted on or must be refused.  The page's job is to
// say which of them this tool can carry forward and to offer the button ONLY on
// those -- a stub where every row looked migratable would let a page that drew
// the button unconditionally pass, and the player would be offered an upgrade
// for a mod from a data generation we never archived.
//
// The shapes are the route's own (`aoe2mod/ui/server.py:7202`): `verdict`,
// `counts.edits`, `conflict_count`, `unmapped_count`, `summary`, `notes`.  A
// stub that answered the OLD route (`/api/repair-check`, verdicts
// `auto/manual/impossible`) left this harness green while the page asked a
// question nobody answered -- 2026-11-09.
// The batch checks below run this fixture a second time, and the apply stub
// rewrites `UPGRADE_ANSWER` in place.  Without a pristine copy the second run
// would start from one `up_to_date` row and prove nothing.
let UPGRADE_ANSWER = {
  ok: true, count: 4,
  official: { ok: true, count: 12 },
  mods: [
    // The `summary` strings below are the ENGINE's own shape, not a prose
    // paraphrase: `aoe2mod/mod/upgrade.py:2376 describe(rep)` opens with
    // 「判定：」「要搬的改动：」「耗时：」, and on a refusal it puts the SAME
    // sentence in `summary` and in `notes[0]` (measured against the shipped
    // route 2026-11-10: `297820_10 倍资源文明联盟3倍科技` returned one sentence
    // twice).  A stub of one-line prose let the page print the whole block and
    // still pass -- which is exactly how 19 rows of doubled text shipped.
    { name: "dsh test v46", title: "村民血量一组", verdict: "mergeable",
      enabled: true, counts: { edits: 5 }, conflict_count: 0, unmapped_count: 0,
      summary: "判定：mergeable\n要搬的改动：5 处字段\n作者的 5 处改动都能搬到新版上。\n耗时：0.62 秒",
      notes: [] },
    // The conflict rows are grouped and translated by the route ('aoe2mod/
    // api.py' _conflict_rows): one line per DECISION, not per record.  The
    // measured case is 57 rows in 4 groups -- 54 civilizations holding one
    // field, plus three copies of one tech prerequisite -- so the fixture keeps
    // that shape, including a group whose civilization count is larger than one.
    // A stub of two identical rows would let a page that prints 54 lines pass.
    { name: "167396_Red Alert 2 MOD", title: "Red Alert 2", verdict: "conflicts",
      enabled: true, counts: { edits: 555 }, conflict_count: 57,
      unmapped_count: 0,
      conflict_kinds: 2,
      conflict_rows: [
        { space: "unit", where: "单位 1971 火焰弓箭手", civ: "54 个文明（不列颠 等）",
          civs: 54, field: "Type50.DisplayedAttack", field_zh: "显示攻击力",
          official: 5, mod: 4, base: 0,
          official_hex: "05", mod_hex: "04", won: "mod" },
        { space: "tech", where: "第 216 号科技 Farms (make avail)", civ: "",
          civs: 0, field: "RequiredTechs.2", field_zh: "前置科技 3",
          official: 1357, mod: 1770, base: -1,
          official_hex: "4d05", mod_hex: "ea06", won: "mod" },
      ],
      summary: "判定：conflicts\n要搬的改动：555 处字段\n官方也改过同一处：57 处，也就是 2 个字段（按你的改法）\n耗时：1.24 秒",
      notes: [] },
    { name: "10 倍资源", title: "10 倍资源文明联盟3倍科技", verdict: "impossible",
      enabled: true, counts: { edits: 0 }, conflict_count: 0,
      unmapped_count: 0,
      summary: "判定：impossible\n要搬的改动：0 处字段\n档案库里还没有 VER 7.8 这一代的官方数据。\n耗时：0.51 秒",
      notes: ["档案库里还没有 VER 7.8 这一代的官方数据。"] },
    { name: "dsh test v61", title: "自己的图标", verdict: "up_to_date",
      enabled: true, counts: { edits: 0 }, conflict_count: 0,
      unmapped_count: 0,
      summary: "判定：up_to_date\n要搬的改动：0 处字段\n这份 .dat 已经是新版了，不用动。\n耗时：0.58 秒",
      notes: [] },
  ],
};
// A deep copy taken before anything mutates the fixture. `repairChecks()`
// clicks a row button, and the apply stub rewrites the answer in place, so by
// the time the batch checks run the live fixture holds a single `up_to_date`
// row. Rerunning from that would prove nothing about a batch of two.
const UPGRADE_PRISTINE = JSON.parse(JSON.stringify(UPGRADE_ANSWER));
const repairedNow = [];
// What the page actually POSTed, not just WHICH mod: a batch that silently
// flipped `official_wins` to true would keep the names right and carry the
// official value over the author's edit, which is the one outcome the row
// button asks a question about.
const appliedBodies = [];
// The roster route's answer.  Empty for every check that drives the scan
// directly (a roster in the way would mean those checks test the roster), and
// filled in by rosterChecks() to prove the chip list is drawn and is what
// decides the scope of the run.
let CANDIDATES = null;

// What /api/ai-meta and /api/ai-sentences answer.  The whole point of this entry
// is that the model's output is SENTENCES and nothing else, so the stub hands
// back text and the page must put it in the box for the ordinary reader to judge
// -- a stub that returned an intent would let a page that applied model output
// directly pass this harness and edit bytes on screen.  `AI_OFF` is the state
// without the three environment variables: the button must not be drawn at all,
// because an AI box that always fails is worse than no box.
let AI_ON = {
  ok: true, available: true, model: "some-model",
  base: "http://127.0.0.1:9/v1", writes: "sentences", grammar: "…",
};
let AI_OFF = {
  ok: true, available: false, model: "", base: "", writes: "sentences",
  grammar: "…",
};
let AI_ANSWER = AI_ON;
const aiAsked = [];

// What /api/mods answers.  Two mods, one of which carries a whole .dat and the
// other of which does not, because the badge the page draws is "this one competes
// for the single data-mod slot" -- and a stub where every mod looked the same
// would let the page print that badge on the wrong row.
const removed = [];

let MODS = [
  { name: "dsh mine", title: "dsh 我的数据模组", enabled: true, kind: "local",
    priority: 3, ships_dat: true, dat_rank: 1, dat_competing: 1,
    role: "data", paired_with: "dsh 我的数据模组（界面）",
    author: "aoe2mod", description: "生命值 单位「SVMBAS」：25 → 137",
    thumb: "thumbnail.png", exists: true },
  { name: "dsh mine（界面）", title: "dsh 我的数据模组（界面）", enabled: true,
    kind: "local", priority: 4, ships_dat: false, dat_rank: null,
    dat_competing: 1, role: "ui", paired_with: "dsh 我的数据模组",
    author: "aoe2mod", description: "", thumb: "thumbnail.jpg", exists: true },
  { name: "someone else", title: "别人做的 UI 模组", enabled: true,
    kind: "subscribed", priority: 9, ships_dat: false, dat_rank: null,
    dat_competing: 1, role: null, paired_with: null,
    author: "", description: "Content comes from the community.",
    thumb: "", exists: true },
];

// What /api/meta answers for the 能做的事 box.  One shipped intent (reachable by
// a sentence) and one a plugin added (`by_sentence: false`), because the defect
// this pins is exactly that the box used to list both as equally available:
// a plugin intent is in the schema but the sentence layer is hand-written, so
// only the API can drive it.  A stub where every intent had `by_sentence: true`
// would make the caveat untestable.
const META_INTENTS = [
  { id: "unit.stat", title: "改数值", by_sentence: true },
  { id: "unit.set_stat", title: "把一项属性设成某个值（插件示例）",
    by_sentence: false },
];

// What /api/dat-sources answers.  Three scopes, deliberately in an order the
// page must not keep: `mod-b` sorts before `Game` alphabetically, so a stub in
// path order would let a page that never sorted look correct.  `mod-a` is the
// one being edited AND the one the game reads; `mod-b` is enabled and loses;
// `mode` has no format (a user pointed at something that is not a .dat).
const DATS = [
  { path: "C:/x/dat/empires2_x2_p1.dat", scope: "mod", mod: "mod-a",
    label: "mod-a", format: 54, supported: true, current: true, head: "VER 8.9" },
  { path: "C:/x/modes/x/empires2_x2_p1.dat", scope: "mode", mod: null,
    label: "modes/x", format: 54, supported: true, current: false, head: "VER 8.9" },
  { path: "C:/x/mod-b/widgetui/junk.dat", scope: "mod", mod: "mod-b",
    label: "mod-b", format: null, supported: false, current: false, head: "" },
  { path: "C:/games/AoE2DE/dat/empires2_x2_p1.dat", scope: "game", mod: null,
    label: "游戏本体", format: 54, supported: true, current: false, head: "VER 8.9" },
];

// What the parse route answers.  Most sections want the two-edit answer; the
// new-unit section swaps in a creating sentence, because whether the box picker
// appears is decided by the PLAN, and only a real creating sentence has one.
let PARSE_ANSWER = FIXTURES.mixed;

// ---- run the real script -------------------------------------------------
const posted = [];
const versionAsked = [];
let RECIPE_ANSWER = RECIPES;
let RECIPES_FAIL = false;
const savedNow = [];
const forgotten = [];
// 页面顶层有一句不带守卫的 `window.addEventListener("resize", …)`（宠物球贴边重排），
// 还有几处 `typeof window !== "undefined"` 的分支。 浏览器里 window 是天生就有的，
// 替身里没有它，整段脚本在加载期就抛 ReferenceError，读起来像页面坏了。
// `getSelection` 故意留成 undefined：页面那些守卫会因此跳过选区清理，正好。
const window = {
  addEventListener() {}, removeEventListener() {},
  __TAURI_INTERNALS__: null,
  confirm: () => false,
  innerWidth: 1264, innerHeight: 821,
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  location: { href: "", assign() {}, replace() {} },
};

const sandbox = {
  document,
  window,
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
    // The form panel's table.  Captured from the live route, so a page that
    // guesses at the slot list is caught here rather than on screen.
    if (url.indexOf("/api/forms") === 0) {
      return { json: async () => FORMS };
    }
    // The screen's own wording, captured from the live `/api/locale`.  A stub
    // that answered `{ok: true}` with no `strings` would let `applyLocale()`
    // return early, and every wording assertion below would stay green while
    // the page showed its stale inline copy.
    if (url.indexOf("/api/locale") === 0) {
      if (LOCALE_FAIL) throw new Error("locale route unreachable");
      return { json: async () => LOCALE };
    }
    // A parse answer is also forwarded to renderClauses, so the stub has to
    // hand back a real one rather than the generic meta-shaped object.
    if (url.indexOf("/api/parse") === 0) {
      return { json: async () => PARSE_ANSWER };
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
      // `DROPPED` stands in for what the real manifest calls `sprite_refusals`:
      // sentences the bundle succeeded without.  The page must print them, or a
      // half-done job looks finished.
      return { json: async () => ({ ok: true, manifest: { mod_dir: "/tmp/x",
        info: { Title: BUILT_TITLE }, sprite_refusals: DROPPED,
        warnings: BUILD_WARNINGS } }) };
    }
    // Saved sentences.  The route is read on boot and after every save/delete, so
    // the stub's answer is a live variable: a page that cached the first response
    // and never re-read would pass a fixed stub and fail on screen.
    if (url.indexOf("/api/recipes") === 0) {
      if (RECIPES_FAIL) throw new Error("recipes route unreachable");
      return { json: async () => RECIPE_ANSWER };
    }
    if (url.indexOf("/api/recipe-forget") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      forgotten.push(body.name);
      RECIPE_ANSWER = { ok: true, recipes: (RECIPE_ANSWER.recipes || [])
        .filter((r) => r.name !== body.name) };
      return { json: async () => ({ ok: true, removed: true }) };
    }
    if (url.indexOf("/api/recipe") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      savedNow.push(body);
      // Answer with the server's own two shapes: a refusal for a bad name (so the
      // page has to print the reason rather than assume success), and a stored row
      // for a good one.
      if (!body.name || !(body.sentences || []).length) {
        return { json: async () => ({ ok: false,
          error: "配方要有个名字，不然下次没法叫它出来。" }) };
      }
      const row = { name: body.name, sentences: body.sentences,
                    count: body.sentences.length, saved_at: "2026-10-26 10:50",
                    note: "" };
      RECIPE_ANSWER = { ok: true, recipes: (RECIPE_ANSWER.recipes || [])
        .filter((r) => r.name !== body.name).concat([row]) };
      return { json: async () => ({ ok: true, recipe: row }) };
    }
    if (url.indexOf("/api/update-install") === 0) {
      installAsked.push(url);
      return { json: async () => INSTALL_ANSWER };
    }
    if (url.indexOf("/api/job?key=update") === 0) {
      return { json: async () => ({ ok: true, job: JOB_ANSWER }) };
    }
    if (url.indexOf("/api/version-changelog") === 0) {
      // 更新日志是另一条路由：它要的是全部版本，而 version-check 只答这一次。
      changelogAsked.push(url);
      return { json: async () => CHANGELOG_ANSWER };
    }
    if (url.indexOf("/api/version-check") === 0) {
      // 版本检查问的是这一份工具本身，和 /api/update-check（问磁盘上游戏的
      // .dat 有没有被游戏改过）是两件事。答案形状照抄服务端的扁平结构。
      versionAsked.push(url);
      return { json: async () => VERSION_ANSWER };
    }
    if (url.indexOf("/api/update-check") === 0) {
      // The route wraps its answer the way the server does ({ok, update}); a stub
      // that returned the bare rows would let a page bug (reading the wrong
      // level) pass here and fail on screen.
      return { json: async () => ({ ok: true, update: UPDATE_ANSWER }) };
    }
    // The route the page asks (`/api/upgrade-check`).  The old
    // `/api/repair-check` is still served, so it is answered too -- but with the
    // upgrade shape, because that is what the box reads now: answering it with
    // the retired shape would make a page that went back to the old route look
    // right here and wrong on screen.
    if (url.indexOf("/api/upgrade-check") === 0
        || url.indexOf("/api/repair-check") === 0) {
      return { json: async () => UPGRADE_ANSWER };
    }
    // The roster route: one directory walk, no .dat opened.  It is what the
    // FIRST press of 自检更新模组 asks, so the chip list is drawn
    // before anything is parsed.  Left empty by default, because the other
    // checks drive the check directly and a roster in their way would mean they
    // test the roster instead.
    if (url.indexOf("/api/upgrade-candidates") === 0) {
      return { json: async () => CANDIDATES || { ok: true, profile_root: "/tmp/p",
        mods: [], count: 0 } };
    }
    // The AI entry.  Note the answer carries no intent, no plan and no bytes --
    // only the sentences a model would have written.  If a future page tried to
    // build straight from this, there would be nothing here to build from.
    if (url.indexOf("/api/ai-meta") === 0) {
      return { json: async () => AI_ANSWER };
    }
    if (url.indexOf("/api/ai-sentences") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      aiAsked.push(body.text);
      return { json: async () => ({ ok: true, ai: {
        ok: true, model: "some-model",
        sentences: ["村民血量改成 1000", "弓箭手攻击力加 2"],
      } }) };
    }
    if (url.indexOf("/api/upgrade-apply") === 0
        || url.indexOf("/api/repair-apply") === 0) {
      const body = opt && opt.body ? JSON.parse(opt.body) : {};
      repairedNow.push(body.name);
      appliedBodies.push(body);
      // An upgrade reinstalls, so it carries the same game-running answer as
      // install/rebuild.  After a successful upgrade the row must read as
      // nothing-left-to-do, because the whole claim is "same edits, same base
      // data, same bytes" -- if the page kept showing 可以更新, the user would
      // click again.
      //
      // `upgraded` is what the engine sets when its own build record says this
      // file was written by the updater against the official data the game
      // ships today; the row prints 已完成更新 for that and 本来就是新版 for a mod
      // that was simply built on this data long ago.  The fixture carries it or
      // the page could not tell the two apart at all.
      UPGRADE_ANSWER = {
        ok: true, count: 1, official: { ok: true, count: 12 }, mods: [
          { name: "dsh test v46", title: "村民血量一组", verdict: "up_to_date",
            enabled: true, counts: { edits: 0 }, conflict_count: 0,
            unmapped_count: 0, upgraded: { title: "村民血量一组", at: "2026-11-21T15:08:34" },
            summary: "这份模组上一次是「一键更新」搬过来的，自那以后官方数据没有再变，不用再更新。",
            notes: [] },
        ],
      };
      return { json: async () => ({ ok: true, manifest: {}, installed: {
        installed: true, game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null,
      } }) };
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
        // `install()` puts the interface half here when the build was split.  The
        // shape below is what `install_mod` returns for the second folder.
        ui_install: UI_HALF,
      } }) };
    }
    // The mods route: the switch POSTs here, and the answer carries the
    // game-running warning the page must not throw away.  A stub without
    // `running_warning` would make "toggling while the game runs says so"
    // untestable -- the page would read `undefined` and look fine.
    // The mods screen's data-file picker.  `/api/dat-set` is answered with the
    // new meta so the page can redraw the "which file" line from the same
    // request -- that is what the real route does.
    if (url.indexOf("/api/dat-sources") === 0) {
      return { json: async () => ({ ok: true, current: DATS[0].path,
                                    sources: DATS }) };
    }
    if (url.indexOf("/api/dat-set") === 0) {
      const body = posted[posted.length - 1].body || {};
      for (const d of DATS) d.current = (d.path === body.path);
      return { json: async () => ({ ok: true, changed: true, dropped: 0 }) };
    }
    // Dragging a row to a new place.  The body carries `position` (1-based);
    // the answer is the whole reordered list, which is what the page redraws.
    // The stub has to really reorder: a page that posted the right body but
    // drew a stale list would look correct here and be wrong on screen.
    if (url.indexOf("/api/mod-move-to") === 0) {
      const body = posted[posted.length - 1].body || {};
      const at = MODS.findIndex((m) => m.name === body.name);
      if (at >= 0) {
        const item = MODS.splice(at, 1)[0];
        const want = Math.max(0, Math.min(body.position - 1, MODS.length));
        MODS.splice(want, 0, item);
      }
      return { json: async () => ({ ok: true, mods: MODS,
        game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null }) };
    }
    // 另存为.  A copy is a NEW row, so the stub has to add one -- a stub that
    // answered with the old list would let the page "succeed" while the row the
    // player just made never appears, which is the bug this route fixes.
    if (url.indexOf("/api/mod-copy") === 0) {
      const body = posted[posted.length - 1].body || {};
      const src = MODS.filter((m) => m.name === body.name)[0] || {};
      const made = body.new_name || (String(src.title || src.name) + " 副本");
      MODS = MODS.concat([{ name: made, title: made, enabled: true,
        kind: "local", priority: MODS.length + 1, ships_dat: true,
        author: src.author || "aoe2mod", description: src.description || "",
        thumb: null, exists: true, workshop_id: 0, role: "data" }]);
      return { json: async () => ({ ok: true,
        copy: { name: body.name, new_name: made, title: made },
        mods: MODS, game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null }) };
    }
    if (url.indexOf("/api/mod") === 0) {
      return { json: async () => ({ ok: true, mods: MODS,
        game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null }) };
    }
    // The remove button.  The answer carries the remaining list (the page
    // re-renders from it rather than splicing locally) and the same
    // game-running warning the switch gets.
    if (url.indexOf("/api/uninstall") === 0) {
      // `posted` records the PARSED body, so it must not be parsed again.
      const gone = posted[posted.length - 1].body || {};
      removed.push(gone.name);
      MODS = MODS.filter((m) => m.name !== gone.name);
      return { json: async () => ({ ok: true, mods: MODS,
        game_running: RUNNING,
        running_warning: RUNNING ? RUNNING_TEXT : null }) };
    }
    // `dat` and `dat_loads` are what the data-file picker and the "which file"
    // line read.  The winner here is deliberately NOT the file being edited:
    // when those two are the same file the page can print one label and still
    // be wrong about the other, and nothing would notice.
    return { json: async () => ({ ok: true, version: 54, civs: new Array(63),
      app_version: "1.0001",
      app_changes: ["这一份自己写了什么"],
      // 装新版那颗按钮只在「这一份确实是装好的副本」时才有意义。 从源码目录跑
      // 的那份没有可替换的 app/，服务端因此把这个布尔值报成 false。
      app_can_update: CAN_UPDATE,
      intents: META_INTENTS, mods: [], manifest: { mod_dir: "/tmp/x", info: {} },
      dat: { path: DATS[2].path, scope: "mod", label: "mod-a", mod: "mod-a",
             head: "VER 8.9", supported: true },
      dat_loads: { reads: "other", competing: 2,
                   winner: { name: "mod-b", title: "mod-b wins", priority: 6 } } }) };
  },
  setTimeout: () => 0, clearTimeout: () => {},
  console,
  JSON,
};
const fn = new Function(
  "document", "window", "fetch", "setTimeout", "clearTimeout", "console", "JSON",
  // 页面在几个地方起计时器（宠物球、数据面纱）。 node 的 setInterval 会真的挂住
  // 事件循环，脚本跑完不退出；requestAnimationFrame 在 node 里根本不存在。
  "setInterval", "clearInterval", "requestAnimationFrame", "cancelAnimationFrame",
  src + "\n;return {renderClauses: renderClauses, buildable: buildable, " +
  "doBuild: doBuild, doParse: doParse, renderDetail: renderDetail, " +
  "loadPick: loadPick, pickCell: pickCell, pickName: pickName, " +
  "setPickKind: setPickKind, PICK: () => PICK, PINS: () => PINS, " +
  "dropOnSay: dropOnSay, DRAGGING: () => DRAGGING, " +
  "checkUpdates: checkUpdates, rebuildAll: rebuildAll, " +
  "versionCheck: versionCheck, VERSION_ASKED: () => versionAsked, " +
  "installUpdate: installUpdate, installTick: installTick, " +
  "INSTALL_ASKED: () => installAsked, " +
  "VERSION_FIXTURE: () => VERSION_ANSWER, " +
  "loadChangelog: loadChangelog, drawChangelog: drawChangelog, " +
  "CHANGELOG_ANSWER: () => CHANGELOG_ANSWER, " +
  "CHANGELOG_ASKED: () => changelogAsked, " +
  "checkRepairs: checkRepairs, adaptAll: adaptAll, " +
  "TODO: () => ADAPT_TODO, UPGRADE_FIXTURE: () => UPGRADE_ANSWER, " +
  "APPLIED: () => appliedBodies, " +
  "REPAIRED: () => repairedNow, " +
  "UPGRADE_VERDICT_ZH: UPGRADE_VERDICT_ZH, " +
  "aiBoot: aiBoot, doAI: doAI, " +
  "renderMods: renderMods, setModsView: setModsView, MODSVIEW: () => MODSVIEW, " +
  "loadDatPicker: loadDatPicker, " +
  "renderIntentList: renderIntentList, " +
  "loadForms: loadForms, renderShapes: renderShapes, " +
  "formValues: formValues, renderFormPreview: renderFormPreview, " +
  "FSHAPE: () => FSHAPE, FORM_NODES: () => FSLOT_NODES, " +
  "boot: boot, " +
  "loadLocale: loadLocale, applyLocale: applyLocale, T: T, STR: () => STR, " +
  "loadRecipes: loadRecipes, renderRecipes: renderRecipes, RECIPES: () => RECIPES, " +
  "setLast: (v) => { LAST = v; }};");
const page = fn(sandbox.document, sandbox.window, sandbox.fetch, sandbox.setTimeout,
                sandbox.clearTimeout, sandbox.console, sandbox.JSON,
                () => 0, () => {}, () => 0, () => {});

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
        ids.commit.classList.contains("open"),
        ids.commit.className);
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
        !ids.commit.classList.contains("open"),
        ids.commit.className);
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

  // ---- a class edit says how many units it reaches ----------------------
  // The byte count alone is not enough: 1,764 处改动 over 28 records and over
  // 1,764 records read identically on screen, and they are different promises.
  page.renderClauses(FIXTURES.classEdit.clauses);
  const clsEditText = text(ids.preview);
  check("a class edit says how many units it reaches",
        clsEditText.indexOf("217 个单位") >= 0, clsEditText);
  check("...next to the byte count, not instead of it",
        clsEditText.indexOf("13671 处改动") >= 0, clsEditText);
  page.renderClauses(FIXTURES.mixed.clauses);
  check("a single-unit edit does not claim a unit count in the plural",
        text(ids.preview).indexOf("个单位") < 0, text(ids.preview));
  page.setLast(FIXTURES.mixed);
  // Render it again: the checks above rendered the OTHER payloads, and the
  // preview box holds only the last one.  (Reading it without re-rendering found
  // 0 pictures -- a real answer to the wrong question, not a page defect.)
  page.renderClauses(FIXTURES.mixed.clauses);
  const boxes = walk(ids.preview, []);
  // Count only the pictures inside clause ROWS.  The game card draws its own
  // tiles from the same route, so a page-wide IMG count now answers a different
  // question -- it went from 2 to 4 the day the card landed, and the card is the
  // subject of its own check below.
  const clauseRows = boxes.filter((n) => String(n.className || "").indexOf("clause") === 0);
  const icos = clauseRows.reduce((acc, r) => acc.concat(
    walk(r, []).filter((n) => n.tagName === "IMG")), []);
  check("each understood clause asks for its own picture",
        icos.length === 2, String(icos.length));
  check("the picture is requested from the real route with the entity id",
        icos.length > 0 && icos[0].src.indexOf("/api/icon?kind=unit&id=83") === 0,
        icos.length ? icos[0].src : "(none)");
  const dets = boxes.filter((n) => n.className === "detailrow");
  check("an understood clause offers the game's own words", dets.length === 2,
        String(dets.length));

  // ---- the game's command card ------------------------------------------
  // The goal asks for a 假游戏界面.  What a player recognises is the bottom card:
  // one square per unit, the box number in the corner, a bar underneath.  A form
  // is not that, and until 2026-10-26 this page had none of it (a full-text
  // search for `hud`, `command-card`, `resource-bar` found nothing).
  //
  // Two things this must NOT become: a tile for a clause whose plan refuses
  // (that would be the "ticked something impossible" bug in picture form), and a
  // corner number on a clause whose plan names no box (inventing a position).
  const tiles = boxes.filter((n) => String(n.className || "").indexOf("tile") === 0);
  check("the screen draws a game-shaped card", tiles.length > 0, String(tiles.length));
  check("the card only holds what can actually be built",
        tiles.length === FIXTURES.mixed.clauses.filter((c) => c.buildable).length,
        tiles.length + " tiles vs " + FIXTURES.mixed.clauses.filter((c) => c.buildable).length + " buildable");
  const slots = boxes.filter((n) => String(n.className || "") === "slot");
  check("a tile shows the box number only when the plan names one",
        slots.length === 0,
        slots.length ? "claimed a box: " + slots.map(text).join(",") : "none claimed");
  const cardImgs = tiles.reduce((acc, t) => acc.concat(
    walk(t, []).filter((n) => n.tagName === "IMG")), []);
  check("each tile draws the game's own picture",
        cardImgs.length === tiles.length, cardImgs.length + " of " + tiles.length);

  // A plan that DOES name a box must show it, or the card is decorative.
  const boxed = { text: "照村民做一个新单位，叫铁匠学徒，放在第5格",
    intent: { intent: "unit.create" }, kind: "unit", entity: "村民",
    entity_id: 83, buildable: true,
    preview: { ok: true, plan: { description: "照 村民 做一个新单位「铁匠学徒」",
                                 builder_names: ["修道院"], button: 5, editable: true } } };
  page.renderClauses([boxed]);
  const b2 = walk(ids.preview, []);
  const s2 = b2.filter((n) => String(n.className || "") === "slot");
  check("a plan that names a box draws its number", s2.length === 1,
        s2.length ? text(s2[0]) : "(none)");
  check("...and the number is the plan's own", s2.length === 1 && text(s2[0]) === "5",
        s2.length ? text(s2[0]) : "(none)");
  const cap = b2.filter((n) => String(n.className || "") === "cap");
  check("...and the caption names the building the box is on",
        cap.length === 1 && text(cap[0]) === "修道院",
        cap.length ? text(cap[0]) : "(none)");

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
    // A build that ships a `.dat` puts its `widgetui` layer in a second folder.
    // The screen has to say so: enabling only the data half is the state measured
    // not to draw a single icon, and nothing about it looks broken.
    check("a one-mod build does not talk about two",
          text(ids.buildnote).indexOf("两个模组") < 0, text(ids.buildnote));
    UI_HALF = { name: "村民血量（界面）", priority: 1,
                files: ["widgetui/icons.json"] };
    return page.doBuild();
  }).then(() => {
    UI_HALF = null;
    const two = text(ids.buildnote);
    check("a split build says there are two mods", two.indexOf("两个模组") >= 0, two);
    check("and it names the interface half", two.indexOf("（界面）") >= 0, two);
    check("and it tells the player both must be enabled",
          two.indexOf("两个都要") >= 0, two);
    check("and it still names the data mod in the dropdown",
          two.indexOf("数据模组") >= 0, two);
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
    // A bundle can succeed and still drop one of the sentences.  Two reskin
    // sentences that want one file to hold two pictures cannot both be honoured;
    // the manifest names the one it dropped, and the screen must print it --
    // otherwise the player reads "已生成并安装" and believes both took effect.
    DROPPED = [{ reason: "「把步弓手的样子换成长弓兵」和「把步弓手的样子换成弩手」"
                        + "都要写 u_arc_archer_attackA_x1.sld 这个文件，"
                        + "可一个文件装不下两张不同的画" }];
    ids.title.value = "";
    page.renderClauses(FIXTURES.mixed.clauses);
    return page.doBuild();
  }).then(() => {
    check("a sentence the build dropped is named on screen",
          text(ids.buildnote).indexOf("有一句没做成") >= 0
          && text(ids.buildnote).indexOf("装不下两张") >= 0,
          text(ids.buildnote));
    check("a dropped sentence is a warning, not a failure",
          !walk(ids.buildnote, []).some((n) => n.className === "err"),
          JSON.stringify(walk(ids.buildnote, []).map((n) => n.className)));
    DROPPED = [];
    return page.doBuild();
  }).then(() => {
    check("a complete build says nothing about dropped sentences",
          text(ids.buildnote).indexOf("有一句没做成") < 0, text(ids.buildnote));
    // A build that SUCCEEDS can still learn something at write time that the
    // preview could not know.  Measured 2026-10-23: `unit.availability` grant of
    // unit 775 to Armenians returns 8 warnings next to `verification.ok: true`,
    // and the page printed none of them -- the same shape as the preview-side
    // `plan.warnings` gap fixed just before, one layer further along the same
    // pipeline.  The stub echoes the two shapes a real manifest carries.
    BUILD_WARNINGS = [
      "「名字」是从捐赠方那一行照抄下来的，不是为这个文明写的",
      "有 1 个 JSON 覆盖文件和本机那份逐字节相同，这等于把这个文件钉在今天的内容上",
    ];
    ids.title.value = "";
    page.renderClauses(FIXTURES.mixed.clauses);
    return page.doBuild();
  }).then(() => {
    check("a successful build's own warnings reach the screen",
          text(ids.buildnote).indexOf("照抄下来的") >= 0,
          text(ids.buildnote));
    check("...and the later one is there too, not just the first",
          text(ids.buildnote).indexOf("钉在今天的内容上") >= 0,
          text(ids.buildnote));
    check("...and they are warnings, not failures",
          !walk(ids.buildnote, []).some((n) => n.className === "err"),
          JSON.stringify(walk(ids.buildnote, []).map((n) => n.className)));
    BUILD_WARNINGS = [];
    return pickChecks();
    return null;
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
    return modsChecks();
  }).catch((e) => { fails.push("the picker threw: " + e.message);
                    console.log("FAIL the picker threw :: " + e.stack); finish(); });
}

// ---- the mod list says which mod the next match will load ------------------
// The single hardest thing for a newcomer: a match loads exactly ONE data mod,
// the game picks it by priority, and none of that is visible anywhere except a
// dropdown on the create-game screen.  A list that says "installed" for twenty
// mods tells the player nothing about whether their edit is in the next game.
function modsChecks() {
  page.renderMods(MODS);
  const rows = (ids.mods.children || []).filter((n) => n.className === "mod");
  check("one row per installed mod", rows.length === 3, String(rows.length));
  const all = walk(ids.mods, []);
  const labels = all.map((n) => n.textContent || "").join(" | ");
  // The badge is gone on purpose (the player, 2026-10-26: "把这个去掉").  A data
  // mod is chosen in the game's own 数据模组 dropdown, so a rank or a state word
  // here describes a decision this page cannot make.  What must NOT happen is the
  // badge growing back -- not the rank, not "没启用", not a replacement phrase.
  check("a data mod carries no rank badge",
        labels.indexOf("排第") < 0, labels);
  check("and no state word either",
        labels.indexOf("数据模组 ·") < 0, labels);
  check("a mod that is not a data mod gets no such badge",
        labels.indexOf("别人做的 UI 模组") >= 0
        && labels.indexOf("数据模组 · 别的") < 0);
  // A split build is two folders and ONE decision.  The interface half must say
  // which build it belongs to; two unnamed rows invite switching off half of a
  // build, which is the state measured to draw no icon at all while looking fine.
  check("the interface half says which build it belongs to",
        labels.indexOf("界面半边") >= 0, labels);
  check("and a mod with no other half is not marked as one",
        labels.indexOf("界面半边") === labels.lastIndexOf("界面半边")
        || rows.filter((n) => text(n).indexOf("界面半边") >= 0).length === 1,
        String(rows.filter((n) => text(n).indexOf("界面半边") >= 0).length));
  // A DISABLED data mod matters: it is in the folder, it looks installed, and the
  // game will not use it.  Saying "排第 0" would be worse than saying nothing.
  const off = [{ name: "dsh mine", title: "dsh 我的数据模组", enabled: false,
                 kind: "local", priority: 3, ships_dat: true, dat_rank: null,
                 dat_competing: 0 }];
  page.renderMods(off);
  // The wording moved on 2026-10-26: "没启用" named a state with no way out of it,
  // because a data mod gets no switch here (the player's words: 数据模组不需要去启用
  // 的).  Pin the FACT the badge has to carry -- never a rank, and it points at the
  // place the choice really is made -- instead of the phrase of the day.
  const offText = text(ids.mods);
  check("a disabled data mod never claims a rank",
        offText.indexOf("排第") < 0, offText);
  check("and gets no badge at all, enabled or not",
        offText.indexOf("数据模组 ·") < 0, offText);
  check("it still gets no switch, because the game chooses it",
        walk(ids.mods, []).filter(
          (n) => n.className === "switch" || n.className === "switch on"
        ).length === 0,
        String(walk(ids.mods, []).filter(
          (n) => n.className === "switch" || n.className === "switch on").length));

  // ---- the two views ---------------------------------------------------
  // A card is a different SHELL for the same rows, and the counter above is
  // `className === "mod"`.  If the card branch had written `"mod card"` every
  // check in this block would have counted zero rows and passed by measuring
  // nothing -- which is the exact failure this family of assertions exists for.
  page.renderMods(MODS);
  page.setModsView("card");
  const cards = (ids.mods.children || []).filter((n) => n.className === "mod");
  check("the card view draws the same one-`mod`-per-row",
        cards.length === 3, String(cards.length));
  check("...and puts the mode on the container, never on the row",
        ids.mods.classList.contains("cards") && cards[0].className === "mod",
        ids.mods.className + " / " + (cards[0] || {}).className);
  const inCards = walk(ids.mods, []);
  const pics = inCards.filter((n) => n.className === "thumb");
  const none = inCards.filter((n) => n.className === "nothumb");
  check("a mod that ships a picture draws one, and one that does not says so",
        pics.length === 2 && none.length === 1,
        pics.length + " pictures, " + none.length + " placeholders");
  check("the picture is fetched from the route that serves it",
        pics.length === 2 && pics.every((p) => String(p.src || "").indexOf("/api/mod-thumb?name=") === 0),
        pics.map((p) => p.src).join(","));
  const cardText = text(ids.mods);
  check("the description is printed as the author wrote it",
        cardText.indexOf("生命值 单位「SVMBAS」：25 → 137") >= 0, cardText);
  check("a mod with no description says that instead of drawing a blank line",
        cardText.indexOf("这个模组没有写简介。") >= 0, cardText);
  check("the author is named",
        cardText.indexOf("作者 aoe2mod") >= 0, cardText);
  const cardCtl = inCards.filter(
    (n) => n.className === "move" || n.className === "remove"
          || (n.className || "").indexOf("switch") === 0).length;
  page.setModsView("list");
  const listCtl = walk(ids.mods, []).filter(
    (n) => n.className === "move" || n.className === "remove"
          || (n.className || "").indexOf("switch") === 0).length;
  check("every control the row had is still there in the card",
        cardCtl === listCtl && cardCtl > 0, cardCtl + " vs " + listCtl);
  check("switching back to the list takes the card shell off",
        !ids.mods.classList.contains("cards")
        && walk(ids.mods, []).filter((n) => n.className === "thumb").length === 0,
        ids.mods.className);

  // ---- dragging a row to a new place -----------------------------------
  // Load order IS the conflict order: the first data mod wins a fight over the
  // same bytes.  Two arrows move one position per press, which is 17 presses to
  // go from last to first in this machine's 18 mods.  A drag says where.
  //
  // `draggable` is FALSE on purpose: the desktop host owns the webview's drop
  // target, so an HTML5 drag is consumed before the page sees it, and asking the
  // browser for one is how a row comes to look clickable and do nothing.
  const dragRows = (ids.mods.children || []).filter((n) => n.className === "mod");
  placeRows(dragRows);
  check("every row answers the pointer, not the HTML5 drag",
        dragRows.length === 3 && dragRows.every((r) => r.draggable === false),
        dragRows.map((r) => String(r.draggable)).join(","));
  check("and carries a pointerdown handler for it",
        dragRows.every((r) => r._ev && (r._ev.pointerdown || []).length === 1),
        dragRows.map((r) => String((r._ev && (r._ev.pointerdown || []).length))).join(","));
  // A drag from the last row onto the FIRST row's top half; the position that
  // must travel is 1, and the body must say `position`, never `delta`.
  const before = posted.length;
  return pointerDrag(dragRows, 2, 0, "top", () => {
    check("hovering while carrying marks the row the drop would land on",
          dragRows[0].classList.contains("dragover")
          && !dragRows[1].classList.contains("dragover"),
          dragRows.map((r) => r.className).join(" / "));
    check("and the row being carried is marked too",
          dragRows[2].classList.contains("dragging"),
          dragRows[2].className);
  }).then(() => {
    const sent = posted[posted.length - 1] || {};
    check("the drop posts a target position, not a delta",
          String(sent.url || "").indexOf("/api/mod-move-to") === 0
          && (sent.body || {}).position === 1
          && (sent.body || {}).delta === undefined,
          JSON.stringify(sent));
    check("the row that was dragged is the one named",
          (sent.body || {}).name === "someone else", JSON.stringify(sent.body));
    const after = (ids.mods.children || []).filter((n) => n.className === "mod");
    check("and the list comes back in the new order",
          text(after[0]).indexOf("别人做的 UI 模组") === 0,
          after.map((n) => text(n).slice(0, 6)).join(" | "));
    check("the highlight came off with the drop",
          (ids.mods.children || []).filter(
            (n) => (n.className || "").indexOf("dragover") >= 0).length === 0,
          (ids.mods.children || []).map((n) => n.className).join(" / "));
    check("the count of posts grew by exactly one", posted.length === before + 1,
          String(posted.length - before));
    return datPickerChecks();
  });

}

// Which .dat, on the mods screen.  The picker lived in the editor's tab bar and
// only filled on view entry, which is why the same request arrived twice.
function datPickerChecks() {
  page.renderMods(MODS);
  return Promise.resolve(page.loadDatPicker(true)).then(() => {
    const rows = (ids["dp-list"].children || [])
      .filter((n) => String(n.className).indexOf("dprow") >= 0);
    check("the mods screen lists every data file the game could load",
          rows.length === 4, String(rows.length));
    // The fixture is listed mod, mode, mod, game: alphabetical order would put
    // `mod-b` first.  A page that never sorted still draws four rows.
    const scopes = rows.map((r) => {
      const cells = (r.children || []).filter(
        (c) => String(c.className).indexOf("dpscope") >= 0);
      return cells.length ? text(cells[0]) : "?";
    });
    check("game first, then mode, then mod -- not alphabetical",
          scopes.join(",") === "游戏本体,模式,模组,模组", scopes.join(","));
    check("the file being edited says so exactly once",
          rows.filter((r) => text(r).indexOf("正在改") >= 0).length === 1,
          rows.map((r) => text(r)).join(" | "));
    check("...and it does not offer to switch to itself",
          rows.filter((r) => text(r).indexOf("正在改") >= 0)
            .every((r) => !(r.children || []).some(
              (c) => String(c.className).indexOf("chip") >= 0)),
          "a 改这一份 button on the current file");
    // "Being edited" and "the game reads it" are different questions: five
    // enabled data mods compete and the highest priority wins.  The row used to
    // answer the second one with a「游戏现在读的是它」badge; asked to remove it
    // (2026-11-07,「这个不需要，去掉吧」), so the ROW no longer says it and the
    // header above the list still does.  Both halves are worth pinning: a silent
    // return of the badge would put fifteen labels back on fifteen rows.
    check("no row says which file the game reads",
          rows.every((r) => text(r).indexOf("游戏现在读的是它") < 0),
          rows.map((r) => text(r)).join(" | "));
    check("...the header above the list still does",
          text(ids["dp-note"]).indexOf("优先级最高的是") >= 0,
          text(ids["dp-note"]));
    check("a file whose format cannot be read says so instead of a number",
          rows.some((r) => text(r).indexOf("格式读不出来") >= 0),
          rows.map((r) => text(r)).join(" | "));
    const note = text(ids["dp-note"]);
    check("the header says which file wins when several mods are enabled",
          note.indexOf("优先级最高的是") >= 0, note);
    // Asked for on 2026-11-21: 「应该改成目前已选的 dat」.  The note used to answer
    // only the game's side, so a player editing `mod-a` read a sentence about the
    // base copy.  The selection must come first, and by name.
    check("...and names the file being edited, before it says what the game reads",
          note.indexOf("目前改的是「mod-a」") === 0, note);
    check("...with the scope of that file spelled out",
          note.indexOf("（模组带的那一份）") >= 0, note);
    const before = posted.filter((p) => p.url.indexOf("/api/dat-set") === 0)
                         .length;
    const go = rows.filter((r) => (r.children || []).some(
      (c) => String(c.className).indexOf("chip") >= 0))[0];
    const btn = (go.children || []).filter(
      (c) => String(c.className).indexOf("chip") >= 0)[0];
    return Promise.resolve(btn.onclick()).then(() => {
      const sent = posted.filter((p) => p.url.indexOf("/api/dat-set") === 0);
      check("改这一份 really switches the session",
            sent.length === before + 1,
            String(sent.length - before));
      check("...by path, not by label",
            (sent[sent.length - 1].body || {}).path === DATS[3].path,
            JSON.stringify(sent[sent.length - 1].body));
      const now = (ids["dp-list"].children || [])
        .filter((n) => String(n.className).indexOf("dprow") >= 0);
      // The list is sorted game-first, so the file just switched to is row 0 --
      // asserting "the last row is marked" would fail on a correct page.
      check("...and the list redraws with the new file marked",
            now.filter((r) => text(r).indexOf("正在改") >= 0).length === 1
            && text(now[0]).indexOf("正在改") >= 0,
            now.map((r) => text(r)).join(" | "));
      // The switch moved the selection to the base game, and the note has to
      // follow it: a note that kept naming `mod-a` would be answering a stale
      // question, which is the same class of bug as answering the wrong one.
      check("the header follows the switch instead of keeping the old answer",
            text(ids["dp-note"]).indexOf("目前改的是「游戏本体」") === 0,
            text(ids["dp-note"]));
      check("...and still says the game reads the other file",
            text(ids["dp-note"]).indexOf("优先级最高的是") >= 0,
            text(ids["dp-note"]));
      return modInfoChecks();
    });
  }).catch((e) => {
    fails.push("the data-file picker threw: " + e.message);
    console.log("FAIL the data-file picker threw :: " + e.stack);
    return modInfoChecks();
  });
}

// 另存为, on the mods screen.  Reported 2026-11-21: 「这个改模组名字和简介没有另存为
// 功能」.  The save above rewrites the ONE `info.json` in place, so a player who
// wanted their own name on a shipped mod had no way to keep the shipped name.
// Two things have to hold and neither is visible from the source: the copy is a
// NEW ROW the page draws from the route's answer, and the SOURCE row survives.
function modInfoChecks() {
  const keep = MODS.slice();
  page.renderMods(MODS);
  const field = ids["modinfo-copy-name"];
  check("the copy-as box is prefilled with the current name, not left empty",
        String(field.value) === "dsh 我的数据模组 副本", String(field.value));
  check("...and the note still says the save above only edits info.json",
        text(ids["modinfo-note"]).indexOf("info.json") >= 0,
        text(ids["modinfo-note"]));
  const before = posted.length;
  return Promise.resolve(ids["modinfo-copy"].onclick()).then(() => {
    const sent = posted[posted.length - 1] || {};
    check("另存为 posts to its own route, not to the in-place save",
          String(sent.url || "").indexOf("/api/mod-copy") === 0
          && posted.length === before + 1, JSON.stringify(sent));
    check("...naming the source mod and the new name",
          (sent.body || {}).name === "dsh mine"
          && (sent.body || {}).new_name === "dsh 我的数据模组 副本",
          JSON.stringify(sent.body));
    const rows = (ids.mods.children || []).filter((n) => n.className === "mod");
    check("the copy appears as a row of its own",
          rows.length === 4 && rows.some((n) => text(n).indexOf("副本") >= 0),
          rows.map((n) => text(n).slice(0, 10)).join(" | "));
    check("...and the mod it came from is still there",
          rows.some((n) => text(n).indexOf("dsh 我的数据模组") === 0),
          rows.map((n) => text(n).slice(0, 10)).join(" | "));
    check("the panel says what it wrote",
          text(ids["modinfo-copy-msg"]).indexOf("已另存为") >= 0,
          text(ids["modinfo-copy-msg"]));
    // The player just made the copy; the panel should be pointed at it, so the
    // next thing they do (write its description) lands on the right mod.
    check("...and moves the selection onto the copy",
          String(ids["modinfo-title"].value) === "dsh 我的数据模组 副本",
          String(ids["modinfo-title"].value));
    // Put the fixture back: later sections count mods and the copy would be a
    // phantom fourth row in all of them.
    MODS = keep;
    page.renderMods(MODS);
    return dragDownChecks();
  }).catch((e) => {
    fails.push("另存为 threw: " + e.message);
    console.log("FAIL 另存为 threw :: " + e.stack);
    MODS = keep;
    page.renderMods(MODS);
    return dragDownChecks();
  });
}

// Rows have no layout in a stub, so `getBoundingClientRect` has to be given
// one.  Without it the page reads every drop as "on the near half" and the
// half-of-the-row rule is never exercised -- the check would pass whichever
// branch the page happened to have.
function placeRows(rows) {
  rows.forEach((r, i) => {
    r.getBoundingClientRect = () => ({top: i * 30, left: 0,
                                      width: 300, height: 30, bottom: i * 30 + 30});
  });
}

// One whole mouse gesture, exactly the way the page hears it: press on a row,
// move the pointer (the page listens on the DOCUMENT, capture, because the
// pointer leaves the row on the first pixel), release.  `half` is "top" or
// "bottom" of the row it is over.
//
// This replaced a two-line `ondragstart`/`ondrop` pair.  The pair was green on a
// page that could not be dragged at all: the shipped window's host owns the
// webview's drop target and swallows HTML5 drag before the page sees it, so the
// stand-in was testing a code path no user could reach.
function pointerDrag(rows, fromAt, ontoAt, half, during) {
  const from = rows[fromAt];
  const onto = rows[ontoAt];
  const startY = fromAt * 30 + 15;
  const y = ontoAt * 30 + (half === "bottom" ? 25 : 5);
  DOC_HIT = () => onto;
  const down = (n) => n.fire("pointerdown", {
    button: 0, clientX: 10, clientY: startY, target: n,
    preventDefault() {}, stopPropagation() {}});
  check("pressing a row starts a gesture", down(from) === 1,
        String(down(from)));
  return document.fire("pointermove", {clientX: 10, clientY: y,
                                       preventDefault() {}}).then(() => {
    // The highlight lives for the length of the gesture and comes off with the
    // drop, so anything that asks about it has to look HERE -- between the move
    // and the release.  Looking afterwards reported "no row is marked" about a
    // row that had been marked the whole time.
    if (during) during();
    DOC_HIT = null;
    return document.fire("pointerup", {clientX: 10, clientY: y,
                                       preventDefault() {}});
  });
}

// The row is taken OUT before it is put back, so every slot after it shifts
// down one.  Without that subtraction a drop one row down is a no-op and a drop
// on itself moves one row -- both look like "the mouse is unreliable".
function dragDownChecks() {
  page.renderMods(MODS);
  const rows = (ids.mods.children || []).filter((n) => n.className === "mod");
  placeRows(rows);
  const head = text(rows[0]).slice(0, 6);
  const second = text(rows[1]).slice(0, 6);
  // Row 0 dropped on row 1's TOP half means "put it just before row 1" -- which
  // is where it already is.  After the removal shift the target is index 0
  // again, so nothing may be sent.  (The BOTTOM half is a real one-row swap,
  // and that case is exercised by the two-row drop below.)
  const before = posted.length;
  return pointerDrag(rows, 0, 1, "top").then(() => {
    check("a drop that lands where the row already is sends nothing",
          posted.length === before, String(posted.length - before));
    // The same drag onto row 2's bottom half really moves it past two rows.
    page.renderMods(MODS);
    const rows2 = (ids.mods.children || []).filter((n) => n.className === "mod");
    placeRows(rows2);
    return pointerDrag(rows2, 0, 2, "bottom");
  }).then(() => {
    const sent = posted[posted.length - 1] || {};
    check("a drop past two rows asks for the third place",
          (sent.body || {}).position === 3, JSON.stringify(sent.body));
    const now = (ids.mods.children || []).filter((n) => n.className === "mod");
    check("and the row that was first is now third",
          text(now[2]).slice(0, 6) === head && text(now[0]).slice(0, 6) === second,
          now.map((n) => text(n).slice(0, 6)).join(" | "));
    // Cards are the same rows with a different shell: a card that cannot be
    // dragged would make the mode the player asked for the one that cannot
    // reorder anything.
    page.renderMods(MODS);
    page.setModsView("card");
    const cards = (ids.mods.children || []).filter((n) => n.className === "mod");
    placeRows(cards);
    check("a card answers the pointer too",
          cards.length === 3
          && cards.every((r) => r._ev && (r._ev.pointerdown || []).length === 1),
          cards.map((r) => String((r._ev && (r._ev.pointerdown || []).length))).join(","));
    page.setModsView("list");
    return toggleChecks();
  });
}

// The switch's own checks.  These used to sit after a `return` inside
// `modsChecks`, where nothing reached them: the harness still exited 0 and its
// summary line simply never printed.
function toggleChecks() {
  page.renderMods(MODS);
  // Toggling while the game runs is the case where the list on screen and the
  // list the game will use can differ.  The server computes the warning; the page
  // used to throw it away and only say "已停用".
  RUNNING = true;
  const sw = (ids.mods.children || [])
    .filter((n) => n.className === "mod")
    .map((n) => (n.children || []).filter((c) => c.className
      && c.className.indexOf("switch") === 0)[0])
    .filter(Boolean)[0];
  return Promise.resolve(sw && sw.onclick ? sw.onclick() : null).then(() => {
    check("toggling a mod while the game runs repeats the warning",
          text(ids.toast).indexOf("游戏正开着") >= 0, text(ids.toast));
    // The other half: with the game closed the same route must be SILENT.  A
    // warning that always shows is a warning nobody reads -- and the first version
    // of this check asserted `true`, which tests nothing at all.
    RUNNING = false;
    const rows2 = (ids.mods.children || []).filter((n) => n.className === "mod");
    const sw2 = rows2.length > 1
      ? (rows2[1].children || []).filter((c) => c.className
          && c.className.indexOf("switch") === 0)[0]
      : null;
    return Promise.resolve(sw2 && sw2.onclick ? sw2.onclick() : null);
  }).then(() => {
    check("and says nothing extra when the game is closed",
          text(ids.toast).indexOf("游戏正开着") < 0, text(ids.toast));
    return removeChecks();
  });
}

// ---- the form panel -------------------------------------------------------
// The panel is the answer to "用中文说就行" being unfriendly if you do not
// already know the syntax.  Two things can go wrong and neither throws:
//   (1) the panel builds a sentence the reader would refuse -- a second,
//       untested way to change bytes;
//   (2) a slot with no `sample` renders as an empty box and the preview says
//       nothing, so the player has no idea what is missing.
// It also must not invent values: a form that prefills its placeholders would
// send a sentence the player never asked for.
// A slot row is [label, control]; the control is the child carrying `data-slot`.
// Reading it that way (rather than by index) means a change in the label markup
// cannot silently point every assertion at a `<label>`.
function controlOf(wrap) {
  const kids = (wrap && wrap.children) || [];
  for (const c of kids) {
    if (c.dataset && c.dataset.slot) return c;
  }
  return kids[kids.length - 1] || null;
}

function fillShape(shapeId, values) {
  ids.fshape.value = shapeId;
  ids.fshape.onchange();
  const nodes = page.FORM_NODES();
  page.FSHAPE().slots.forEach((slot, i) => {
    const ctl = controlOf(nodes[i]);
    if (ctl && Object.prototype.hasOwnProperty.call(values, slot.name)) {
      ctl.value = values[slot.name];
    }
  });
  page.renderFormPreview();
}

function formChecks() {
  ids.say.value = "";
  // Touch the panel through the same selector the page uses: `ids.form` only
  // exists once something has called `$("#form")`, and asserting on a node the
  // page never asked for would test nothing.
  document.querySelector("#form").className = "";
  // The toggle is async -- it fetches the table the first time it opens -- so the
  // harness has to await it, exactly as the browser does before the panel exists.
  return Promise.resolve(ids["btn-form"].onclick()).then(() => {
    check("the panel asks the forms route instead of hard-coding a table",
          posted.some((p) => p.url.indexOf("/api/forms") === 0),
          JSON.stringify(posted.map((p) => p.url).slice(-3)));
    check("the panel is open after the first click",
          document.querySelector("#form").className === "open",
          document.querySelector("#form").className);
    check("every intent in the table gets one entry in the intent picker",
          (ids.fintent.children || []).length === 2,
          JSON.stringify((ids.fintent.children || []).map((n) => n.value)));
    check("selecting an intent offers its shapes",
          (ids.fshape.children || []).length === 2,
          JSON.stringify((ids.fshape.children || []).map((n) => n.value)));
    // Every slot must get a control; a shape whose slots are dropped would
    // compose a sentence with braces still in it.
    check("each slot of the chosen shape gets a control",
          (ids.fslots.children || []).length === 3,
          String((ids.fslots.children || []).length));
    // An empty form is not a sentence: placeholders are hints, not values.
    check("an empty form previews nothing rather than a prefilled guess",
          text(ids.fpreview).indexOf("还差") === 0, text(ids.fpreview));
    check("...and the button refuses to write an incomplete sentence",
          (ids.say.value || "") === "", ids.say.value);

    const fill = (shapeId, values) => fillShape(shapeId, values);

    fillShape("value", { unit: "村民", stat: "血量", n: "1000" });
    check("a filled form composes exactly the sentence the reader accepts",
          text(ids.fpreview) === "村民 血量 改成 1000", text(ids.fpreview));
    ids.fuse.onclick();
    check("writing it into the box appends, keeping what was already there",
          (ids.say.value || "").indexOf("村民 血量 改成 1000") >= 0,
          ids.say.value);
    // And the composed sentence goes through the ORDINARY reader -- the harness
    // proves the request, the round-trip nail proves the reader accepts it.
    ids.say.value = "村民 血量 改成 1000";
    PARSE_ANSWER = FIXTURES.mixed;
    return page.doParse();
  }).then(() => {
    check("the composed sentence is read like any typed one",
          posted.filter((p) => p.url.indexOf("/api/parse") === 0).length >= 1,
          JSON.stringify(posted.map((p) => p.url).slice(-3)));

    // A civ slot is a closed list: typing a civilization by hand is how you get
    // "不列颠" vs "不列颠人" and a refusal that reads like a tool bug.
    ids.fintent.value = "unit.create";
    ids.fintent.onchange();
    const nodes = page.FORM_NODES();
    const civWrap = nodes[0];
    const civCtl = controlOf(civWrap);
    check("a civilization slot is a closed list, not a text box",
          civCtl.tagName === "SELECT", String(civCtl.tagName));
    check("...and the list is the game's civilizations",
          (civCtl.children || []).length === 63,
          String((civCtl.children || []).length));
    fillShape("clone", { civ: "不列颠", donor: "村民", name: "铁匠学徒" });
    check("the creating form composes a creating sentence",
          text(ids.fpreview) === "不列颠照村民做一个新单位，叫铁匠学徒",
          text(ids.fpreview));

    // Switching shape must rebuild the controls, not keep the previous ones: a
    // leftover control writes a slot the new template does not have, and the
    // preview silently loses it.  Go back to the unit.stat intent first -- its
    // shapes are the pair a player is most likely to flip between.
    ids.fintent.value = "unit.stat";
    ids.fintent.onchange();
    ids.fshape.value = "delta";
    ids.fshape.onchange();
    check("switching shape rebuilds the controls instead of stacking them",
          (ids.fslots.children || []).length === 4
          && (ids.fslots.children || []).length === page.FORM_NODES().length,
          String((ids.fslots.children || []).length));
    const opWrap = page.FORM_NODES()[2];
    const opCtl = controlOf(opWrap);
    check("an op slot is a fixed list of the words the reader knows",
          opCtl.tagName === "SELECT"
          && (opCtl.children || []).map((o) => o.value).join("/") === "改成/加/减",
          String((opCtl.children || []).map((o) => o.value)));
    ids.say.value = "";
    return boxChecks();
  }).catch((e) => { fails.push("the form panel threw: " + e.message);
                    console.log("FAIL the form panel threw :: " + e.stack);
                    finish(); });
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
    return formChecks();
  }).catch((e) => { fails.push("the drag threw: " + e.message);
                    console.log("FAIL the drag threw :: " + e.stack); });
}

// ---- choosing which box a new unit goes on -------------------------------
// The clone inherits the donor's own training entry, and that entry can share a
// box with four other units, so "which box" is a real question with a finite
// answer.  The product already computes the free numbers; the page's only job is
// to offer exactly those -- and to offer NONE when there is no card at all,
// because a picker over a card that does not exist is the screen promising
// something the preview already refused.
function boxChecks() {
  const chips = () => walk(ids.preview, []).filter(
    (n) => n.tagName === "BUTTON" && n.className === "chip" &&
           /^第 \d+ 格$/.test(n.textContent || ""));
  PARSE_ANSWER = FIXTURES.newUnit;
  ids.say.value = "不列颠照村民做一个新单位，叫铁匠学徒，放在第5格";
  return page.doParse().then(() => {
    const got = chips();
    check("a new unit offers the boxes its card has free", got.length === 4,
          JSON.stringify(got.map((n) => n.textContent)));
    check("...and names the building whose card they are",
          text(ids.preview).indexOf("修道院") >= 0, text(ids.preview));
    // A plan can be buildable and still carry sentences the player needs before
    // pressing 生成: the icon is borrowed, a new technology will not appear in
    // the tech tree, the research box already holds two others.  `plan.warnings`
    // existed from the day these intents landed and the page printed none of
    // them -- measured 2026-10-23: `tech.create` produced four and the preview
    // showed zero.  Not a refusal, so the class must not be `.why`.
    check("a buildable plan's warnings reach the screen",
          text(ids.preview).indexOf("图标的号 0..999 已满") >= 0, text(ids.preview));
    check("...and are not styled as a refusal",
          walk(ids.preview, []).every(
            (n) => !(n.className === "why" &&
                     (n.textContent || "").indexOf("图标的号") >= 0)));
    // 14 is where the donor's own entry sits: five units already share it, so
    // offering it would be offering the collision the player is trying to leave.
    check("...and does not offer the box the donor already occupies",
          !got.some((n) => n.textContent === "第 14 格"),
          JSON.stringify(got.map((n) => n.textContent)));
    const seven = got.filter((n) => n.textContent === "第 7 格")[0];
    check("the box the player asked for is one of them",
          !!seven, JSON.stringify(got.map((n) => n.textContent)));
    if (seven) {
      ids.say.value = "不列颠照村民做一个新单位，叫铁匠学徒，放在第5格";
      seven.onclick();
      const said = ids.say.value;
      check("clicking a box rewrites the sentence, keeping the rest",
            said.indexOf("不列颠照村民做一个新单位，叫铁匠学徒") >= 0
            && said.indexOf("放在第7格") >= 0, said);
      // Two boxes in one sentence is the same class of bug as two numbers: the
      // reader takes the first match, so leaving the old one behind would make
      // the picker a no-op that looks like it worked.
      check("...and does not leave the previous box in the sentence",
            said.indexOf("第5格") < 0, said);
    }
    // No box typed yet: the choice still exists, so the picker must still be
    // there -- otherwise the only way to reach it is to guess the syntax.
    PARSE_ANSWER = FIXTURES.newUnitNoBox;
    ids.say.value = "不列颠照村民做一个新单位，叫铁匠学徒";
    return page.doParse();
  }).then(() => {
    check("a creating sentence without a box still offers the picker",
          chips().length === 4, JSON.stringify(chips().map((n) => n.textContent)));
    PARSE_ANSWER = FIXTURES.newUnitNoCard;
    ids.say.value = "不列颠照斯托尔特贝克做一个新单位，叫测试兵，放在第3格";
    return page.doParse();
  }).then(() => {
    check("a donor with no card gets no picker",
          chips().length === 0, JSON.stringify(chips().map((n) => n.textContent)));
    check("...and the screen says why there is no card",
          text(ids.preview).indexOf("建造位置没有指向任何建筑") >= 0,
          text(ids.preview));
    PARSE_ANSWER = FIXTURES.mixed;
    return Promise.resolve();
  }).catch((e) => { fails.push("the box picker threw: " + e.message);
                    console.log("FAIL the box picker threw :: " + e.stack); });
}

// ---- the update banner ---------------------------------------------------
// A mod we build ships a whole .dat, so a game patch is silently overwritten by
// the installed copy.  The screen has to say so -- and has to say nothing when
// the only rows it does not recognize are ones it could never know about.
// ---- the remove button ----------------------------------------------------
// Removing is the only action on this page that deletes folders, and the list is
// the only place a player can reach it.  Three ways it can be wrong without
// throwing: it fires on one click, it promises to take one row and takes two, or
// it swallows the game-running warning (the game rewrites mod-status.json on exit,
// so a delete made while it runs is undone -- measures, not a guess).
function removeChecks() {
  page.renderMods(MODS);
  const row = (ids.mods.children || []).filter((n) => n.className === "mod")[0];
  const rm = (row.children || []).filter((c) => c.className
    && c.className.indexOf("remove") === 0)[0];
  check("each row carries a remove button", !!rm,
        JSON.stringify((row.children || []).map((c) => c.className)));
  check("it does not delete anything on the first click",
        removed.length === 0, JSON.stringify(removed));
  const before = (ids.mods.children || []).length;
  RUNNING = true;
  return Promise.resolve(rm && rm.onclick ? rm.onclick() : null).then(() => {
    check("the first click only arms it", removed.length === 0,
          JSON.stringify(removed));
    // The label has to ask before it acts.  It used to read "确定删掉？"; since the
    // button recycles instead of deleting, the FACT being pinned is that a second
    // confirmation is demanded at all -- not the verb of the day.
    check("and the label asks before acting", text(rm).indexOf("确定") >= 0,
          text(rm));
    check("a split build says both halves go", text(rm).indexOf("两个") >= 0,
          text(rm));
    check("nothing was removed from the list yet",
          (ids.mods.children || []).length === before,
          String((ids.mods.children || []).length));
    return rm.onclick();
  }).then(() => {
    check("the second click removes the row it names", removed.length === 1
          && removed[0] === "dsh mine", JSON.stringify(removed));
    check("it re-renders from the answer rather than splicing locally",
          (ids.mods.children || []).length === before - 1,
          String((ids.mods.children || []).length));
    check("and repeats the warning about the running game",
          text(ids.toast).indexOf("游戏正开着") >= 0, text(ids.toast));
    RUNNING = false;
    MODS = MODS.concat([{ name: "dsh mine", title: "dsh 我的数据模组", enabled: true,
                          kind: "local", priority: 3, ships_dat: true, dat_rank: 1,
                          dat_competing: 1, role: "data",
                          paired_with: "dsh 我的数据模组（界面）" }]);
    return updateChecks();
  });
}

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
    return rosterChecks();
  }).catch((e) => { fails.push("the update banner threw: " + e.message);
                    console.log("FAIL the update banner threw :: " + e.stack);
                    finish(); });
}

// ---- the roster: which mods, before anything is parsed -------------------
// The check reads every installed .dat, which is 666 s for nineteen of them
// (measured 2026-11-10).  So the first press draws one chip per mod and parses
// nothing until 检查选中的 is pressed (m19827).  What can go wrong is not
// cosmetic: a chip list that cannot be emptied is a list that lies about what
// "clean" means, a 检查选中的 that stays pressable with nothing ticked starts a
// run over zero mods, and a scope that does not reach the request would check
// nineteen after the player ticked two -- which is the complaint in m19874.
function rosterChecks() {
  CANDIDATES = { ok: true, profile_root: "/tmp/p", count: 3, mods: [
    { name: "mod-a", title: "模组甲", enabled: true, kind: "subscribed", bytes: 12000000 },
    { name: "mod-b", title: "模组乙", enabled: false, kind: "local", bytes: 9000000 },
    { name: "mod-c", title: "模组丙", enabled: true, kind: "local", bytes: 4000000 },
  ] };
  const before = posted.length;
  return page.checkRepairs().then(() => {
    const box = ids.repair;
    const chips = walk(box, []).filter((n) => n.className.indexOf("chip") === 0);
    // 检查选中的 wears its count ("检查选中的 3 个"), so the actions are found by
    // prefix; the mod chips by title.
    const btnOn = (pre) => chips.filter((n) => text(n).indexOf(pre) === 0)[0] || null;
    const labelled = (lbl) => chips.filter((n) => text(n) === lbl)[0] || null;
    check("the first press draws a chip per mod instead of parsing them",
          chips.filter((n) => text(n).indexOf("模组") === 0).length === 3,
          JSON.stringify(chips.map((n) => text(n))));
    check("nothing was parsed yet",
          !posted.slice(before).some((p) => p.url.indexOf("/api/upgrade-check") === 0),
          JSON.stringify(posted.slice(before).map((p) => p.url)));
    // A button that cannot change anything is a broken button: the whole roster
    // starts ticked, so 全选 has nothing to do and 全不选 has everything to do.
    check("a fully ticked roster disables 全选 and offers 全不选",
          labelled("全选").disabled === true && labelled("全不选").disabled === false,
          JSON.stringify([labelled("全选").disabled, labelled("全不选").disabled]));
    labelled("全不选").onclick({ target: labelled("全不选") });
    const after = () => walk(box, []).filter((n) => n.className.indexOf("chip") === 0);
    check("全不选 clears every chip",
          after().filter((n) => n.className.split(/\s+/).indexOf("on") >= 0).length === 0,
          JSON.stringify(after().map((n) => n.className)));
    check("and then 检查选中的 refuses to run over nothing",
          btnOn("检查选中的").disabled === true,
          JSON.stringify(text(btnOn("检查选中的"))));
    check("while 全选 becomes the way back",
          labelled("全选").disabled === false && labelled("全不选").disabled === true,
          JSON.stringify([labelled("全选").disabled, labelled("全不选").disabled]));
    labelled("全选").onclick({ target: labelled("全选") });
    check("全选 ticks them all back",
          after().filter((n) => n.className.split(/\s+/).indexOf("on") >= 0).length === 3,
          JSON.stringify(after().map((n) => n.className)));
    // Untick one: the scope sentence and the request must both say "two".
    const third = after().filter((n) => text(n).indexOf("模组丙") === 0)[0];
    third.onclick({ target: third });
    check("unticking one names the new count on the button",
          text(btnOn("检查选中的")).indexOf("2 个") >= 0,
          JSON.stringify(text(btnOn("检查选中的"))));
    const mark = posted.length;
    const go = btnOn("检查选中的");
    return go.onclick({ target: go }).then(() => {
      const call = posted.slice(mark)
        .filter((p) => p.url.indexOf("/api/upgrade-check") === 0)[0];
      check("the request names exactly the ticked mods",
            !!call && call.url.indexOf("names=mod-a%2Cmod-b") >= 0,
            call ? call.url : JSON.stringify(posted.slice(mark).map((p) => p.url)));
      check("a run started from the roster does not ask for the roster again",
            !posted.slice(mark).some((p) => p.url.indexOf("/api/upgrade-candidates") === 0),
            JSON.stringify(posted.slice(mark).map((p) => p.url)));
      CANDIDATES = null;
      return repairChecks();
    });
  }).catch((e) => { fails.push("the roster threw: " + e.message);
                    console.log("FAIL the roster threw :: " + e.stack);
                    CANDIDATES = null;
                    finish(); });
}

// ---- saving a community mod that ships its own .dat ----------------------
// Three things can go wrong here and only one of them is cosmetic: offering the
// button on a mod that cannot be fixed, saying "fixed" without re-checking, and
// dropping the game-running warning on the repair path (a repair reinstalls, so
// it rewrites mod-status.json exactly like install does).  The last one is the
// same defect that made "重建并重装" look safe, one level down.
function repairChecks() {
  return page.checkRepairs().then(() => {
    const box = ids.repair;
    const flat = text(box);
    // The count comes first: twenty rows with no "2 of them can be carried
    // forward here" makes the player read all twenty to find out.
    check("the upgrade box says how many it can carry forward",
          flat.indexOf("模组 4 个") >= 0
            && flat.indexOf("可以更新 2 个") >= 0, flat);
    // The archive line is the reason the tool can answer at all: without it the
    // only thing it could say is "this file differs from the shipped one".
    check("and says where the baseline came from",
          flat.indexOf("官方这一版的数据已经存档") >= 0
            && flat.indexOf("档案里共 12 份") >= 0, flat);
    // `conflicts` is actionable too -- one click "keep mine" -- so two buttons,
    // not one.  A page that only offered it on `mergeable` would silently drop
    // the mods the official patch happened to touch.
    check("both actionable rows offer the button",
          walk(box, []).filter((n) => n.className === "chip"
            && text(n) === "更新").length === 2,
          JSON.stringify(walk(box, []).map((n) => text(n)).slice(0, 14)));
    // A cross-generation mod cannot be carried forward, and an attempt would
    // produce a mod that silently is not the author's.  No button on that row.
    check("a row that cannot be carried forward offers no button",
          walk(box, []).filter((n) => text(n).indexOf("10 倍资源文明联盟3倍科技") >= 0
            && n.children.some((c) => text(c) === "更新")).length === 0,
          flat);
    check("the verdict is printed in Chinese, not as the file's spelling",
          flat.indexOf("可以更新") >= 0 && flat.indexOf("这一版搬不过去") >= 0
            && flat.indexOf("impossible") < 0 && flat.indexOf("mergeable") < 0,
          flat);
    // The engine writes `summary` as the panel's OWN lines (判定 / 要搬的改动 /
    // … / 耗时), so a page that prints the block verbatim repeats the badge and
    // the count row above it -- and on a refusal, repeats the one sentence that
    // lives in `summary` AND `notes[0]`.  Both are counted here because both
    // looked fine in a screenshot: the old panel drew them on top of each other
    // inside a 30px row, so "the text is there" was true and unreadable.
    const times = (hay, needle) => hay.split(needle).length - 1;
    check("the engine's 判定 line is not printed under the badge that says it",
          flat.indexOf("判定：") < 0, flat);
    check("the engine's 要搬 line is not printed under the count row",
          flat.indexOf("要搬的改动：") < 0, flat);
    check("耗时 is moved onto the count row, once per row",
          times(flat, "耗时：") === 4, JSON.stringify(times(flat, "耗时：")));
    check("a refusal that is in both summary and notes is printed once",
          times(flat, "档案库里还没有 VER 7.8 这一代的官方数据。") === 1,
          JSON.stringify(times(flat, "档案库里还没有 VER 7.8 这一代的官方数据。")));
    // Colour is the only thing that separates nineteen rows at a glance, and
    // the page used to put the same green pill on every verdict: `.stat` with
    // a `.dim` that only exists for `.detailtext`, so a mod that cannot be
    // carried forward looked exactly like one the button fixes.
    const badgesOf = (v) => walk(box, []).filter((n) => n.className
      && n.className.indexOf("stat") === 0
      && text(n) === (page.UPGRADE_VERDICT_ZH[v] || v));
    check("a fixable verdict wears the plain success pill",
          badgesOf("mergeable").every((n) => n.className === "stat"),
          JSON.stringify(badgesOf("mergeable").map((n) => n.className)));
    check("a verdict the official patch touched is not drawn as a clean pass",
          badgesOf("conflicts").every((n) => n.className === "stat warn"),
          JSON.stringify(badgesOf("conflicts").map((n) => n.className)));
    check("a row this tool cannot carry forward is drawn as a refusal",
          badgesOf("impossible").every((n) => n.className === "stat bad"),
          JSON.stringify(badgesOf("impossible").map((n) => n.className)));
    check("a row with nothing to do is drawn quietly, not as a pass",
          badgesOf("up_to_date").every((n) => n.className === "stat plain"),
          JSON.stringify(badgesOf("up_to_date").map((n) => n.className)));
    // 「有 57 处」 is a count of RECORDS, and the game keeps one record per
    // civilization: the measured mod had 57 of them for 4 decisions.  The row
    // therefore has to say how many DECISIONS there are, and the fold has to
    // open into one line each.  Both halves are checked, because a label that
    // says 2 while the list prints 54 lines is the defect this list exists for.
    const conflictBox = walk(box, []).filter((n) => n.className === "conflict")[0];
    const foldBtn = walk(box, []).filter((n) => n.className === "chip fold")[0];
    check("a conflicts row offers a fold naming how many decisions there are",
          !!foldBtn && text(foldBtn).indexOf("2") >= 0,
          JSON.stringify(foldBtn ? text(foldBtn) : walk(box, []).map((n) => text(n)).slice(0, 12)));
    check("and the fold starts closed",
          !!conflictBox && conflictBox.hidden === true,
          JSON.stringify(conflictBox ? conflictBox.hidden : "no .conflict"));
    check("the count line says records AND fields, not just records",
          flat.indexOf("冲突 57 处（2 个字段）") >= 0, flat);
    if (foldBtn) foldBtn.onclick({ target: foldBtn });
    check("opening it lists the field, both values and who they belong to",
          !!conflictBox && conflictBox.hidden === false
            && text(conflictBox).indexOf("显示攻击力") >= 0
            && text(conflictBox).indexOf("官方 5") >= 0
            && text(conflictBox).indexOf("你的 4") >= 0,
          conflictBox ? text(conflictBox) : "no .conflict");
    check("one line per decision, not one per civilization",
          !!conflictBox && conflictBox.children.filter((n) => n.className === "cf").length === 2,
          conflictBox ? JSON.stringify(conflictBox.children.map((n) => n.className)) : "");
    // A group spanning civilizations must say how many: a line reading just
    // 「不列颠」 would look like one civilization was affected.
    check("a group spanning civilizations says how many",
          !!conflictBox && text(conflictBox).indexOf("54 个文明") >= 0,
          conflictBox ? text(conflictBox) : "");
    if (foldBtn) foldBtn.onclick({ target: foldBtn });
    check("and closing it folds the lines away again",
          !!conflictBox && conflictBox.hidden === true,
          JSON.stringify(conflictBox ? conflictBox.hidden : "no .conflict"));
    const btn = walk(box, []).find((n) => n.className === "chip"
      && text(n) === "更新");
    RUNNING = true;
    const mark = posted.length;
    return btn ? btn.onclick({ target: btn }).then(() => mark) : null;
  }).then((mark) => {
    // The re-ask after a row upgrade is about THAT mod.  It used to pass no
    // names, which the route reads as "every candidate" -- so pressing one row's
    // button set the tool reading all nineteen .dat files again (m19874:
    // "工具自己去把别的检查了").  The URL is the proof, not the row text.
    const again = posted.slice(mark)
      .filter((p) => p.url.indexOf("/api/upgrade-check") === 0);
    check("re-asking after one row asks about that one mod",
          again.length === 1 && again[0].url.indexOf("names=") >= 0
            && again[0].url.indexOf("dsh%20test%20v46") >= 0,
          JSON.stringify(again.map((p) => p.url)));
    check("the upgrade posts the installed mod's own folder name",
          repairedNow.length === 1 && repairedNow[0] === "dsh test v46",
          JSON.stringify(repairedNow));
    check("a upgrade says the game is open too",
          text(ids.toast).indexOf("游戏正开着") >= 0, text(ids.toast));
    // Re-asked, not assumed: the row has to read as DONE afterwards.
    // Asserting the toast would pass even if the merge produced a different
    // .dat -- the toast is a claim about the request, the row is a claim about
    // the answer.
    //
    // And the wording is not 「本来就是新版」: that sentence belongs to a mod
    // that was built on this data long ago.  A row whose file exists BECAUSE
    // the player just pressed 更新 has to say so, or the button press leaves no
    // trace on the screen and reads as "it did nothing" (reported 2026-11-21).
    // The engine marks the difference (`upgraded`, from the build record) and
    // the fixture carries it, so what is checked here is the page using it.
    check("the row reads as completed after the upgrade",
          text(ids.repair).indexOf("已完成更新") >= 0, text(ids.repair));
    // The count row legitimately prints 「本来就是新版 0 个」, so the claim to
    // forbid is a BADGE saying it, not the string anywhere on the panel.
    check("and no badge claims the mod was always current",
          walk(ids.repair, []).filter((n) => n.className === "stat plain"
            && text(n) === "本来就是新版").length === 0,
          JSON.stringify(walk(ids.repair, [])
            .filter((n) => n.className === "stat plain")
            .map((n) => text(n))));
    check("and no button is left on it",
          walk(ids.repair, []).filter((n) => n.className === "chip"
            && text(n) === "更新").length === 0, text(ids.repair));
    RUNNING = false;
    return adaptAllChecks();
  }).catch((e) => { fails.push("the repair box threw: " + e.message);
                    console.log("FAIL the repair box threw :: " + e.stack);
                    finish(); });
}

// ---- the batch button -----------------------------------------------------
// Nineteen rows each needing one press is not the "one-click update" the panel
// promises, so there is a second button that walks the same route.  Three
// things about it can go wrong without anything else on this screen noticing:
//   (1) it is offered when nothing is actionable, which teaches the player to
//       ignore it;
//   (2) it stops at the first mod that throws, so a batch of nineteen is a
//       batch of however many came first;
//   (3) it flips `official_wins` and carries the official value over the
//       author's edit -- the exact outcome the row button asks a question
//       about, silently applied to every row at once.
// The body of each POST is recorded for (3): names alone would still look
// right with the flag inverted.
function adaptAllChecks() {
  // repairChecks() clicked a row button, and the apply stub rewrites the
  // fixture in place; start from the pristine copy so this run sees two
  // actionable rows, as a screen with nineteen mods does.
  // Assigned here, in the harness scope, because that is where the stub reads
  // it: an assignment made from inside the page creates a page-scope variable
  // and leaves the stub answering from the spent fixture.
  UPGRADE_ANSWER = JSON.parse(JSON.stringify(UPGRADE_PRISTINE));
  repairedNow.length = 0;
  appliedBodies.length = 0;
  ids.toast.textContent = "";
  let mark = posted.length;
  return page.checkRepairs().then(() => {
    mark = posted.length;
    const all = ids["btn-repair-all"];
    check("the batch button appears when something can be batched",
          all && !all.classList.contains("hide"),
          all ? all.className : "no #btn-repair-all");
    // Not cosmetic: `repairChecks()` counts the row buttons by their exact
    // wording, so a batch button sharing it would be counted as a third
    // row button and the screen would offer the same action twice.
    check("and it does not wear the row button's wording",
          all && text(all) !== "更新",
          all ? JSON.stringify(text(all)) : "");
    // The queue is the answer the rows were drawn from, not a second query:
    // two sources for "what needs work" is how a batch and a list disagree.
    check("the queue is exactly the actionable rows, in screen order",
          JSON.stringify(page.TODO().map((r) => r.name))
            === JSON.stringify(["dsh test v46", "167396_Red Alert 2 MOD"]),
          JSON.stringify(page.TODO().map((r) => r.name)));
    return page.adaptAll().then(() => mark);
  }).then((mark) => {
    // The re-ask after a batch is about the mods the BATCH rebuilt.  It used to
    // pass no names -- "every candidate" -- so adapting two mods quietly set the
    // tool reading all nineteen .dat files, which is what m19874 saw as the tool
    // checking things nobody asked about.
    const again = posted.slice(mark)
      .filter((p) => p.url.indexOf("/api/upgrade-check") === 0);
    check("re-asking after a batch names the mods the batch rebuilt",
          again.length === 1 && again[0].url.indexOf("names=") >= 0
            && again[0].url.indexOf("Red%20Alert") >= 0
            && again[0].url.indexOf("dsh%20test%20v46") >= 0,
          JSON.stringify(again.map((p) => p.url)));
    // Both, not the first one: a batch that stopped at a throwing mod is the
    // failure this button exists to avoid, and it looks identical here unless
    // the names are counted.
    check("the batch carries every actionable mod, not just the first",
          repairedNow.length === 2
            && repairedNow[0] === "dsh test v46"
            && repairedNow[1] === "167396_Red Alert 2 MOD",
          JSON.stringify(repairedNow));
    check("each press keeps the author's edit (official_wins false)",
          appliedBodies.length === 2
            && appliedBodies.every((b) => b.official_wins === false
                                 && b.install === true),
          JSON.stringify(appliedBodies));
    // Said out loud, because the player did not answer the conflict question
    // for these rows: they answered it for one, or for none.
    check("the batch says which mods the official patch also touched",
          text(ids.repair).indexOf("Red Alert 2") >= 0
            && text(ids.repair).indexOf("按作者的改法") >= 0,
          text(ids.repair));
    // One toast, and it must be the summary -- `toast()` overwrites, so four
    // calls in a row would leave the failure list on screen for four seconds
    // and then nothing.
    check("the batch reports its result in one toast",
          text(ids.toast).indexOf("2 个") >= 0
            && (text(ids.toast).match(/已更新/g) || []).length === 1,
          JSON.stringify(text(ids.toast)));
    // Re-asked, not assumed: the stub answers the second query with one
    // already-current row, so the button must have withdrawn itself.
    check("the button withdraws once the work is done",
          ids["btn-repair-all"].classList.contains("hide"),
          ids["btn-repair-all"].className);
    check("and the rows were re-read from the route, not assumed",
          text(ids.repair).indexOf("已完成更新") >= 0,
          text(ids.repair));
    // The count line has to separate the two kinds of "nothing to do" too, or
    // the row says 已完成更新 under a summary that counted it as 本来就是新版.
    check("the summary counts completed updates apart from always-current mods",
          text(ids.repair).indexOf("已完成更新 1 个") >= 0,
          text(ids.repair));
    return intentListChecks();
  }).catch((e) => { fails.push("the batch button threw: " + e.message);
                    console.log("FAIL the batch button threw :: " + e.stack);
                    finish(); });
}

// ---- the screen's own wording ---------------------------------------------
// Two failures this pins, and neither is cosmetic:
//   (1) `applyLocale()` that writes the KEY when the table lacks an entry turns
//       every heading into `say.heading` -- and a page whose text is keys is
//       still "rendering", so nothing else here would notice.
//   (2) A string that still holds `{version}` must not be written: the number
//       lives in code that knows it, and pasting the raw template would put
//       `{civs} 个文明` in front of a player.
// The harness has no HTML body, so the tagged nodes are built here the same way
// the file declares them -- `document.createElement` + `data-i18n`.
function taggedNode(tag, key, text, attr) {
  const n = sandbox.document.createElement(tag);
  n.setAttribute(attr || "data-i18n", key);
  n.textContent = text;
  ids.preview.appendChild(n);
  return n;
}

function localeChecks() {
  // A failed fetch must leave the inline Chinese alone: the page cannot reach
  // the table at all here, and blank headings would be worse than stale ones.
  LOCALE_FAIL = true;
  STR_BEFORE = Object.keys(page.STR()).length;
  return page.loadLocale().then(() => {
    const h = taggedNode("h2", "say.heading", "你想要什么改动？用中文说就行");
    page.applyLocale();
    check("a failed locale fetch leaves the inline wording alone",
          h.textContent === "你想要什么改动？用中文说就行",
          JSON.stringify(h.textContent));
    check("...and the page knows it has no table",
          Object.keys(page.STR()).length === 0,
          JSON.stringify(Object.keys(page.STR()).length));
    LOCALE_FAIL = false;
    return page.loadLocale();
  }).then(() => {
    page.applyLocale();
    const h = taggedNode("h2", "say.heading", "旧的一句话");
    const ph = taggedNode("input", "pick.search", "", "data-i18n-ph");
    ph.setAttribute("placeholder", "旧提示");
    const templ = taggedNode("span", "page.version", "游戏版本 54");
    page.applyLocale();
    check("the table's wording replaces the inline copy",
          h.textContent === "你想要什么改动？用中文说就行",
          JSON.stringify(h.textContent));
    check("a placeholder is replaced too",
          ph.getAttribute("placeholder") === "在这个列表里找…",
          JSON.stringify(ph.getAttribute("placeholder")));
    check("a string with a placeholder is left to the code that fills it",
          templ.textContent === "游戏版本 54",
          JSON.stringify(templ.textContent));
    const ghost = taggedNode("h2", "no.such.key", "原样留着");
    page.applyLocale();
    check("a key the table lacks shows its inline text, not the key",
          ghost.textContent === "原样留着",
          JSON.stringify(ghost.textContent));
    check("the page fetched its wording from the route",
          posted.some((p) => p.url.indexOf("/api/locale") === 0),
          JSON.stringify(posted.map((p) => p.url).slice(-3)));
    return Promise.resolve();
  });
}


// ---- 检查更新：问的是这一份工具自己 ------------------------------------
// 和上面的 update banner 是两条不同的消息，所以分两次检查。 banner 说的是
// 「游戏的 .dat 在你装模组之后被游戏改过，模组要重建」；这条说的是「远端仓库
// 里这一份工具有没有新版」。两条混成一条，玩家会在数据没变的时候被叫去下载
// 一个不存在的升级包，或者在新版出来的时候什么都没看到。
function versionChecks() {
  // boot 已经静默问过一次（设置里没关的话），那一次必须是 force=0：启动时强制
  // 刷缓存会让「六小时缓存」形同不存在。
  check("boot asks once, without forcing",
        versionAsked.length >= 1 && versionAsked[0].indexOf("force=0") >= 0,
        JSON.stringify(versionAsked));
  // behind 是唯一会让人去下载的状态，所以它必须点名远端版本号，并且说去哪儿。
  VERSION_ANSWER = VERSIONS.behind;
  return page.versionCheck(true).then(() => {
    check("the button asks again, and forces the cache",
          versionAsked[versionAsked.length - 1].indexOf("force=1") >= 0,
          JSON.stringify(versionAsked.slice(-2)));
    const line = text(ids["about-update"]);
    check("a newer remote version is named on the line",
          line.indexOf("1.1") >= 0, line);
    // 说法从「去 GitHub 下载覆盖」改成「按那个按钮，它自己换」：玩家要的是
    // 一键装好，不是被指去网页上手动替换一个正在运行的程序。
    check("...and names the button that installs it",
          line.indexOf("下载并装好") >= 0, line);
    check("...and that button is on the card",
          ids["about-install"].hidden === false, String(ids["about-install"].hidden));
    // 号码只说明有东西变了：286 MB 要不要下是另一回事。 所以「有新版」时必须
    // 把新版自己写的改动列出来，而且列的是远端的，不是这一份的。
    const remoteBox = text(ids["about-remote"]);
    check("...and lists what the new version changed",
          remoteBox.indexOf("远端说这一版多了什么") >= 0, remoteBox);
    check("...without borrowing the lines this copy wrote about itself",
          remoteBox.indexOf("这一份自己写了什么") < 0, remoteBox);
    // same：已经最新时说一句就行，不要留一个「去下载」的按钮引导。
    VERSION_ANSWER = VERSIONS.same;
    return page.versionCheck(false);
  }).then(() => {
    const line = text(ids["about-update"]);
    check("an up-to-date copy says so", line.indexOf("最新") >= 0, line);
    // 没有新版时那颗按钮必须收起来：留着它等于在最新的一份上写着「可以装」。
    check("...and the install button goes away",
          ids["about-install"].hidden === true,
          String(ids["about-install"].hidden));
    // 上一次按出来的「新版改了什么」不能留在这一次「已经是最新的」下面：屏幕
    // 同时说两件事，玩家会以为那个新版他还没装。
    check("...and the previous answer's change list is taken back",
          text(ids["about-remote"]).indexOf("远端说这一版多了什么") < 0,
          text(ids["about-remote"]));
    // 按「下载并装好」之后：服务端起了一个 job 槽，条子跟着它走；槽里报
    // running:false 才算装好，error 有字就必须原样说出来。 这里一拍一拍地
    // 驱动 installTick，而不是让页面自己连问 —— 测试里没有真的时钟。
    JOB_ANSWER = { key: "update", label: "正在下载新版", percent: 37, done: 37,
                   total: 100, elapsed: 1, running: true, error: null,
                   known: true, seq: 1 };
    return page.installUpdate();
  }).then(() => {
    check("the install button asks the server to start",
          installAsked.length === 1, JSON.stringify(installAsked));
    check("...and the bar shows the bytes the server has walked",
          text(ids["about-install-bar"]).indexOf("37%") >= 0,
          text(ids["about-install-bar"]));
    JOB_ANSWER = { key: "update", label: "正在重启以装好", percent: 100,
                   done: 100, total: 100, elapsed: 9, running: false,
                   error: null, known: true, seq: 1 };
    return page.installTick();
  }).then((next) => {
    check("...and a finished job says the new version is being opened",
          next === "done"
          && text(ids["about-install-bar"]).indexOf("重新打开") >= 0,
          next + " :: " + text(ids["about-install-bar"]));
    JOB_ANSWER = { key: "update", label: "正在下载新版", percent: 12, done: 12,
                   total: 100, elapsed: 2, running: true, error: null,
                   known: true, seq: 2 };
    return page.installUpdate();
  }).then(() => {
    JOB_ANSWER = { key: "update", label: "正在下载新版", percent: 12, done: 12,
                   total: 100, elapsed: 2, running: false,
                   error: "下下来的包和发布页公布的不一样，没有装", known: true,
                   seq: 2 };
    return page.installTick();
  }).then((next) => {
    check("...and a failed download repeats the reason the server gave",
          next === "fail" && text(ids["toast"]).indexOf("公布的不一样") >= 0,
          next + " :: " + text(ids["toast"]));
    check("...and a failure puts the bar away instead of leaving it at 100%",
          ids["about-install-bar"].hidden === true,
          String(ids["about-install-bar"].hidden));
    // 从源码目录跑的那一份：服务端在答案里带 can_update:false。
    VERSION_ANSWER = Object.assign({}, VERSIONS.behind, { can_update: false });
    return page.versionCheck(true);
  }).then(() => {
    check("a source checkout cannot replace itself, and says why",
          ids["about-install"].disabled === true
          && String(ids["about-install"].title).indexOf("源码") >= 0,
          String(ids["about-install"].title));
    VERSION_ANSWER = VERSIONS.offline;
    return page.versionCheck(true);
  }).then(() => {
    // offline：连不上就直说不知道，不能静默留白，也不能说成最新。
    const line = text(ids["about-update"]);
    // 「不知道」这一条不能点名版本号，也不能说成已经最新 —— 文案里允许出现
    // 「是不是最新就不知道了」这种否认句，所以判据是「没有点名 1.1」。
    check("an unreachable repository says it does not know",
          line.indexOf("连不上") >= 0 && line.indexOf("1.1") < 0, line);
    // 按钮在自己问完之后必须是能按的：一个转圈转到永远的按钮比错误更糟。
    check("the button is usable again after the answer",
          ids["about-check"].disabled === false
          || ids["about-check"].disabled === undefined,
          String(ids["about-check"].disabled));
    // 更新日志：打开关于页时拉一次，把 GitHub 上每一版都列出来。 只印手上这一
    // 份的改动，回答不了「上一版改了什么」，而那正是点开版本卡想问的事。
    return page.loadChangelog();
  }).then(() => {
    check("opening the version card fetches the whole log, not just this copy",
          changelogAsked.length >= 1, JSON.stringify(changelogAsked));
    const logBox = text(ids["about-changelog-list"]);
    check("...and every release in it is on screen",
          logBox.indexOf("1.0004") >= 0 && logBox.indexOf("1.0003") >= 0
          && logBox.indexOf("1.0002") >= 0, logBox);
    check("...newest first",
          logBox.indexOf("1.0004") < logBox.indexOf("1.0003")
          && logBox.indexOf("1.0003") < logBox.indexOf("1.0002"), logBox);
    check("...with the date beside the number",
          logBox.indexOf("2026-11-17") >= 0, logBox);
    check("...and each line says what changed, not how",
          logBox.indexOf("下载新版的网络慢，现在快多了") >= 0, logBox);
    // 连不上时不能留白：手上这一份自己写了什么，是唯一不需要网络的答案。
    CHANGELOG_ANSWER = { ok: true, reachable: false, cached: false,
                         rows: [{ version: "1.0004", date: "",
                                  notes: ["这一份自己写了什么"], url: "" }] };
    return page.loadChangelog(true);
  }).then(() => {
    const logBox = text(ids["about-changelog-list"]);
    check("an unreachable log falls back to what this copy says about itself",
          logBox.indexOf("这一份自己写了什么") >= 0, logBox);
    check("...instead of leaving the previous release list behind",
          logBox.indexOf("1.0003") < 0, logBox);
    return recipeChecks();
  }).catch((e) => { fails.push("the version check threw: " + e.message);
                    console.log("FAIL the version check threw :: " + e.stack);
                    finish(); });
}

// ---- the 能做的事 list ---------------------------------------------------
// A plugin adds intents to the schema and this box lists the schema, but the
// sentence layer is hand-written: a plugin intent is reachable only through the
// API.  Measured 2026-10-23: a plugin intent `unit.set_stat` was listed as if a
// sentence could ask for it, while `把村民血量设成40` still parsed to `unit.stat`.
function intentListChecks() {
  return page.boot().then(() => {
    const rows = walk(ids.intents, []);
    const flat = text(ids.intents);
    // One card per intent.  Pinned on the card class rather than on "the class
    // is empty": the row became a card on 2026-10-26, and an assertion that the
    // class is "" would have kept passing while the CSS had nothing to hook.
    check("the capability list renders one row per intent",
          rows.filter((n) => String(n.className).indexOf("intentcard") >= 0
                             && n.children.length >= 1).length >= 2,
          flat);
    check("an intent a sentence can reach is listed plainly",
          flat.indexOf("改数值") >= 0,
          flat);
    // The tag belongs to the plugin row, not to the whole box: asserting "the box
    // does not contain the phrase" would be satisfied by a page that printed the
    // tag on BOTH rows, which is the mistake this guards against.  Read the row
    // with `text()` (it walks children); `textContent` only holds the row's own
    // direct string in this stub, so it would miss the appended span.
    const _rows = (ids.intents.children || []);
    const _plain = _rows.filter((n) => text(n).indexOf("改数值") >= 0);
    const _api = _rows.filter((n) => text(n).indexOf("插件示例") >= 0);
    check("the sentence-reachable row carries no caveat",
          _plain.length === 1 && text(_plain[0]).indexOf("只能用接口") < 0,
          _plain.length ? text(_plain[0]) : "row missing");
    check("one that only the API can reach says so",
          _api.length === 1
          && text(_api[0]).indexOf("只能用接口（句子还认不出来）") >= 0,
          _api.length ? text(_api[0]) : "row missing");
    check("...and it is still listed, not hidden",
          flat.indexOf("把一项属性设成某个值") >= 0, flat);
    check("...with a tooltip that names the API",
          String((ids.intents.children || []).map((n) => n.title).join(" "))
            .indexOf("/api/plan") >= 0,
          JSON.stringify(walk(ids.intents, []).map((n) => n.title)));
    return localeChecks().then(() => versionChecks());
  }).catch((e) => { fails.push("the capability list threw: " + e.message);
                    console.log("FAIL the capability list threw :: " + e.stack);
                    finish(); });
}

// ---- the saved sentences --------------------------------------------------
// Three ways this panel can lie, and each of them looks like success:
//   (1) save failing and the list still drawing the row, so the player believes
//       a name exists that will be gone after a restart;
//   (2) "use this recipe" APPENDING to the box, so the reader sees five sentences
//       when three were meant -- and the extra two are whatever was there before;
//   (3) an empty box or an empty name being saved anyway, which produces a name
//       that rebuilds nothing.
function recipeChecks() {
  RECIPE_ANSWER = RECIPES;
  return page.loadRecipes().then(() => {
    const names = listNames();
    check("every stored name is drawn",
          names.length === 2 && names.indexOf("我的伐木场") >= 0
          && names.indexOf("旧的写法") >= 0, JSON.stringify(names));
    const flat = text(ids.rlist);
    check("the list shows the sentences, not just the name",
          flat.indexOf("村民血量改成1000") >= 0, flat);
    // A sentence the reader would refuse is still shown: the list reports what is
    // in the file.  Hiding it would make the panel tidier and dishonest.
    check("a sentence the reader would refuse is still listed",
          flat.indexOf("把村民血量变成很多") >= 0, flat);

    // (2) loading REPLACES the box.
    ids.say.value = "先写一句占位";
    const rows = walk(ids.rlist, []).filter((n) => text(n) === "用这几句");
    return Promise.resolve(rows[0].onclick()).then(() => {
      check("using a recipe replaces the box instead of stacking on it",
            ids.say.value === "波兰的伐木场木材成本减少 10\n村民血量改成1000",
            JSON.stringify(ids.say.value));

      // (1) a bad save must not enter the list.
      el("rname").value = "";
      const before = listNames().length;
      return Promise.resolve(ids.rsave.onclick()).then(() => {
        check("saving without a name does not add a row",
              listNames().length === before, JSON.stringify(listNames()));

        // (3) an empty box must not be saved under a name either.
        el("rname").value = "空的";
        ids.say.value = "";
        return Promise.resolve(ids.rsave.onclick()).then(() => {
          check("an empty box is not saved under a name",
                listNames().indexOf("空的") < 0, JSON.stringify(listNames()));
          check("and neither attempt reached the route",
                savedNow.filter((b) => !b.name || !b.sentences.length).length === 0,
                JSON.stringify(savedNow));

          // A real save does reach the route and the list is re-read after it.
          el("rname").value = "新的名字";
          ids.say.value = "村民血量改成1000";
          return Promise.resolve(ids.rsave.onclick()).then(() => {
            check("a real save posts the name and the sentences",
                  savedNow.some((b) => b.name === "新的名字"
                    && b.sentences.length === 1), JSON.stringify(savedNow));
            check("...and the list is re-read rather than patched in place",
                  listNames().indexOf("新的名字") >= 0, JSON.stringify(listNames()));

            // Deleting goes through the route and the row disappears.
            const del = walk(ids.rlist, []).filter((n) => text(n) === "删掉");
            return Promise.resolve(del[0].onclick()).then(() => {
              check("deleting a name removes its row",
                    listNames().indexOf("我的伐木场") < 0,
                    JSON.stringify(listNames()));
              check("...by asking the route, not by editing the list",
                    forgotten.indexOf("我的伐木场") >= 0,
                    JSON.stringify(forgotten));
              return Promise.resolve();
            });
          });
        });
      });
    });
  }).then(() => aiChecks())
    .catch((e) => { fails.push("the recipe panel threw: " + e.message);
                    console.log("FAIL the recipe panel threw :: " + e.stack);
                    finish(); });
}

function listNames() {
  return walk(ids.rlist, [])
    .filter((n) => n.className === "rname")
    .map((n) => n.textContent);
}

// `ids` only holds nodes the page itself asked for by id.  The recipe box is
// reached the same way, so ask the document rather than reading a key that may
// not exist yet (that was the `Cannot set properties of undefined` above).
function el(key) {
  return document.querySelector("#" + key);
}

// ---- the AI entry ---------------------------------------------------------
// Two things can go wrong and neither is cosmetic.  (1) A page that draws the
// button when the endpoint is not configured sends the player into a box that
// can only fail.  (2) A page that applies the model's answer directly would put
// a guess straight into bytes -- so the only thing this entry may do is replace
// the text and re-run the ordinary reader, which is what the second half pins.
function aiChecks() {
  AI_ANSWER = AI_OFF;
  return page.aiBoot().then(() => {
    check("no endpoint configured means no button",
          ids["btn-ai"].classList.contains("hide"),
          ids["btn-ai"].className);
    AI_ANSWER = AI_ON;
    return page.aiBoot();
  }).then(() => {
    check("a configured endpoint draws the button",
          !ids["btn-ai"].classList.contains("hide"),
          ids["btn-ai"].className);
    check("and the button names the model it will call",
          String(ids["btn-ai"].title).indexOf("some-model") >= 0,
          ids["btn-ai"].title);
    ids.say.value = "让村民更耐打一点";
    return page.doAI();
  }).then(() => {
    check("the wish is what gets sent",
          aiAsked.length === 1 && aiAsked[0] === "让村民更耐打一点",
          JSON.stringify(aiAsked));
    const rows = walk(ids.aigot, []);
    check("every sentence comes back as its own row",
          rows.filter((n) => n.className === "mod").length === 2,
          JSON.stringify(rows.map((n) => text(n)).slice(0, 6)));
    check("the model's sentence is offered, not applied",
          text(ids.say).indexOf("村民血量改成 1000") < 0,
          text(ids.say));
    const use = rows.find((n) => n.className === "chip"
      && text(n) === "用这句");
    check("each row carries a button that replaces the box",
          !!use, JSON.stringify(rows.map((n) => text(n)).slice(0, 6)));
    return use ? use.onclick({ target: use }) : null;
  }).then(() => {
    // Replaced, not appended: the wish the player typed is on its way out, and
    // keeping both would leave two versions of one request in a single box.
    check("using a sentence replaces the box instead of stacking requests",
          String(ids.say.value).indexOf("村民血量改成 1000") >= 0
          && String(ids.say.value).indexOf("让村民更耐打一点") < 0,
          ids.say.value);
    // And the click re-runs the ORDINARY reader, so a refusal is still a refusal.
    check("...and it goes back through the same reader",
          posted.filter((p) => p.url.indexOf("/api/parse") === 0).length >= 1,
          JSON.stringify(posted.map((p) => p.url).slice(-4)));
    finish();
  }).catch((e) => { fails.push("the AI entry threw: " + e.message);
                    console.log("FAIL the AI entry threw :: " + e.stack);
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
