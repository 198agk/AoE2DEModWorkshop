// Ask the MARKET'S OWN compatibility engine which shortlist plugins fit this
// host, instead of re-implementing semver badly in Python.
//
// The market already ships the classifier that decides installs
// (`deriveHostCompatibility` in discovery-compatibility.js).  Using it means a
// verdict here is the same verdict the install button would get -- including
// the prerelease handling, which is exactly where a hand-rolled range check
// goes wrong (`^4.0.4` is cordis's line, not the kernel's).
//
// Inputs:
//   hostVersion  -- the kernel's own version, read from /dsh-market/check
//   hostPackages -- {peer name: resolved version} straight from that report
//   the compat cache -- each candidate's declared peerDependencies
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { deriveHostCompatibility, manifestFacts }
  from 'file:///C:/Users/26913/.dsh/profiles/desktop/node_modules/dshmarket/lib/discovery-compatibility.js';

const CACHE = join(homedir(), '.dsh', 'profiles', 'desktop', '.dsh-market',
                   'discovery-compatibility-v1.json');

// Pulled from GET /dsh-market/check (resolved versions of every @deepseek-ai
// peer the profile actually has), plus the kernel version it reports.
//
// `hostPackages` must be a Set, and note which names it MUST contain: the
// classifier only consults packages matching /^@deepseek-ai\/dsh(?:-|$)/, so
// cordis and schemastery are deliberately excluded -- they version on their
// own lines and their ranges say nothing about the kernel.
const HOST_VERSION = '0.2.0-rc.2';
const HOST_PACKAGES = new Set([
  '@deepseek-ai/dsh',
  '@deepseek-ai/dsh-tools',
  '@deepseek-ai/dsh-llm',
  '@deepseek-ai/dsh-agent',
  '@deepseek-ai/dsh-session',
  '@deepseek-ai/dsh-commands',
  '@deepseek-ai/dsh-skill',
  '@deepseek-ai/dsh-settings',
  '@deepseek-ai/dsh-workspace',
  '@deepseek-ai/dsh-host-webserver',
  '@deepseek-ai/dsh-client-ui-slots',
  '@deepseek-ai/dsh-client-locale',
  '@deepseek-ai/dsh-client-runtime',
  '@deepseek-ai/dsh-client-ui-primitives',
  '@deepseek-ai/dsh-attachment',
  '@deepseek-ai/dsh-atomic-write',
  '@deepseek-ai/dsh-home-paths',
  '@deepseek-ai/dsh-llm-pi-ai',
  '@deepseek-ai/dsh-system-prompt',
  '@deepseek-ai/dsh-client-ui-settings',
  // NOT host packages, kept here only to document that they are ignored:
  // '@deepseek-ai/cordis', '@deepseek-ai/schemastery',
]);

// Names on argv override the built-in list, so a second batch can be checked
// without editing this file.  (Every candidate must be in the compat cache;
// unprobed ones come back UNPROBED and can be sent to plugin_find_version.mjs.)
const ARGV = process.argv.slice(2).filter(a => !a.startsWith('-'));

const SHORTLIST = [
  ['@michengai/dsh-skills-manager', 'manage/validate/import the five hand-written skills'],
  ['@linxin666/dsh-client-ui-skill-explorer', 'browse the skill tree read-only'],
  ['@lcthe/dsh-skills-hub', 'skill hub'],
  ['@weibaohui/skills-management', 'skill management'],
  ['@yanglaofish/dsh-skill-manager', 'skill pool / whitelist / per-session'],
  ['dsh-context', 'context dashboard + compression events'],
  ['dsh-client-auto-continue', 'auto-continue after an interrupted turn'],
  ['task-complete-notify-for-dsh', 'notify when a long run finishes'],
  ['@wingsky-1/dsh-notifier', 'notifications'],
  ['dsh-free-search', 'multi-engine search + web_fetch'],
  ['dsh-web-search-pro', 'multi-engine search + SQLite cache'],
  ['@liustack/modsearch', 'structured JSON search evidence'],
  ['@michengai/dsh-codex-ui', 'codex-style sidebar + global search'],
  ['@michengai/dsh-archive-manager', 'archived sessions page'],
  ['@linxin666/dsh-client-ui-task-board', 'task board + cron'],
  ['@michengai/dsh-agency-agents', 'summonable expert subagents'],
  ['@nanmicoder/dsh-agent-teams', 'agent teams'],
  ['@michengai/dsh-code-review', 'subagent review of a git range'],
  ['@michengai/dsh-simplify', 'simplify a git range'],
  ['@sduwall/dsh-wall-mcp-manager', 'MCP manager'],
  ['@caob23/dsh-browser-control', 'drive a real Chrome'],
  ['@anionex/dsh-vision-toolkit', 'vision toolkit'],
  ['dsh-windows-ocr', 'Windows OCR'],
  ['picturereader', 'read images'],
  ['dsh-deepread', 'deep reading of books/papers'],
  ['dsh-reasoning-effort', 'reasoning-effort slider'],
  ['@neptune810/dsh-model-router', 'route steps across a model pool'],
  ['@linxin666/dsh-client-ui-git-graph', 'git graph in the composer'],
  ['dsh-config-manager', 'backup/export/import the whole DSH config'],
];

const cache = JSON.parse(readFileSync(CACHE, 'utf8'));
const entries = cache.entries ?? {};

// Resolved versions the host actually has, from GET /dsh-market/check.  Kept
// separate from HOST_PACKAGES (which answers "is this a host package?") so the
// two questions -- membership and version -- cannot be confused.  Declared
// before the loop below, because `hostVersionOf` reads it there.
const RESOLVED = {
  '@deepseek-ai/dsh': '0.2.0-rc.2',
  '@deepseek-ai/dsh-tools': '0.2.0-rc.2',
  '@deepseek-ai/dsh-llm': '0.2.0-rc.2',
  '@deepseek-ai/dsh-agent': '0.2.0-rc.2',
  '@deepseek-ai/dsh-session': '0.2.0-rc.2',
  '@deepseek-ai/dsh-commands': '0.2.0-rc.2',
  '@deepseek-ai/dsh-skill': '0.2.0-rc.2',
  '@deepseek-ai/dsh-settings': '0.2.0-rc.2',
  '@deepseek-ai/dsh-workspace': '0.2.0-rc.2',
  '@deepseek-ai/dsh-host-webserver': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-slots': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-locale': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-runtime': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-primitives': '0.2.0-rc.2',
};
function hostVersionOf(name) {
  return RESOLVED[name] ?? 'unknown';
}

const verdicts = [];
const WATCH = ARGV.length > 0 ? ARGV.map(n => [n, 'argv']) : SHORTLIST;
for (const [name, why] of WATCH) {
  const e = entries[name];
  if (e === undefined) {
    verdicts.push({ name, why, status: 'UNPROBED', detail: 'no cached manifest' });
    continue;
  }
  const facts = e.facts ?? {};
  const result = deriveHostCompatibility(facts, HOST_VERSION, HOST_PACKAGES);
  // `deriveHostCompatibility` returns the STATUS but not the per-declaration
  // breakdown (it returns `declarations`, not `outcomes` -- only the internal
  // `declarationResult` sees the boolean).  Report the declarations and let the
  // reader see which range produced the verdict.
  const decls = (result.declarations ?? []).map(d => d.package ?? d.kind);
  const blocking = (result.declarations ?? []).map(d => {
    const held = d.kind === 'engine' ? HOST_VERSION : HOST_PACKAGES.has(d.package)
      ? hostVersionOf(d.package) : 'nothing';
    return `${d.package ?? d.kind} needs ${d.range}, host has ${held}`;
  });
  verdicts.push({
    name, why,
    version: facts.version ?? '-',
    status: result.status,
    basis: result.basis,
    requirement: result.requirement,
    blocking: result.status === 'compatible' ? [] : blocking,
    warnings: decls.length === 0 ? ['nothing in the catalog decides it'] : [],
  });
}

const order = ['compatible', 'UNPROBED', 'risky', 'incompatible'];
verdicts.sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));
for (const v of verdicts) {
  console.log(`${(v.status ?? '?').padEnd(13)} ${(v.version ?? '-').padEnd(10)} ${v.name}`);
  console.log(`              ${v.why}`);
  for (const b of v.blocking ?? []) console.log(`      BLOCKS ${b}`);
  for (const w of v.warnings ?? []) console.log(`      warns  ${w}`);
}
