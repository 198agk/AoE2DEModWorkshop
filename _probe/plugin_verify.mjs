// Two independent checks before recommending an install.
//
// 1. Re-verify every version /dsh-market/find-compatible returned, by fetching
//    the packument ourselves and running the market's OWN classifier on it.  A
//    single HTTP call is evidence; re-deriving it is corroboration -- and if the
//    route ever regressed, this file would notice.
// 2. Pull each candidate's declared capabilities and capabilityRedLines from
//    the catalog, because "compatible" is not "harmless".  A plugin that reads
//    the whole filesystem or talks to the network should be a conscious choice.
import { readFileSync } from 'node:fs';
import { deriveHostCompatibility, manifestFacts }
  from 'file:///C:/Users/26913/.dsh/profiles/desktop/node_modules/dshmarket/lib/discovery-compatibility.js';

const CATALOG = 'D:/Software/DeepSeek Harness/工作区2/_probe/awesome_plugins.json';
const MIRROR = 'https://mirrors.cloud.tencent.com/npm';

const HOST_VERSION = '0.2.0-rc.2';
const HOST_PACKAGES = new Set([
  '@deepseek-ai/dsh', '@deepseek-ai/dsh-tools', '@deepseek-ai/dsh-llm',
  '@deepseek-ai/dsh-agent', '@deepseek-ai/dsh-session', '@deepseek-ai/dsh-commands',
  '@deepseek-ai/dsh-skill', '@deepseek-ai/dsh-settings', '@deepseek-ai/dsh-workspace',
  '@deepseek-ai/dsh-host-webserver', '@deepseek-ai/dsh-client-ui-slots',
  '@deepseek-ai/dsh-client-locale', '@deepseek-ai/dsh-client-runtime',
  '@deepseek-ai/dsh-client-ui-primitives', '@deepseek-ai/dsh-attachment',
  '@deepseek-ai/dsh-atomic-write', '@deepseek-ai/dsh-home-paths',
  '@deepseek-ai/dsh-llm-pi-ai', '@deepseek-ai/dsh-system-prompt',
  '@deepseek-ai/dsh-client-ui-settings',
]);

// name -> the version the market said would work (null = market found none).
// Second batch: the ones the ecosystem-wide scan surfaced that map onto a
// problem this session actually hit (driving the game window, pixel comparison,
// being told when a 20-minute suite ends, seeing what compression did).
const WANT = {
  'dsh-click': null,
  'dsh-notify-me': null,
  'dsh-image-viewer': null,
  'dsh-builtin-browser': null,
  '@openma/deepseek-harness-acp': null,
  'dsh-cost-meter': null,
  'dsh-context-compression-improved': null,
  'dsh-skill-hub': null,
  'dsh-rewind-plugin': null,
  'dsh-ui-tweaks': null,
  'dsh-bash-terminal-ts': null,
  'dsh-mcp-panel': null,
  'dsh-better-sidebar': null,
  'dsh-image-gen': null,
  'dsh-prompt': null,
  '@weibaohui/skills-management': null,
  '@linxin666/dsh-client-ui-skill-explorer': null,
};

const catalog = JSON.parse(readFileSync(CATALOG, 'utf8'));
const byNpm = new Map();
for (const p of catalog.plugins ?? catalog) {
  const key = p.npm ?? p.name;
  if (key) byNpm.set(key, p);
}

// The ecosystem scan already walked every published version; reuse its answer
// so this check confirms the SAME version the scan would recommend.  Without
// this, a plugin whose newest compatible release is behind `latest` would look
// refuted here purely because the scan's finding was not passed along.
const SCAN = 'D:/Software/DeepSeek Harness/工作区2/_probe/plugin_scan.json';
const scanned = new Map();
try {
  const s = JSON.parse(readFileSync(SCAN, 'utf8'));
  for (const r of s.compatible ?? []) scanned.set(r.npm, r.newestCompatible);
} catch { /* scan not run yet; fall back to the market answer only */ }

async function packument(name) {
  const res = await fetch(`${MIRROR}/${name.replace('/', '%2F')}`,
    { signal: AbortSignal.timeout(20_000), headers: { accept: 'application/json' } });
  if (!res.ok) return null;
  return res.json();
}

let confirmed = 0, refuted = 0, unreadable = 0;
for (const [name, marketSaid] of Object.entries(WANT)) {
  const cat = byNpm.get(name) ?? {};
  const caps = (cat.capabilities ?? []).join(', ') || '(none declared)';
  const reds = (cat.capabilityRedLines ?? []);
  const redText = reds.length
    ? reds.map(r => typeof r === 'string' ? r : (r.zh ?? r.en ?? JSON.stringify(r))).join(' / ')
    : '(none)';
  console.log(`\n=== ${name}`);
  console.log(`    category    : ${cat.category ?? '?'}   stars ${cat.stars ?? '?'}  downloads ${cat.downloads ?? '?'}`);
  console.log(`    install     : ${cat.install ?? '(no install snippet in catalog)'}`);
  console.log(`    capabilities: ${caps}`);
  console.log(`    red lines   : ${redText}`);

  const doc = await packument(name);
  if (doc === null) {
    unreadable += 1;
    console.log(`    verify      : packument unreadable (not an npm-published package?)`);
    continue;
  }
  const versions = doc.versions ?? {};
  // Prefer the market's answer, then the scan's newest-compatible, then latest.
  // Re-derive the verdict rather than trusting any of them.
  const target = marketSaid ?? scanned.get(name) ?? doc['dist-tags']?.latest ?? null;
  if (target === null || versions[target] === undefined) {
    console.log(`    verify      : version ${target} absent from the packument`);
    refuted += 1;
    continue;
  }
  const verdict = deriveHostCompatibility(
    manifestFacts(versions[target]), HOST_VERSION, HOST_PACKAGES).status;
  const ok = verdict === 'compatible';
  if (ok) confirmed += 1; else refuted += 1;
  console.log(`    verify      : ${target} -> ${verdict} ${ok ? '(CONFIRMED)' : '(REFUTED)'}`);
  if (!ok) {
    // Show what the version we checked declares, so the mismatch is visible
    // instead of implied.
    const facts = manifestFacts(versions[target]);
    const peers = Object.entries(facts.peerDependencies ?? {});
    if (peers.length === 0 && facts.enginesDsh === null) {
      console.log(`                  declares no dsh peers at all (nothing decides it)`);
    }
    for (const [k, v] of peers) console.log(`                  wants ${k} ${v}`);
    if (facts.enginesDsh !== null) console.log(`                  wants engine ${facts.enginesDsh}`);
  }
}

console.log(`\nverified: ${confirmed} confirmed, ${refuted} refuted/unreadable, ${unreadable} no packument`);
