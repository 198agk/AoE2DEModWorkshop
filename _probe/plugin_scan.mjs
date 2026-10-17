// Classify a whole slice of the ecosystem instead of a hand-picked list.
//
// The shortlist was assembled by keyword; this answers the opposite question --
// "of everything published that is plausibly useful here, what would actually
// install on kernel 0.2.0-rc.2?"  It reuses the market's own classifier, so a
// verdict here is the verdict the install button gets.
import { readFileSync, writeFileSync } from 'node:fs';
import { deriveHostCompatibility, manifestFacts }
  from 'file:///C:/Users/26913/.dsh/profiles/desktop/node_modules/dshmarket/lib/discovery-compatibility.js';

const CATALOG = 'D:/Software/DeepSeek Harness/工作区2/_probe/awesome_plugins.json';
const OUT = 'D:/Software/DeepSeek Harness/工作区2/_probe/plugin_scan.json';
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

// Categories that could plausibly serve this project's actual problems:
// long test suites, reviewing what changed, searching the web for format docs,
// looking at rendered sprites, and keeping the skill library honest.
const WANTED = new Set(['tools', 'browser', 'vision', 'notify', 'dev',
                        'session', 'workflow', 'skill', 'usage', 'ui']);
const MIN_DOWNLOADS = 400;

const catalog = JSON.parse(readFileSync(CATALOG, 'utf8'));
const all = catalog.plugins ?? catalog;
const candidates = all.filter(p => {
  const npm = p.npm ?? p.name;
  return npm && WANTED.has(p.category) && (p.downloads ?? 0) >= MIN_DOWNLOADS;
});
console.log(`catalog ${all.length} -> ${candidates.length} candidates `
  + `(categories ${[...WANTED].join('/')}, downloads >= ${MIN_DOWNLOADS})`);

async function classify(p) {
  const npm = p.npm ?? p.name;
  try {
    const res = await fetch(`${MIRROR}/${npm.replace('/', '%2F')}`,
      { signal: AbortSignal.timeout(15_000), headers: { accept: 'application/json' } });
    if (!res.ok) return { npm, status: 'no-packument', http: res.status };
    const doc = await res.json();
    const versions = doc.versions ?? {};
    // Walk newest-first and report the newest version the host satisfies, which
    // is what an installer would pick -- not just a verdict on `latest`.
    const semver = Object.keys(versions)
      .filter(v => /^\d+\.\d+\.\d+/.test(v))
      .sort((a, b) => {
        const pa = a.split(/[-.]/).map(x => /^\d+$/.test(x) ? Number(x) : x);
        const pb = b.split(/[-.]/).map(x => /^\d+$/.test(x) ? Number(x) : x);
        for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
          const x = pa[i] ?? -1, y = pb[i] ?? -1;
          if (x === y) continue;
          if (typeof x === 'number' && typeof y === 'number') return y - x;
          if (typeof x === 'number') return -1;   // release outranks prerelease
          if (typeof y === 'number') return 1;
          return String(y).localeCompare(String(x));
        }
        return 0;
      });
    let newestCompatible = null;
    for (const v of semver) {
      const verdict = deriveHostCompatibility(
        manifestFacts(versions[v]), HOST_VERSION, HOST_PACKAGES).status;
      if (verdict === 'compatible') { newestCompatible = v; break; }
    }
    const latest = doc['dist-tags']?.latest ?? null;
    const latestVerdict = latest && versions[latest]
      ? deriveHostCompatibility(manifestFacts(versions[latest]), HOST_VERSION, HOST_PACKAGES).status
      : 'no-latest';
    return {
      npm, status: 'ok', latest, latestVerdict, newestCompatible,
      versionCount: semver.length,
    };
  } catch (e) {
    return { npm, status: 'error', error: String(e).slice(0, 80) };
  }
}

const results = [];
let cursor = 0;
const workers = Array.from({ length: 12 }, async () => {
  while (cursor < candidates.length) {
    const p = candidates[cursor++];
    const r = await classify(p);
    r.name = p.name; r.category = p.category;
    r.stars = p.stars; r.downloads = p.downloads;
    r.zh = (p.description?.zh ?? '').slice(0, 90);
    r.en = (p.description?.en ?? '').slice(0, 90);
    r.redLines = p.capabilityRedLines ?? [];
    results.push(r);
    if (results.length % 25 === 0) console.log(`  ... ${results.length}/${candidates.length}`);
  }
});
await Promise.all(workers);

const compatible = results.filter(r => r.status === 'ok' && r.newestCompatible);
const noVersion = results.filter(r => r.status === 'ok' && !r.newestCompatible);
const broken = results.filter(r => r.status !== 'ok');

writeFileSync(OUT, JSON.stringify({ host: HOST_VERSION, candidates: candidates.length,
  compatible, noVersion, broken }, null, 1), 'utf8');

console.log(`\nCOMPATIBLE somewhere in their history : ${compatible.length}`);
console.log(`no compatible release at all          : ${noVersion.length}`);
console.log(`packument unreadable                  : ${broken.length}`);
compatible.sort((a, b) => (b.downloads ?? 0) - (a.downloads ?? 0));
console.log('\nnewest compatible version per plugin (top 45 by downloads):');
for (const r of compatible.slice(0, 45)) {
  console.log(`  ${r.npm.padEnd(46)} ${String(r.newestCompatible).padEnd(12)} `
    + `latest=${r.latest} dl=${r.downloads}`);
}
console.log(`\nwrote ${OUT}`);
