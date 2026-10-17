// Mine the scan for the things this project actually keeps needing.
//
// The scan answered "what installs here"; this answers "which of those matches
// a problem we have hit".  Grouping by need keeps the output short enough to
// act on -- a 713-row list is a directory, not a recommendation.
import { readFileSync } from 'node:fs';

const SCAN = 'D:/Software/DeepSeek Harness/工作区2/_probe/plugin_scan.json';
const scan = JSON.parse(readFileSync(SCAN, 'utf8'));
const rows = scan.compatible;

// Problem -> evidence pattern.  Every pattern is a need this session actually
// had at some point, not a category of software.
const NEEDS = {
  'watch/screenshot a Windows app (sprite + UI verification)': [
    /screenshot/i, /screen-?shot/i, /window/i, /capture/i, /desktop/i,
    /snipping/i, /ocr/i, /image/i, /vision/i, /photo/i, /picture/i, /sprite/i,
  ],
  'run/supervise long test suites and get told when they finish': [
    /notif/i, /notify/i, /alert/i, /continue/i, /resume/i, /cron/i,
    /schedul/i, /task/i, /monitor/i, /automation/i, /background/i,
  ],
  'search the web for format documentation': [
    /search/i, /research/i, /browse/i, /reader/i, /fetch/i, /deep-?read/i,
  ],
  'render + edit images programmatically': [
    /image/i, /vision/i, /ocr/i, /sprite/i, /pixel/i, /canvas/i, /draw/i,
    /diff/i, /compare/i,
  ],
  'keep the skill library honest': [
    /skill/i, /prompt/i, /memory/i, /context/i, /knowledge/i,
  ],
  'read and diff what changed on disk': [
    /git/i, /diff/i, /review/i, /file/i, /explorer/i, /search/i, /ripgrep/i,
  ],
};

const hit = new Map();
for (const r of rows) {
  const hay = `${r.npm} ${r.name} ${r.zh} ${r.en} ${r.category}`;
  for (const [need, pats] of Object.entries(NEEDS)) {
    if (!pats.some(p => p.test(hay))) continue;
    if (!hit.has(need)) hit.set(need, []);
    hit.get(need).push(r);
  }
}

for (const [need, list] of hit) {
  list.sort((a, b) => (b.downloads ?? 0) - (a.downloads ?? 0));
  console.log(`\n### ${need}`);
  for (const r of list.slice(0, 14)) {
    const red = (r.redLines ?? []).length ? '  RED-LINE' : '';
    console.log(`  ${String(r.downloads).padStart(7)}  ${r.npm.padEnd(42)} `
      + `${String(r.newestCompatible).padEnd(12)} ${r.category}${red}`);
    console.log(`           ${(r.zh || r.en).slice(0, 88)}`);
  }
  if (list.length > 14) console.log(`  ... ${list.length - 14} more`);
}
