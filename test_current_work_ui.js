'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ui = require('./current_work_ui.js');
const SHA = 'a'.repeat(40);
const item = (kind = 'BUILDABLE', paths = ['host/example.py']) => ({id:'example-work-01', title:'Example work', kind, claimed_paths:paths});
const snapshot = () => ({sha:SHA, cache:new Map()});
const response = (status, data) => ({ok:status >= 200 && status < 300, status, json:async () => data});
const catalog = {schema:'commons-current-work-v1',items:[{...item(),title:'Café — current work'}]};
function sourceFetch(c = catalog) {
  const calls=[];
  return {calls, fetch:async (url, options) => {
    calls.push({url, options});
    if (url.endsWith('/git/ref/heads/main')) return response(200,{object:{sha:SHA}});
    return response(200,{encoding:'base64',content:Buffer.from(JSON.stringify(c),'utf8').toString('base64')});
  }};
}
test('page wires the real viewer while retaining source and no-script roads', () => {
  const html=fs.readFileSync(path.join(__dirname,'current-work.html'),'utf8');
  for(const id of ['current-work-viewer','cw-items','cw-search','cw-kind','cw-refresh','cw-source','cw-count']) assert.match(html,new RegExp(`id="${id}"`));
  assert.match(html,/current_work_ui\.js[^>]+defer/);
  assert.match(html,/<noscript>[\s\S]*ground\/CURRENT_WORK.json/);
  assert.match(html,/HTTP is not the computer\. Device pins stay pinned\./);
});
test('loads UTF-8 data from one official-main SHA, never an unpinned ledger', async () => {
  const source=sourceFetch(); const result=await ui.loadSnapshot(source.fetch);
  assert.equal(result.sha,SHA); assert.equal(result.items[0].title,'Café — current work');
  assert.equal(source.calls.length,2);
  assert.ok(source.calls[1].url.endsWith(`CURRENT_WORK.json?ref=${SHA}`));
  assert.equal(source.calls[1].options.cache,'no-store');
});
test('malformed main reference cannot produce a ledger observation', async () => {
  await assert.rejects(ui.loadSnapshot(async()=>response(200,{object:{sha:'main'}})),/official-main SHA/);
});
test('unavailable and malformed ledgers are errors rather than empty queues', async () => {
  await assert.rejects(ui.loadSnapshot(async()=>response(403,{})),/HTTP 403/);
  await assert.rejects(ui.loadSnapshot(sourceFetch({schema:'wrong',items:[]}).fetch),/schema/);
  await assert.rejects(ui.loadSnapshot(sourceFetch({schema:catalog.schema,items:{}}).fetch),/items/);
});
test('all kind distinctions, empty paths and malformed rows remain visible', () => {
  assert.equal(ui.initialStatus(item()),'UNVERIFIED');
  assert.equal(ui.initialStatus(item('BUILDABLE',[])),'OPEN');
  assert.equal(ui.initialStatus(item('OWNER_PLATFORM',[])),'NEEDS_OWNER');
  assert.equal(ui.initialStatus(item('DEVICE_PINNED')),'PINNED');
  for(const bad of [null,[],4,{kind:'WRONG'},item('BUILDABLE','path'),item('BUILDABLE',[null])]) assert.equal(ui.initialStatus(bad),'INVALID ROW');
});
test('pinned and pathless rows issue no requests and never close vacuously', async () => {
  const never=()=>assert.fail('unexpected request');
  assert.equal((await ui.verifyItem(item('DEVICE_PINNED'),snapshot(),never)).status,'PINNED');
  assert.equal((await ui.verifyItem(item('OWNER_PLATFORM',[]),snapshot(),never)).status,'NEEDS_OWNER');
  assert.equal((await ui.verifyItem(item('BUILDABLE',[]),snapshot(),never)).status,'OPEN');
});
test('every claimed path must exist at the same SHA before closure', async () => {
  const calls=[];
  const result=await ui.verifyItem(item('BUILDABLE',['a.py','dir/café #1.py']),snapshot(),async url=>{calls.push(url);return response(200);});
  assert.equal(result.status,'CLOSED'); assert.deepEqual(result.missing,[]);
  assert.equal(calls.length,2); assert.ok(calls.every(url=>url.endsWith(`?ref=${SHA}`)));
  assert.ok(calls[1].includes('caf%C3%A9%20%231.py'));
});
test('missing paths preserve OPEN versus NEEDS_OWNER', async () => {
  for(const [kind,status] of [['BUILDABLE','OPEN'],['OWNER_PLATFORM','NEEDS_OWNER']]) {
    const result=await ui.verifyItem(item(kind,['exists','missing']),snapshot(),async url=>response(url.includes('/missing?')?404:200));
    assert.equal(result.status,status); assert.deepEqual(result.missing,['missing']);
  }
});
test('rate limits, server errors and network failures never become missing paths', async () => {
  for(const status of [403,429,500]) await assert.rejects(ui.verifyItem(item(),snapshot(),async()=>response(status)),new RegExp(`HTTP ${status}`));
  await assert.rejects(ui.verifyItem(item(),snapshot(),async()=>{throw new Error('offline');}),/offline/);
});
test('successful checks share a snapshot cache; failed requests are retryable', async () => {
  const snap=snapshot(); let calls=0;
  const fetcher=async()=>{calls++;return response(200);};
  await ui.verifyItem(item(),snap,fetcher); await ui.verifyItem(item(),snap,fetcher);
  assert.equal(calls,1);
  const retry=snapshot();
  await assert.rejects(ui.verifyItem(item(),retry,async()=>response(429)),/429/);
  assert.equal((await ui.verifyItem(item(),retry,fetcher)).status,'CLOSED');
  assert.equal(calls,2);
});
test('invalid snapshots cannot be used to verify claimed paths', async () => {
  await assert.rejects(ui.verifyItem(item(),{sha:'main',cache:new Map()},async()=>response(200)),/official-main snapshot/);
});
test('source links stay on the repository and encode unsafe path text', () => {
  const url=ui.sourceURL(SHA,'dir/<img>#example.py');
  assert.ok(url.startsWith(`https://github.com/woahwhattheheck/commons/blob/${SHA}/`));
  assert.ok(url.includes('%3Cimg%3E%23example.py'));
});
