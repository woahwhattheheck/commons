"use strict";
const assert = require("assert");
const api = require("../tools/two-source-reconciler.js");

function fixture() {
  return {
    fields: ["a", "b", "c"],
    left: [
      {rowId:"L1", key:"K1", values:{a:100,b:10,c:90}},
      {rowId:"L2", key:"K2", values:{a:200,b:20,c:180}},
      {rowId:"L3", key:"K3", values:{a:300,b:30,c:270}}
    ],
    right: [
      {rowId:"R1", key:"K1", values:{a:100,b:10,c:90}},
      {rowId:"R2", key:"K2", values:{a:200,b:20,c:180}},
      {rowId:"R3", key:"K3", values:{a:300,b:30,c:270}}
    ]
  };
}
function clone(v){ return JSON.parse(JSON.stringify(v)); }

(function exact(){ const out=api.reconcile(fixture()); assert.strictEqual(out.summary.match,3); assert.deepStrictEqual(out.totals.delta,{a:0,b:0,c:0}); })();
(function missingLeft(){ const f=fixture(); f.left.shift(); const r=api.reconcile(f).rows.find(x=>x.key==="K1"); assert.deepStrictEqual(r.issues,["MISSING_LEFT"]); })();
(function missingRight(){ const f=fixture(); f.right.pop(); const r=api.reconcile(f).rows.find(x=>x.key==="K3"); assert.deepStrictEqual(r.issues,["MISSING_RIGHT"]); })();
(function duplicate(){ const f=fixture(); const row=clone(f.right[0]); row.rowId="R4"; f.right.push(row); const r=api.reconcile(f).rows.find(x=>x.key==="K1"); assert(r.issues.includes("DUPLICATE_RIGHT")); })();
(function mismatch(){ const f=fixture(); f.right[1].values.b=25; const r=api.reconcile(f).rows.find(x=>x.key==="K2"); assert(r.issues.includes("MISMATCH:b")); assert.strictEqual(r.delta.b,-5); })();
(function deterministic(){ const f=fixture(); f.left.reverse(); f.right.reverse(); assert.deepStrictEqual(api.reconcile(f).rows.map(x=>x.key),["K1","K2","K3"]); })();
(function invalidInteger(){ const f=fixture(); f.left[0].values.a=1.5; assert.throws(()=>api.reconcile(f),/safe integer/); })();
(function duplicateField(){ const f=fixture(); f.fields=["a","a"]; assert.throws(()=>api.reconcile(f),/duplicate field/); })();

console.log("two-source reconciler: 8/8 tests passed");
