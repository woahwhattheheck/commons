'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {matches, init} = require('./paid-opportunities.js');
const html = fs.readFileSync(path.join(__dirname, 'paid-opportunities.html'), 'utf8');

function element(value = '') {
  return {value, hidden: false, textContent: '', handlers: {},
    addEventListener(event, handler) { this.handlers[event] = handler; },
    focus() { this.focused = true; }};
}
function fixture() {
  const cards = Array.from(html.matchAll(/<li data-channel="([^"]+)" data-keywords="([^"]+)">([\s\S]*?)<\/li>/g), match => {
    const card = element();
    card.textContent = match[3].replace(/<[^>]*>/g, ' ');
    card.getAttribute = name => name === 'data-channel' ? match[1] : name === 'data-keywords' ? match[2] : null;
    return card;
  });
  const nodes = {};
  for (const id of ['channel-search', 'channel-query', 'channel-clear', 'channel-count', 'channel-empty', 'channel-directory']) nodes[id] = element();
  nodes['channel-search'].hidden = true;
  nodes['channel-empty'].hidden = true;
  nodes['channel-directory'].querySelectorAll = () => cards;
  return {nodes, cards, doc: {getElementById: id => nodes[id] || null}};
}
function shown(f) { return f.cards.filter(card => !card.hidden).map(card => card.getAttribute('data-channel')); }

test('empty, missing and whitespace queries show all text', () => {
  for (const query of ['', ' \t\n ', null, undefined]) assert.equal(matches('any channel', query), true);
});
test('case, full-width text, hashtags, hyphens and underscores normalize', () => {
  assert.equal(matches('#bug-bounty', 'BUG bounty'), true);
  assert.equal(matches('#bug-bounty', 'ＢＵＧ_bounty'), true);
});
test('all terms must match; punctuation is literal, not a regular expression', () => {
  assert.equal(matches('connector API compatibility', 'API connector'), true);
  assert.equal(matches('connector API compatibility', 'API university'), false);
  assert.equal(matches('API compatibility', '.*'), false);
});
test('enhancement starts with all eight real static cards', () => {
  const f = fixture();
  assert.equal(f.cards.length, 8);
  assert.equal(init(f.doc), true);
  assert.equal(shown(f).length, 8);
  assert.equal(f.nodes['channel-count'].textContent, '8 of 8 channels shown.');
  assert.equal(f.nodes['channel-search'].hidden, false);
});
test('input searches the real descriptions and channel IDs', () => {
  const f = fixture(); init(f.doc);
  for (const [query, expected] of [['  InTeGrAtIoNs ', 'C0C01AXLCGZ'], ['university', 'C0BUY3EKMSB'], ['c0c0344tf7w', 'C0C0344TF7W'], ['bug bounty', 'C0BVANHNB26']]) {
    f.nodes['channel-query'].value = query;
    f.nodes['channel-query'].handlers.input();
    assert.deepEqual(shown(f), [expected]);
    assert.equal(f.nodes['channel-empty'].hidden, true);
  }
});
test('no match announces zero; clear restores links and keyboard focus', () => {
  const f = fixture(); init(f.doc);
  f.nodes['channel-query'].value = '<script>not-a-channel</script>';
  f.nodes['channel-query'].handlers.input();
  assert.equal(shown(f).length, 0);
  assert.equal(f.nodes['channel-empty'].hidden, false);
  assert.equal(f.nodes['channel-count'].textContent, '0 of 8 channels shown.');
  f.nodes['channel-clear'].handlers.click();
  assert.equal(f.nodes['channel-query'].value, '');
  assert.equal(shown(f).length, 8);
  assert.equal(f.nodes['channel-empty'].hidden, true);
  assert.equal(f.nodes['channel-query'].focused, true);
});
test('Enter stays on the page rather than navigating or submitting a claim', () => {
  const f = fixture(); init(f.doc);
  f.nodes['channel-query'].value = 'math';
  let prevented = false;
  f.nodes['channel-search'].handlers.submit({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.deepEqual(shown(f), ['C0BV7KHRGF7']);
});
test('missing enhancement elements preserve the static links', () => {
  assert.equal(init(null), false);
  for (const id of Object.keys(fixture().nodes)) {
    const f = fixture(); delete f.nodes[id];
    assert.equal(init(f.doc), false);
    assert.equal(shown(f).length, 8);
    if (f.nodes['channel-search']) assert.equal(f.nodes['channel-search'].hidden, true);
  }
});
test('an empty directory does not expose nonfunctional search controls', () => {
  const f = fixture(); f.cards.length = 0;
  assert.equal(init(f.doc), false);
  assert.equal(f.nodes['channel-search'].hidden, true);
});
test('missing optional keywords do not hide a card with a matching description', () => {
  const f = fixture();
  f.cards[0].getAttribute = name => name === 'data-channel' ? 'C0BVANHNB26' : null;
  init(f.doc); f.nodes['channel-query'].value = 'bug'; f.nodes['channel-query'].handlers.input();
  assert.ok(shown(f).includes('C0BVANHNB26'));
});
