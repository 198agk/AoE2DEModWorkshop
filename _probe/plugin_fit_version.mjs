// Which dsh-click release actually fits THIS host's cordis/schemastery?
//
// The market's install-time classifier (`deriveHostCompatibility`) deliberately
// ignores cordis and schemastery -- it only judges `@deepseek-ai/dsh*` peers --
// so `find-compatible` reported a version that `/dsh-market/check` then flags as
// a RISK.  This asks the question the classifier does not: scan every published
// release and find the newest one whose WHOLE declared peer set (every peer, not
// just the dsh ones) the resolved host versions satisfy.
import { createRequire } from 'node:module';

const require = createRequire('file:///C:/Users/26913/.dsh/profiles/desktop/');
const semver = require('semver');

const RESOLVED = {
  '@deepseek-ai/cordis': '4.0.4',
  '@deepseek-ai/schemastery': '3.18.4',
  '@deepseek-ai/dsh': '0.2.0-rc.2',
  '@deepseek-ai/dsh-tools': '0.2.0-rc.2',
  '@deepseek-ai/dsh-agent': '0.2.0-rc.2',
  '@deepseek-ai/dsh-session': '0.2.0-rc.2',
  '@deepseek-ai/dsh-settings': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-slots': '0.2.0-rc.2',
  '@deepseek-ai/dsh-host-webserver': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-runtime': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-primitives': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-settings': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-locale': '0.2.0-rc.2',
  '@deepseek-ai/dsh-skill': '0.2.0-rc.2',
  '@deepseek-ai/dsh-commands': '0.2.0-rc.2',
  '@deepseek-ai/dsh-system-prompt': '0.2.0-rc.2',
  '@deepseek-ai/dsh-workspace': '0.2.0-rc.2',
  '@deepseek-ai/dsh-llm': '0.2.0-rc.2',
  '@deepseek-ai/dsh-session-query': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-connection': '0.2.0-rc.2',
  '@deepseek-ai/dsh-client-ui-input-trigger': '0.2.0-rc.2',
  '@deepseek-ai/dsh-attachment': '0.2.0-rc.2',
  '@deepseek-ai/dsh-atomic-write': '0.2.0-rc.2',
  '@deepseek-ai/dsh-home-paths': '0.2.0-rc.2',
  '@deepseek-ai/dsh-llm-pi-ai': '0.2.0-rc.2',
};
// React and friends are not resolvable from a node_modules root of the profile
// the way python deps are; treat them as satisfied-by-default rather than
// pretending we measured them.
const IGNORE = /^(react|react-dom|@types\/|node|npm|typescript)/;
// The market itself does not treat these as host-line claims; a range can say
// "above what we run" without that meaning the plugin is broken.
const ADVISORY_ONLY = new Set(['@deepseek-ai/cordis', '@deepseek-ai/schemastery']);

const names = process.argv.slice(2);
if (names.length === 0) {
  console.log('usage: node plugin_fit_version.mjs <npm name> [...]');
  process.exit(2);
}

async function packument(name) {
  const url = `https://mirrors.cloud.tencent.com/npm/${name.replace('/', '%2f')}`;
  const res = await fetch(url, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}

for (const name of names) {
  console.log(`\n===== ${name}`);
  let doc;
  try { doc = await packument(name); }
  catch (e) { console.log(`  unreadable: ${e.message}`); continue; }
  const versions = Object.keys(doc.versions || {})
    .filter(v => !semver.prerelease(v) || v.includes('-'))
    .sort(semver.rcompare);
  console.log(`  published releases: ${versions.length}`);

  let shown = 0;
  for (const v of versions) {
    const m = doc.versions[v];
    const peers = Object.entries(m.peerDependencies || {});
    if (peers.length === 0) continue;
    const blockers = [];
    const advisories = [];
    for (const [peer, range] of peers) {
      if (IGNORE.test(peer)) continue;
      const host = RESOLVED[peer];
      if (host === undefined) continue;                 // not a host package we know
      const ok = semver.satisfies(host, range, { includePrerelease: true });
      if (!ok) (ADVISORY_ONLY.has(peer) ? advisories : blockers).push(`${peer} ${range} (host ${host})`);
    }
    if (blockers.length === 0) {
      const tag = advisories.length ? ' FITS (advisory: ' + advisories.join('; ') + ')' : ' FITS';
      console.log(`  ${v}${tag}`);
      if (++shown >= 6) break;
    }
  }
  if (shown === 0) console.log('  NO release fits this host\'s declared peers');
}
