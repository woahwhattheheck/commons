import test from 'node:test';
import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import { openState, runMonitor, serializeState } from './runner.mjs';

test('SQLite state round-trips through private text snapshot', () => {
  const opened = openState();
  opened.sqlite.prepare(`INSERT INTO slack_shipping_cursors
    (channel,latest_ts,initialized,updated_at) VALUES ('C0BU51F1PL3','123.456',1,123)`).run();
  const snapshot = serializeState(opened.sqlite);
  assert.equal(JSON.parse(snapshot).version, 2);
  opened.sqlite.close();
  const restored = openState(snapshot);
  assert.equal(restored.sqlite.prepare('SELECT latest_ts FROM slack_shipping_cursors').get().latest_ts, '123.456');
  assert.equal(serializeState(restored.sqlite), snapshot);
  restored.sqlite.close();
});

test('legacy v1 loads and a raw state over 390 KB compresses without dropping rows', () => {
  const legacy = JSON.stringify({ version: 1, tables: { slack_shipping_state: [
    { key: 'legacy', value: 'retained', updated_at: 1 }
  ] } });
  const opened = openState(legacy);
  opened.sqlite.prepare('INSERT INTO slack_shipping_state (key,value,updated_at) VALUES (?,?,?)')
    .run('large', 'A'.repeat(450_000), 2);
  const snapshot = serializeState(opened.sqlite);
  opened.sqlite.close();
  assert.ok(snapshot.length < 390_000);
  const restored = openState(snapshot);
  assert.equal(restored.sqlite.prepare('SELECT value FROM slack_shipping_state WHERE key=?')
    .get('large').value.length, 450_000);
  assert.equal(restored.sqlite.prepare('SELECT value FROM slack_shipping_state WHERE key=?')
    .get('legacy').value, 'retained');
  restored.sqlite.close();
});

test('compressed state exceeding the bounded decode limit is rejected', () => {
  const oversized = gzipSync(Buffer.alloc(32 * 1024 * 1024 + 1));
  const envelope = JSON.stringify({ version: 2, codec: 'gzip+base64',
    raw_sha256: '0'.repeat(64), data: oversized.toString('base64') });
  assert.throws(() => openState(envelope), /state_decompression_invalid/u);
});

test('public state repository stops before Slack or private content reads', async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async rawUrl => {
    requests.push(String(rawUrl));
    return Response.json({ private: false, visibility: 'public' });
  };
  try {
    await assert.rejects(runMonitor({ COMMONS_GITHUB_TOKEN: 'fixture', SLACK_BOT_TOKEN: 'fixture',
      TYPESAFE_API_KEY: 'fixture' }),
      /private_repository_required/u);
    assert.equal(requests.length, 1);
    assert.equal(new URL(requests[0]).pathname,
      '/repos/woahwhattheheck/commons-ship-enforcer');
  } finally { globalThis.fetch = originalFetch; }
});

test('runner bootstraps private state, imports durable notice, uses GET reads and CAS writes once', async () => {
  const originalFetch = globalThis.fetch;
  const env = { COMMONS_GITHUB_TOKEN: 'fixture-github', SLACK_BOT_TOKEN: 'fixture-slack', TYPESAFE_API_KEY: 'fixture-jev' };
  const statePath = '/repos/woahwhattheheck/commons-ship-enforcer/contents/paid-work/shipping-state.json';
  const noticeId = 'a'.repeat(64);
  const noticePath = `paid-work/shipping-operator-notices/${noticeId}.json`;
  const notice = { notice_id: noticeId, reason_code: 'git_publication_inspection_unavailable',
    tool_name: 'gh', operation_id: 'ship-test-1' };
  const files = new Map([[noticePath, JSON.stringify(notice)]]);
  const shas = new Map([[noticePath, '1'.repeat(40)]]);
  const writes = [];
  const posts = [];
  const requests = [];
  globalThis.fetch = async (rawUrl, options = {}) => {
    const url = new URL(String(rawUrl));
    requests.push({ path: url.pathname, method: options.method || 'GET' });
    if (url.hostname === 'api.github.com' && url.pathname ===
      '/repos/woahwhattheheck/commons-ship-enforcer')
      return Response.json({ private: true, visibility: 'private' });
    if (url.hostname === 'api.github.com' && url.pathname.includes('/contents/')) {
      const path = url.pathname.replace('/repos/woahwhattheheck/commons-ship-enforcer/contents/', '');
      if (!files.has(path)) return Response.json({ message: 'Not Found' }, { status: 404 });
      return Response.json({ type: 'file', sha: shas.get(path),
        content: Buffer.from(files.get(path)).toString('base64') });
    }
    if (url.hostname === 'api.github.com' && url.pathname.endsWith('/git/trees/main'))
      return Response.json({ truncated: false, tree: [{ type: 'blob', path: noticePath }] });
    if (url.hostname === 'account-publisher.tjlabs-publisher.workers.dev') {
      assert.equal(options.headers['User-Agent'], 'Commons-Shipping-Enforcer/1.0');
      const input = JSON.parse(options.body);
      assert.equal(input.operation, 'file.put');
      assert.equal(input.args.path, 'paid-work/shipping-state.json');
      assert.equal(input.args.sha, shas.get(input.args.path));
      files.set(input.args.path, Buffer.from(input.args.content, 'base64').toString('utf8'));
      shas.set(input.args.path, String(writes.length + 2).repeat(40));
      writes.push(input.operation_id);
      return Response.json({ allow: true, receipt: { commit: { oid: 'b'.repeat(40) } } });
    }
    if (url.hostname === 'slack.com') {
      const method = url.pathname.split('/').at(-1);
      if (method === 'conversations.history' || method === 'conversations.replies') {
        assert.equal(options.method, 'GET');
        return Response.json({ ok: true, messages: posts.map((p, i) => ({ ts: `${i + 1}.000001`,
          text: p.text, metadata: p.metadata })), response_metadata: { next_cursor: '' } });
      }
      if (method === 'chat.postMessage') {
        assert.equal(options.method, 'POST');
        posts.push(JSON.parse(options.body));
        return Response.json({ ok: true, ts: '1.000001' });
      }
    }
    throw new Error(`unexpected ${url.pathname}`);
  };
  try {
    const first = await runMonitor(env);
    assert.equal(first.imported, 1);
    assert.equal(first.delivered, 1);
    assert.equal(posts.length, 1);
    assert.equal(writes.length, 2); // initial private snapshot, then CAS update
    assert.ok(requests.filter(r => r.path.endsWith('/conversations.history')).every(r => r.method === 'GET'));
    const second = await runMonitor(env);
    assert.equal(second.imported, 0);
    assert.equal(posts.length, 1);
  } finally { globalThis.fetch = originalFetch; }
});
