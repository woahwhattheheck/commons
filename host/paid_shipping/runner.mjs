import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { pathToFileURL } from 'node:url';
import { gzipSync, gunzipSync } from 'node:zlib';
import { tick, validNotice } from './worker.mjs';

const PRIVATE_REPO = 'woahwhattheheck/commons-ship-enforcer';
const STATE_PATH = 'paid-work/shipping-state.json';
const STATE_DIR = 'paid-work/shipping-state';
const SHARD_THREADS = 200;
const NOTICE_PREFIX = 'paid-work/shipping-operator-notices/';
const PUBLISHER = 'https://account-publisher.tjlabs-publisher.workers.dev';
const MAX_RAW_STATE_BYTES = 32 * 1024 * 1024;
const TABLES = ['slack_shipping_cursors', 'slack_shipping_threads', 'slack_shipping_outbox',
  'slack_shipping_state', 'slack_shipping_operator_notices'];
const sha256 = value => createHash('sha256').update(value).digest('hex');
const b64 = value => Buffer.from(value, 'utf8').toString('base64');
const unb64 = value => Buffer.from(value.replace(/\s/gu, ''), 'base64').toString('utf8');
const ghPath = path => `/repos/${PRIVATE_REPO}/${path}`;

function requireToken(env) {
  if (!env.COMMONS_GITHUB_TOKEN || !env.SLACK_BOT_TOKEN || !env.TYPESAFE_API_KEY)
    throw new Error('secrets_unbound');
}

async function github(env, path) {
  const response = await fetch(`https://api.github.com${path}`, { headers: {
    Authorization: `Bearer ${env.COMMONS_GITHUB_TOKEN}`, Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'commons-shipping-enforcer'
  } });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`github_read_${response.status}`);
  return response.json();
}

async function readFile(env, path) {
  const entry = await github(env, ghPath(`contents/${path}?ref=main`));
  if (!entry) return null;
  if (entry.type !== 'file' || typeof entry.content !== 'string' || !/^[a-f0-9]{40}$/iu.test(entry.sha))
    throw new Error('private_file_invalid');
  return { sha: entry.sha, text: unb64(entry.content) };
}

function publisherStateError(result, status) {
  const reason = String((result && (result.reason_code || result.error)) || status || 'unknown')
    .toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '') || 'unknown';
  return new Error(`publisher_state_${reason}`);
}

export async function putPrivateFile(env, path, text, previousSha) {
  if (Buffer.byteLength(text, 'utf8') > 390_000) throw new Error('private_file_too_large');
  const operationId = `ship-${sha256(`${path}\n${previousSha || 'new'}\n${sha256(text)}`)}`;
  const args = { owner: 'woahwhattheheck', repo: 'commons-ship-enforcer', path,
    message: `Update shipping monitor state ${operationId.slice(5, 17)}`,
    content: b64(text), ...(previousSha ? { sha: previousSha } : {}) };
  const payload = { operation_id: operationId, operation: 'file.put', args };
  let response, result = {};
  for (let attempt = 0; attempt < 8; attempt++) {
    response = await fetch(`${PUBLISHER}/v1/publish`, { method: 'POST', headers: {
      Authorization: `Bearer ${env.COMMONS_GITHUB_TOKEN}`, Accept: 'application/json',
      'Content-Type': 'application/json', 'User-Agent': 'Commons-Shipping-Enforcer/1.0'
    }, body: JSON.stringify(payload) });
    result = await response.json().catch(() => ({}));
    if (response.status === 409 && result.error === 'RESOURCE_BUSY') {
      await new Promise(resolve => setTimeout(resolve, Math.min(2 ** attempt, 30) * 1000));
      continue;
    }
    break;
  }
  if (!response.ok || result.allow !== true || !result.receipt?.commit?.oid)
    throw publisherStateError(result, response.status);
  return result.receipt.commit.oid;
}

function decodeVersion2(state) {
  const hex = state.codec === 'gzip+hex';
  const b64c = state.codec === 'gzip+base64';
  if ((!hex && !b64c) || typeof state.data !== 'string' ||
    !/^[a-f0-9]{64}$/u.test(state.raw_sha256 || '') ||
    (b64c && !/^[A-Za-z0-9+/]*={0,2}$/u.test(state.data)) ||
    (hex && !/^[0-9a-f]*$/u.test(state.data))) throw new Error('state_schema_invalid');
  let raw;
  try {
    raw = gunzipSync(Buffer.from(state.data, hex ? 'hex' : 'base64'),
      { maxOutputLength: MAX_RAW_STATE_BYTES });
  } catch { throw new Error('state_decompression_invalid'); }
  if (sha256(raw) !== state.raw_sha256) throw new Error('state_checksum_invalid');
  return raw;
}

function opaqueEnvelope(raw) {
  return JSON.stringify({ version: 2, codec: 'gzip+hex', raw_sha256: sha256(raw),
    data: gzipSync(raw, { level: 9 }).toString('hex') }) + '\n';
}

export function openState(snapshot) {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('./schema.sql', import.meta.url), 'utf8'));
  // Cloud incidents are emitted through the publisher. This free runner reads only
  // its private Git notice ledger and never invokes the Cloudflare/D1 monitor.
  sqlite.exec('CREATE TABLE incidents (id TEXT, op_id TEXT, reason TEXT, destination TEXT, email_status TEXT)');
  if (snapshot) {
    let state = JSON.parse(snapshot);
    if (state.version === 2) {
      state = JSON.parse(decodeVersion2(state).toString('utf8'));
    }
    if (state.version !== 1 || !state.tables || Object.keys(state.tables).some(k => !TABLES.includes(k)))
      throw new Error('state_schema_invalid');
    for (const table of TABLES) {
      const rows = state.tables[table] || [];
      if (!Array.isArray(rows)) throw new Error('state_schema_invalid');
      const columns = sqlite.prepare(`PRAGMA table_info(${table})`).all().map(x => x.name);
      for (const row of rows) {
        if (!row || Object.keys(row).some(k => !columns.includes(k))) throw new Error('state_schema_invalid');
        const names = Object.keys(row);
        if (!names.length) continue;
        sqlite.prepare(`INSERT INTO ${table} (${names.join(',')}) VALUES (${names.map(() => '?').join(',')})`)
          .run(...names.map(k => row[k]));
      }
    }
  }
  const DB = { prepare(sql) { return { bind(...args) {
    const query = sqlite.prepare(sql);
    return {
      first: async () => query.get(...args),
      all: async () => ({ results: query.all(...args) }),
      run: async () => ({ meta: { changes: query.run(...args).changes } })
    };
  } }; } };
  return { sqlite, DB };
}

export function serializeState(sqlite) {
  const tables = Object.fromEntries(TABLES.map(table => [table,
    sqlite.prepare(`SELECT * FROM ${table} ORDER BY rowid`).all()]));
  const raw = Buffer.from(JSON.stringify({ version: 1, tables }) + '\n', 'utf8');
  if (raw.length > MAX_RAW_STATE_BYTES) throw new Error('state_raw_too_large');
  return JSON.stringify({ version: 2, codec: 'gzip+base64', raw_sha256: sha256(raw),
    data: gzipSync(raw, { level: 9 }).toString('base64') }) + '\n';
}

export function planStateFiles(sqlite) {
  const tables = Object.fromEntries(TABLES.map(table => [table,
    sqlite.prepare(`SELECT * FROM ${table} ORDER BY rowid`).all()]));
  const threads = tables.slack_shipping_threads;
  if (threads.length <= SHARD_THREADS) {
    return { mode: 'single', files: [{ path: STATE_PATH, text: serializeState(sqlite) }] };
  }
  const files = [];
  const names = [];
  for (let index = 0; index < threads.length; index += SHARD_THREADS) {
    const rows = threads.slice(index, index + SHARD_THREADS);
    const name = `threads-${String(names.length).padStart(4, '0')}.json`;
    const raw = Buffer.from(JSON.stringify({ version: 1, table: 'slack_shipping_threads', rows }) + '\n', 'utf8');
    files.push({ path: `${STATE_DIR}/${name}`, text: opaqueEnvelope(raw) });
    names.push(name);
  }
  const rest = { version: 1, tables: { ...tables, slack_shipping_threads: [] } };
  const restRaw = Buffer.from(JSON.stringify(rest) + '\n', 'utf8');
  files.push({ path: `${STATE_DIR}/rest.json`, text: opaqueEnvelope(restRaw) });
  files.push({ path: STATE_PATH, text: JSON.stringify({
    version: 3, codec: 'shard-gzip+hex', shards: names, rest: 'rest.json',
    thread_count: threads.length }) + '\n' });
  return { mode: 'sharded', files };
}

async function materializeState(env, stored) {
  const state = JSON.parse(stored.text);
  if (state.version !== 3) return stored.text;
  if (state.codec !== 'shard-gzip+hex' || !Array.isArray(state.shards) || typeof state.rest !== 'string')
    throw new Error('state_schema_invalid');
  const threads = [];
  for (const name of state.shards) {
    if (!/^threads-\d{4}\.json$/u.test(name)) throw new Error('state_schema_invalid');
    const file = await readFile(env, `${STATE_DIR}/${name}`);
    if (!file) throw new Error('state_shard_missing');
    const part = JSON.parse(decodeVersion2(JSON.parse(file.text)).toString('utf8'));
    if (part.version !== 1 || part.table !== 'slack_shipping_threads' || !Array.isArray(part.rows))
      throw new Error('state_schema_invalid');
    threads.push(...part.rows);
  }
  if (!/^rest\.json$/u.test(state.rest)) throw new Error('state_schema_invalid');
  const restFile = await readFile(env, `${STATE_DIR}/${state.rest}`);
  if (!restFile) throw new Error('state_shard_missing');
  const rest = JSON.parse(decodeVersion2(JSON.parse(restFile.text)).toString('utf8'));
  if (rest.version !== 1 || !rest.tables) throw new Error('state_schema_invalid');
  rest.tables.slack_shipping_threads = threads;
  return JSON.stringify(rest);
}

async function persistShardedState(env, plan, stored) {
  for (const file of plan.files) {
    if (file.path === STATE_PATH) continue;
    const prev = await readFile(env, file.path);
    if (prev && prev.text === file.text) continue;
    await putPrivateFile(env, file.path, file.text, prev ? prev.sha : undefined);
  }
  const index = plan.files.find(file => file.path === STATE_PATH);
  if (index.text !== stored.text)
    await putPrivateFile(env, STATE_PATH, index.text, stored.sha);
}

async function importNotices(env, sqlite) {
  const tree = await github(env, ghPath('git/trees/main?recursive=1'));
  if (!tree || tree.truncated || !Array.isArray(tree.tree)) throw new Error('notice_index_incomplete');
  const pending = tree.tree.filter(x => x.type === 'blob' &&
    new RegExp(`^${NOTICE_PREFIX}[a-f0-9]{64}\\.json$`, 'u').test(x.path))
    .filter(x => !sqlite.prepare('SELECT 1 FROM slack_shipping_operator_notices WHERE notice_id=?')
      .get(x.path.slice(NOTICE_PREFIX.length, -5))).slice(0, 4);
  for (const entry of pending) {
    const file = await readFile(env, entry.path);
    if (!file) throw new Error('notice_file_disappeared');
    const notice = JSON.parse(file.text);
    if (!validNotice(notice) || entry.path !== `${NOTICE_PREFIX}${notice.notice_id}.json`)
      throw new Error('notice_file_invalid');
    sqlite.prepare(`INSERT OR IGNORE INTO slack_shipping_operator_notices
      (notice_id,reason_code,tool_name,operation_id,repository,issue_number,created_at)
      VALUES (?,?,?,?,?,?,?)`).run(notice.notice_id, notice.reason_code, notice.tool_name,
      notice.operation_id || null, notice.repository || null, notice.issue_number || null,
      Math.floor(Date.now() / 1000));
  }
  return pending.length;
}

export async function runMonitor(env = process.env) {
  requireToken(env);
  const repository = await github(env, `/repos/${PRIVATE_REPO}`);
  if (repository?.private !== true || repository.visibility !== 'private')
    throw new Error('private_repository_required');
  let stored = await readFile(env, STATE_PATH);
  if (!stored) {
    const base = openState();
    const initial = serializeState(base.sqlite);
    base.sqlite.close();
    await putPrivateFile(env, STATE_PATH, initial);
    stored = await readFile(env, STATE_PATH);
    if (!stored) throw new Error('state_bootstrap_unconfirmed');
  }
  const loaded = await materializeState(env, stored);
  const { sqlite, DB } = openState(loaded);
  try {
    const imported = await importNotices(env, sqlite);
    const result = await tick({ DB, FREE_ACTIONS: true, SLACK_BOT_TOKEN: env.SLACK_BOT_TOKEN,
      GITHUB_TOKEN: env.COMMONS_GITHUB_TOKEN, TYPESAFE_API_KEY: env.TYPESAFE_API_KEY });
    const plan = planStateFiles(sqlite);
    if (plan.mode === 'single') {
      const next = plan.files[0].text;
      if (next !== stored.text) await putPrivateFile(env, STATE_PATH, next, stored.sha);
    } else {
      await persistShardedState(env, plan, stored);
    }
    return { imported, mode: result.mode, slack_writes: result.slack_writes,
      channels: result.channels.map(c => ({ channel: c.channel,
      messages: c.messages || 0, queued: c.queued || 0,
      recent_messages: c.recent?.messages || 0, recent_queued: c.recent?.queued || 0,
      error: c.error || null })),
      thread_pages: result.threads.pages || 0,
      thread_rate_limited: Boolean(result.threads.rate_limited),
      thread_deadline_reached: Boolean(result.threads.deadline_reached),
      thread_error: result.threads.error || null,
      incident_error: result.incidents.error || null,
      operator_error: result.operators?.error || null,
      delivered: typeof result.delivered === 'number' ? result.delivered : 0,
      delivery_error: result.delivered.error || null,
      delivery_code: result.delivered.code || null,
      delivery_held: result.delivered.held || 0,
      operator_held: result.operators?.held || 0,
      incident_held: result.incidents.held || 0,
      jev: result.jev };
  } finally { sqlite.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  runMonitor().then(result => {
    const rateLimited = result.thread_rate_limited || result.channels.some(c => c.error === 'slack_rate_limited') ||
      result.delivery_error === 'slack_rate_limited';
    if (result.channels.some(c => c.error && c.error !== 'slack_rate_limited') || result.thread_error ||
      result.incident_error || result.operator_error ||
      result.delivery_error && result.delivery_error !== 'slack_rate_limited')
      throw new Error('tick_partial_failure');
    console.log(JSON.stringify({ mode: result.mode, slack_writes: result.slack_writes,
      channels: result.channels.length,
      messages: result.channels.reduce((n, c) => n + c.messages, 0),
      recent_messages: result.channels.reduce((n, c) => n + c.recent_messages, 0),
      thread_pages: result.thread_pages, imported: result.imported, delivered: result.delivered,
      delivery_code: result.delivery_code, delivery_held: result.delivery_held,
      operator_held: result.operator_held, incident_held: result.incident_held,
      thread_rate_limited: result.thread_rate_limited,
      thread_deadline_reached: result.thread_deadline_reached,
      rate_limited: rateLimited,
      jev_calls: result.jev.calls, jev_input_tokens: result.jev.input_tokens,
      jev_errors: result.jev.errors, jev_status: result.jev.status }));
  }).catch(error => {
    // Never print response bodies, request data, Slack text, or raw exception stacks.
    console.error(`monitor_failed:${/^[a-z][a-z0-9_]*$/u.test(error.message) ? error.message : 'provider_failure'}`);
    process.exitCode = 1;
  });
}
