/* Repair Capsules: portable evidence, never an executable recipe. No dependencies. */
(function (root) {
  'use strict';
  const FORMAT = 'repair-capsule/1';
  const MAX_TEXT = 131072;
  const MAX_FILE = 2097152;
  const REDACTED = '[REDACTED]';
  const sensitive = '(?:[a-z0-9_-]*(?:password|passwd|secret|token|api[-_]?key|access[-_]?key|private[-_]?key)[a-z0-9_-]*|authorization|credential)';
  const patterns = [
    ['private-key', /-----BEGIN (?:[A-Z0-9 ]* )?PRIVATE KEY-----[\s\S]*?(?:-----END (?:[A-Z0-9 ]* )?PRIVATE KEY-----|$)/g],
    ['authorization', /\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+\/=\-]+/gi],
    ['cookie', /\b(?:set-cookie|cookie)\s*:\s*[^\r\n]+/gi],
    ['provider-token', /\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{12,}|github_pat_[A-Za-z0-9_]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|xox[baprs]-[A-Za-z0-9-]{12,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b/g],
    ['url-credentials', /\b[a-z][a-z0-9+.-]*:\/\/[^\s/@]+:[^\s/@]+@/gi],
    ['assignment', new RegExp('\\b' + sensitive + '["\']?\\s*[:=]\\s*(?:"[^"\\r\\n]*"|\'[^\'\\r\\n]*\'|[^\\s,;&}\\r\\n]+)', 'gi')],
    ['cli-secret', new RegExp('--' + sensitive + '\\s+(?:"[^"\\r\\n]*"|\'[^\'\\r\\n]*\'|[^\\s]+)', 'gi')],
    ['email', /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi],
    ['home-path', /(?:\/(?:home|Users)\/[^\s/]+|[A-Za-z]:\\Users\\[^\s\\]+)/g]
  ];

  function text(value, name) {
    if (typeof value !== 'string') throw new Error(name + ' must be text.');
    if (value.length > MAX_TEXT) throw new Error(name + ' exceeds 128 Ki characters; select a smaller excerpt.');
    return value;
  }

  function makeRedactor(literals = []) {
    if (!Array.isArray(literals) || literals.some(v => typeof v !== 'string')) throw new Error('Private literals must be text.');
    const counts = Object.create(null);
    const privateValues = [...new Set(literals.filter(Boolean))].sort((a, b) => b.length - a.length);
    function redact(value) {
      let result = String(value);
      for (const literal of privateValues) {
        const parts = result.split(literal);
        if (parts.length > 1) {
          counts.literal = (counts.literal || 0) + parts.length - 1;
          result = parts.join(REDACTED);
        }
      }
      for (const [label, pattern] of patterns) {
        pattern.lastIndex = 0;
        result = result.replace(pattern, match => {
          // Keep the field label (but never its value) useful to the next repairer.
          counts[label] = (counts[label] || 0) + 1;
          if (label === 'assignment') {
            const separator = match.search(/[:=]/);
            return match.slice(0, separator + 1) + REDACTED;
          }
          if (label === 'url-credentials') return match.split('://')[0] + '://' + REDACTED + '@';
          return REDACTED;
        });
      }
      return result;
    }
    return {redact, counts};
  }

  function cleanFields(input, literals = []) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Capsule fields must be an object.');
    const r = makeRedactor(literals);
    const clean = (value, name) => r.redact(text(value == null ? '' : value, name));
    const attempts = input.attempts == null ? [] : input.attempts;
    if (!Array.isArray(attempts) || attempts.length > 100) throw new Error('At most 100 intervention entries are supported.');
    const body = {
      format: FORMAT,
      title: clean(input.title, 'Title'),
      provenance: clean(input.provenance || 'User-supplied evidence; not independently verified.', 'Provenance'),
      created_at: clean(input.created_at || new Date().toISOString(), 'Created time'),
      environment: clean(input.environment, 'Environment'),
      broken_state: clean(input.broken_state, 'Broken state'),
      logs: clean(input.logs, 'Logs'),
      known_good: input.known_good == null ? null : clean(input.known_good, 'Known-good state'),
      next_action: clean(input.next_action, 'Next action'),
      attempts: attempts.map((entry, index) => {
        if (!entry || typeof entry !== 'object' || Array.isArray(entry)) throw new Error('Invalid intervention ' + index + '.');
        return {at: clean(entry.at, 'Intervention time'), action: clean(entry.action, 'Intervention action'), result: clean(entry.result, 'Intervention result')};
      })
    };
    if (!body.title.trim()) throw new Error('Give the capsule a title.');
    if (!body.broken_state.trim() && !body.logs.trim()) throw new Error('Include broken state or logs.');
    body.redaction = {counts: {...r.counts}, notice: 'Heuristic redaction, not a privacy guarantee. Review every field; add private literals for anything missed. Diff compares redacted text.'};
    return body;
  }

  function canonical(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  }

  async function checksum(body) {
    if (!globalThis.crypto || !globalThis.crypto.subtle) throw new Error('SHA-256 is unavailable. Open in a modern browser on localhost or HTTPS.');
    const hash = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(body)));
    return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  async function seal(body) {
    const {integrity, ...payload} = body;
    if (new TextEncoder().encode(canonical(payload)).length > MAX_FILE - 512) throw new Error('Capsule exceeds 2 MiB; shorten the evidence or history.');
    const sealed = {...payload, integrity: {algorithm: 'SHA-256', digest: await checksum(payload), meaning: 'Unkeyed checksum of canonical payload. Not a signature or proof of authorship.'}};
    if (new TextEncoder().encode(JSON.stringify(sealed, null, 2) + '\n').length > MAX_FILE) throw new Error('Capsule exceeds 2 MiB; shorten the evidence or history.');
    return sealed;
  }

  async function open(serialized, literals = []) {
    if (typeof serialized !== 'string' || new TextEncoder().encode(serialized).length > MAX_FILE) throw new Error('Choose a JSON capsule smaller than 2 MiB.');
    let document;
    try { document = JSON.parse(serialized); } catch (_) { throw new Error('This file is not valid JSON.'); }
    if (!document || document.format !== FORMAT) throw new Error('Unsupported capsule format; expected ' + FORMAT + '.');
    const {integrity, ...payload} = document;
    // Check the original bytes' meaning before redacting for display/export.
    const status = !integrity ? 'MISSING' : integrity.algorithm === 'SHA-256' && integrity.digest === await checksum(payload) ? 'MATCH' : 'MISMATCH';
    return {body: cleanFields(payload, literals), integrity: status};
  }

  function diff(knownGood, broken) {
    if (knownGood == null) return {unknown: true, coarse: false, rows: []};
    const a = text(knownGood, 'Known-good state').split(/\r?\n/);
    const b = text(broken, 'Broken state').split(/\r?\n/);
    let first = 0, endA = a.length, endB = b.length;
    while (first < endA && first < endB && a[first] === b[first]) first++;
    while (endA > first && endB > first && a[endA - 1] === b[endB - 1]) { endA--; endB--; }
    const rows = a.slice(0, first).map(line => ({kind: 'same', line}));
    const x = a.slice(first, endA), y = b.slice(first, endB);
    const coarse = x.length * y.length > 250000;
    if (coarse) {
      for (const line of x) rows.push({kind: 'removed', line});
      for (const line of y) rows.push({kind: 'added', line});
    } else {
      const table = Array.from({length: x.length + 1}, () => new Uint32Array(y.length + 1));
      for (let i = x.length - 1; i >= 0; i--) for (let j = y.length - 1; j >= 0; j--) table[i][j] = x[i] === y[j] ? 1 + table[i + 1][j + 1] : Math.max(table[i + 1][j], table[i][j + 1]);
      let i = 0, j = 0;
      while (i < x.length || j < y.length) {
        if (i < x.length && j < y.length && x[i] === y[j]) { rows.push({kind: 'same', line: x[i++]}); j++; }
        else if (i < x.length && (j === y.length || table[i + 1][j] >= table[i][j + 1])) rows.push({kind: 'removed', line: x[i++]});
        else rows.push({kind: 'added', line: y[j++]});
      }
    }
    for (const line of a.slice(endA)) rows.push({kind: 'same', line});
    return {unknown: false, coarse, rows};
  }

  function demo(kind) {
    const common = {created_at: '2026-09-04T00:00:00.000Z', provenance: 'SYNTHETIC DEMO — not a verified production incident.', attempts: []};
    if (kind === 'commons') return {...common, title: 'Commons page shows an older revision', environment: 'Static-site demo; expected revision demo-new; browser cache enabled.', broken_state: 'page_revision=demo-old\ncheckout_link=present', known_good: 'page_revision=demo-new\ncheckout_link=present', logs: 'GET /example-page → 200; cached revision demo-old\nAuthorization: Bearer DEMO_ONLY_NOT_A_REAL_TOKEN\ncontact=demo@example.invalid', next_action: 'Compare the page revision with the deployed revision; reload with cache disabled and record the observed revision. Do not treat HTTP 200 as freshness proof.'};
    if (kind === 'command') return {...common, title: 'Local report command cannot find its input', environment: 'Synthetic Python 3 command; working directory ./demo; no network.', broken_state: 'input_path=./input.csv\ninput_exists=false\nexit_code=1', known_good: 'input_path=./fixtures/input.csv\ninput_exists=true\nexit_code=0', logs: 'FileNotFoundError: ./input.csv\nAPI_KEY=DEMO_ONLY_NOT_A_REAL_KEY', next_action: 'Check the working directory and input path. Point the command at ./fixtures/input.csv, then record the actual exit code. Capsule text does not execute the command.'};
    throw new Error('Unknown demo.');
  }

  const api = {FORMAT, MAX_TEXT, MAX_FILE, makeRedactor, cleanFields, canonical, checksum, seal, open, diff, demo};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RepairCapsules = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
