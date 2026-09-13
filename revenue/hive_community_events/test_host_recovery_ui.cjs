'use strict';
const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
function functionSource(name){
  const marker=`function ${name}(`;const start=html.indexOf(marker);assert.notEqual(start,-1,`missing ${name}`);
  const open=html.indexOf('{',start);let depth=0;let quote='';let escaped=false;
  for(let i=open;i<html.length;i++){
    const ch=html[i];
    if(quote){if(escaped)escaped=false;else if(ch==='\\')escaped=true;else if(ch===quote)quote='';continue;}
    if(ch==='\''||ch==='"'||ch==='`'){quote=ch;continue;}
    if(ch==='{')depth++;else if(ch==='}'&&--depth===0)return html.slice(start,i+1);
  }
  throw new Error(`unterminated ${name}`);
}
function harness(localStorage){
  const context={localStorage,hostRefs:{}};vm.createContext(context);
  vm.runInContext([functionSource('storedHost'),functionSource('rememberHost'),functionSource('hostPersistenceMessage')].join('\n'),context);
  return context;
}
test('successful host recovery persistence is verified by readback',()=>{
  const values=new Map();const storage={setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k)||null};const h=harness(storage);
  assert.equal(h.rememberHost('evt','fresh-key'),true);assert.equal(h.storedHost('evt'),'fresh-key');
  assert.match(h.hostPersistenceMessage('create',true),/saved in this browser/);
});
test('storage failure keeps fresh verified key for this tab and warns about reload loss',()=>{
  const storage={getItem:()=> 'stale-key',setItem:()=>{throw new Error('blocked');}};const h=harness(storage);
  assert.equal(h.rememberHost('evt','fresh-key'),false);assert.equal(h.storedHost('evt'),'fresh-key');
  const message=h.hostPersistenceMessage('restore',false);assert.match(message,/tab only/i);assert.match(message,/copy/i);assert.match(message,/reload/i);
});
test('silent storage readback mismatch is not reported as durable persistence',()=>{
  const storage={setItem:()=>{},getItem:()=> 'different-key'};const h=harness(storage);
  assert.equal(h.rememberHost('evt','fresh-key'),false);assert.equal(h.storedHost('evt'),'fresh-key');
});
test('create and restore notices consume the explicit persistence result',()=>{
  assert.match(html,/const persisted=rememberHost\(data\.id,key\)/);assert.match(html,/hostPersistenceMessage\('restore',persisted\)/);
  assert.match(html,/const persisted=rememberHost\(event\.id,event\.host_key\)/);assert.match(html,/hostPersistenceMessage\('create',persisted\)/);
  assert.doesNotMatch(html,/notice\('Event created\. The host recovery key is saved in this browser/);
});
