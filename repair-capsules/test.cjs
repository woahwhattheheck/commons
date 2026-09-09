'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const RC = require('./capsule.js');
const fixture = () => ({title:'A useful failure', environment:'Node demo', broken_state:'value=2', logs:'exit=1', known_good:'value=1', next_action:'Compare values', attempts:[], created_at:'2026-09-04T00:00:00Z'});

test('both synthetic demos complete export/open loop', async () => {
  for (const name of ['commons','command']) {
    const sealed=await RC.seal(RC.cleanFields(RC.demo(name)));
    const serialized=JSON.stringify(sealed,null,2)+'\n';
    assert(!serialized.includes('DEMO_ONLY_NOT_A_REAL'));
    const reopened=await RC.open(serialized);
    assert.equal(reopened.integrity,'MATCH');
    assert(reopened.body.provenance.includes('SYNTHETIC'));
    assert.equal(reopened.body.next_action,sealed.next_action);
    assert(RC.diff(reopened.body.known_good,reopened.body.broken_state).rows.some(r=>r.kind==='added'));
  }
});
test('private literal redaction covers all evidence fields and attempts', () => {
  const input=fixture();
  for(const key of ['title','environment','broken_state','logs','known_good','next_action','provenance','created_at'])input[key]='private-value-123 useful';
  input.attempts=[{at:'private-value-123',action:'private-value-123',result:'private-value-123'}];
  const clean=RC.cleanFields(input,['private-value-123']);
  assert(!JSON.stringify(clean).includes('private-value-123'));
  assert.equal(clean.redaction.counts.literal,11);
});
const cases = [
  ['authorization','Authorization: Bearer veryprivate123','veryprivate123'],
  ['basic','Authorization: Basic dXNlcjpwYXNz','dXNlcjpwYXNz'],
  ['cookie','Cookie: a=some-cookie; b=another-cookie','some-cookie'],
  ['json','{"api_key":"some-secret", "safe":123}','some-secret'],
  ['quoted spaces',"password='several secret words'",'several secret words'],
  ['environment','AWS_SECRET_ACCESS_KEY=sample-value','sample-value'],
  ['query','https://example.invalid/?access_token=sample-query&mode=ok','sample-query'],
  ['CLI','run --api-key "sample-cli secret" --verbose','sample-cli secret'],
  ['URL','postgres://demo:sample-url@localhost/db','sample-url'],
  ['provider','sk-proj-abcdefghijklmnopqrst','abcdefghijklmnopqrst'],
  ['AWS identifier','AKIAABCDEFGHIJKLMNOP','AKIAABCDEFGHIJKLMNOP'],
  ['email','email=someone@example.invalid','someone@example.invalid'],
  ['Unix home','/home/someone/private.txt','/home/someone'],
  ['Windows home','C:\\Users\\someone\\private.txt','Users\\someone'],
  ['PEM','-----BEGIN RSA PRIVATE KEY-----\nPRIVATEBYTES\n-----END RSA PRIVATE KEY-----','PRIVATEBYTES'],
  ['truncated PEM','-----BEGIN PRIVATE KEY-----\nTRUNCATEDPRIVATEBYTES','TRUNCATEDPRIVATEBYTES']
];
for(const [name,value,secret] of cases)test('redaction: '+name,()=>{
  const result=RC.makeRedactor().redact(value);
  assert(!result.includes(secret),result);assert(result.includes('[REDACTED]'));
});
test('custom literals are not serialized as redaction configuration',()=>{
  const body=RC.cleanFields(fixture(),['not-in-any-input']);assert(!JSON.stringify(body).includes('not-in-any-input'));
});
test('benign data remains useful',()=>{
  assert.equal(RC.makeRedactor().redact('build=demo-a\nexit_code=1\nmode=read'), 'build=demo-a\nexit_code=1\nmode=read');
});
test('tampered evidence is inspectable with mismatch, never silently blessed',async()=>{
  const sealed=await RC.seal(RC.cleanFields(fixture()));sealed.next_action='Changed after export';
  const result=await RC.open(JSON.stringify(sealed));assert.equal(result.integrity,'MISMATCH');assert.equal(result.body.next_action,'Changed after export');
});
test('missing checksum remains inspectable with explicit status',async()=>{
  const result=await RC.open(JSON.stringify(RC.cleanFields(fixture())));assert.equal(result.integrity,'MISSING');
});
test('import redacts unsafe content after checking original integrity',async()=>{
  const unsafe={...RC.cleanFields(fixture()),logs:'password=unsafe-import'};
  const result=await RC.open(JSON.stringify(await RC.seal(unsafe)));
  assert.equal(result.integrity,'MATCH');assert(!result.body.logs.includes('unsafe-import'));
});
test('intervention history persists after redaction and export',async()=>{
  const body=fixture();body.attempts=[{at:'2026-09-04T12:00:00Z',action:'Changed path',result:'exit_code=0 token=history-secret'}];
  const reopened=await RC.open(JSON.stringify(await RC.seal(RC.cleanFields(body))));
  assert.equal(reopened.body.attempts.length,1);assert(reopened.body.attempts[0].result.includes('exit_code=0'));assert(!reopened.body.attempts[0].result.includes('history-secret'));
});
test('unknown baseline and intentionally empty baseline are different',()=>{
  assert.equal(RC.diff(null,'state').unknown,true);
  const diff=RC.diff('','state');assert.equal(diff.unknown,false);assert(diff.rows.some(r=>r.kind==='added'&&r.line==='state'));
});
test('diff reconstructs both original states',()=>{
  const a='before\nshared\nold\nafter',b='before\nnew\nshared\nafter';
  const delta=RC.diff(a,b);assert.equal(delta.rows.filter(r=>r.kind!=='added').map(r=>r.line).join('\n'),a);assert.equal(delta.rows.filter(r=>r.kind!=='removed').map(r=>r.line).join('\n'),b);
});
test('large diff uses documented coarse fallback',()=>{
  const a=Array.from({length:600},(_,i)=>'old'+i).join('\n'),b=Array.from({length:600},(_,i)=>'new'+i).join('\n');
  assert.equal(RC.diff(a,b).coarse,true);
});
test('maximum-line input does not overflow argument stack',()=>{
  assert(RC.diff('x','\n'.repeat(RC.MAX_TEXT)).rows.length>100000);
});
test('canonical checksum independent of object key insertion order',async()=>{
  assert.equal(await RC.checksum({b:2,a:1}),await RC.checksum({a:1,b:2}));
});
test('malformed input reports errors',async()=>{
  await assert.rejects(()=>RC.open('not json'),/valid JSON/);
  await assert.rejects(()=>RC.open('{"format":"other"}'),/Unsupported/);
  assert.throws(()=>RC.cleanFields({...fixture(),logs:{value:'not text'}}),/must be text/);
  assert.throws(()=>RC.cleanFields({...fixture(),title:''}),/title/);
  assert.throws(()=>RC.cleanFields({...fixture(),attempts:new Array(101).fill({})}),/100/);
});
test('oversize file and fields report errors',async()=>{
  await assert.rejects(()=>RC.open(' '.repeat(RC.MAX_FILE+1)),/smaller/);
  assert.throws(()=>RC.cleanFields({...fixture(),logs:'x'.repeat(RC.MAX_TEXT+1)}),/128 Ki/);
});
test('export size cannot exceed reopen byte limit',async()=>{
  const body=fixture();body.attempts=Array.from({length:12},()=>({at:'now',action:'a'.repeat(RC.MAX_TEXT),result:'b'.repeat(RC.MAX_TEXT)}));
  await assert.rejects(()=>RC.seal(RC.cleanFields(body)),/exceeds 2 MiB/);
});
test('capsule strings are data, not executed',async()=>{
  globalThis.capsuleTestExecuted=false;
  const body=fixture();body.next_action='globalThis.capsuleTestExecuted=true';
  await RC.open(JSON.stringify(await RC.seal(RC.cleanFields(body))));
  assert.equal(globalThis.capsuleTestExecuted,false);
});
