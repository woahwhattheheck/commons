'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const nav = require('./review_navigation.js');
const R = 'd'.repeat(64);
function report() { return {receipt_sha256: R, synthetic_demo: true, assessment_matrix: [{group:'ESS',dimension:'software_development',source_ids:['synthetic-ess-software_development']},{group:'RIS',dimension:'security',source_ids:['shared']} ]}; }
function packet() { return nav.validatePacket(nav.syntheticPacket(), report()); }
const record = () => packet().records[2];
const route = r => nav.parseRoute(nav.routeFor(R, r));
for (const id of ['COMMENT-SYN-128/é + #1', '中 / ? = & # % +', ' a ', 'é', 'e\u0301', '<tag>"quotes"', 'NA', '0']) {
  test(`exact round trip ${JSON.stringify(id)}`, () => { const r={...record(),id}; assert.deepEqual(nav.identity(nav.parseRoute(nav.routeFor(R,r))), nav.identity(r)); });
}
test('normalization never coalesces case or composed Unicode', () => {assert.notEqual(nav.key({...record(),id:'é'}),nav.key({...record(),id:'e\u0301'}));assert.notEqual(nav.key({...record(),id:'ID'}),nav.key({...record(),id:'id'}));});
test('unrelated fragments are ignored',()=>{assert.equal(nav.parseRoute('#detail-heading'),null);assert.equal(nav.parseRoute(''),null);});
for (const suffix of ['&id=other','&extra=bad']) test(`rejects invalid route ${suffix}`,()=>assert.throws(()=>nav.parseRoute(nav.routeFor(R,record())+suffix)));
for (const changed of ['review=v2', 'review=v1&receipt=%XX', 'review=v1&receipt=%ED%A0%80', 'review=v1&id=missing']) test(`rejects malformed ${changed}`,()=>assert.throws(()=>nav.parseRoute('#'+changed)));
test('receipt is exact lower hexadecimal',()=>assert.throws(()=>nav.routeFor('D'.repeat(64),record()),/receipt/));
test('rejects invalid kind and malformed identity',()=>{for (const id of ['', '\u0000', '\ud800']) assert.throws(()=>nav.routeFor(R,{...record(),id}));assert.throws(()=>nav.identity({...record(),kind:'cell'}));});
test('link pending until report imported',()=>assert.equal(nav.resolve(route(record()),null,null).status,'WAITING_FOR_REPORT'));
test('report mismatch never substitutes a record',()=>assert.equal(nav.resolve(route(record()),{...report(),receipt_sha256:'a'.repeat(64)},packet()).status,'REPORT_MISMATCH'));
test('records remain pending after report import',()=>assert.equal(nav.resolve(route(record()),report(),null).status,'WAITING_FOR_RECORDS'));
test('exact record is found',()=>assert.equal(nav.resolve(route(record()),report(),packet()).record.id,record().id));
test('missing revision lists alternatives without substituting',()=>{const r=nav.resolve(route({...record(),revision:'v2'}),report(),packet()); assert.equal(r.status,'MISSING_RECORD');assert.equal(r.candidates.length,1);assert.equal(r.candidates[0].revision,'example-v1');});
test('duplicate exact identities remain ambiguous',()=>{const p=packet();p.records.push(structuredClone(p.records[2]));assert.equal(nav.resolve(route(record()),report(),p).status,'AMBIGUOUS_RECORD');});
test('same spelling in another origin is not ambiguous',()=>{const p=packet();p.records.push({...record(),origin:'elsewhere'});assert.equal(nav.resolve(route(record()),report(),p).status,'FOUND');});
test('source references support multiple cells without source duplication',()=>{const r=report();r.assessment_matrix[1].source_ids.push('synthetic-ess-software_development');const s=nav.sourceRecords(r);assert.equal(s.length,2);assert.equal(s[0].cell_keys.length,2);});
test('comment-to-recommendation-to-finding-to-source reaches actual cell',()=>assert.deepEqual(nav.relatedCells(record(),report(),packet()),['ESS|software_development']));
test('cycles do not recurse forever or invent cells',()=>{const p=packet();p.records[0].references=[nav.identity(p.records[2])];assert.deepEqual(nav.relatedCells(p.records[2],report(),p),[]);});
test('ambiguous and missing graph edges never resolve implicitly',()=>{const p=packet();p.records.push(structuredClone(p.records[0]));assert.deepEqual(nav.relatedCells(p.records[2],report(),p),[]);p.records.pop();p.records[0].references[0].id='missing';assert.deepEqual(nav.relatedCells(p.records[2],report(),p),[]);});
test('packet import requires matching report',()=>{assert.throws(()=>nav.validatePacket(nav.syntheticPacket(),null),/matching/);assert.throws(()=>nav.validatePacket(nav.syntheticPacket(),{...report(),receipt_sha256:'a'.repeat(64)}),/MISMATCH/);});
test('unvalidated stale packet is excluded',()=>{const p=packet();p.report_receipt_sha256='a'.repeat(64);assert.equal(nav.catalog(report(),p).records.length,2);});
test('records cannot forge compiler source membership',()=>{const p=packet();p.records[0].origin='compiler-report';assert.throws(()=>nav.validatePacket(p,report()),/reserved/);});
test('invalid cell and absent synthetic declaration are refused',()=>{let p=packet();p.records[0].cell_keys=['not|real'];assert.throws(()=>nav.validatePacket(p,report()),/cell_keys/);p=packet();delete p.records[0].synthetic;assert.throws(()=>nav.validatePacket(p,report()),/synthetic/);});
test('extension fields and unknowns survive and inputs are not mutated',()=>{const p=nav.syntheticPacket();p.records[1].extensions.extra={'null':null,'empty':'','NA':'NA'};const before=JSON.stringify(p);const q=nav.validatePacket(p,report());q.records[1].extensions.extra.empty='changed';assert.equal(JSON.stringify(p),before);assert.equal(q.records[1].extensions.effort,null);});
test('guide is deterministic and all records remain represented',()=>{const a=nav.guideHTML(report(),packet());assert.equal(a,nav.guideHTML(report(),packet()));assert.equal((a.match(/<section /g)||[]).length,5);});
test('guide escapes text and never promotes unresolved refs to links',()=>{const p=packet();p.records[0].text='<b>literal & only</b>';p.records[0].references[0].id='missing';const s=nav.guideHTML(report(),p);assert.ok(s.includes('&lt;b&gt;literal &amp; only&lt;/b&gt;'));assert.ok(s.includes('MISSING'));assert.ok(!s.includes('<b>literal'));});
test('guide duplicate identities have distinct anchors and diagnose ambiguity',()=>{const p=packet();p.records.push(structuredClone(p.records[0]));const s=nav.guideHTML(report(),p);assert.ok(s.includes('AMBIGUOUS'));const ids=[...s.matchAll(/<section id="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length);});
test('source record text does not claim the source document is present',()=>assert.match(nav.sourceRecords(report())[0].text,/does not contain the source document/));
test('identical IDs of different kinds remain separate',()=>{const p=packet();p.records.push({...record(),kind:'finding'});assert.equal(nav.resolve(route(record()),report(),p).status,'FOUND');});
test('no report means no guide',()=>assert.throws(()=>nav.guideHTML(null,null),/No report/));

test('unrepresentable extension numbers are refused rather than rounded to null',()=>{for (const number of [Infinity,NaN,-0,9007199254740992]) {const p=packet();p.records[0].extensions.number=number;assert.throws(()=>nav.validatePacket(p,report()),/preserved safely/);}});
