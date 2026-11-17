const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const crypto=require('node:crypto');
const scene=require('../web/scene.js');
const frame={time:0,meshes:[{id:'tetra',positions:[[0,0,0],[1,0,0],[0,2,0],[0,0,3]],faces:[[0,1,2],[0,3,1]],color:[.2,.4,.8],opacity:1}],lines:[],points:[],metrics:[]};
assert.equal(scene.validateFrame(frame),4);
const bad=structuredClone(frame);bad.meshes[0].faces[0][2]=20;
assert.throws(()=>scene.validateFrame(bad),/connectivity/);
bad.meshes[0].faces=[[0,1,2]];bad.meshes[0].positions[0][0]=Infinity;
assert.throws(()=>scene.validateFrame(bad),/position/);
const b=scene.bounds({frames:[frame]});assert.deepEqual(b.center,[.5,1,1.5]);
for(const p of [[1,2,3],[-3,2,1],[0,0,1]]){
 const projected=scene.project(p);
 assert.ok(Math.abs(Math.hypot(...p)-Math.hypot(...projected))<1e-12,'Orthonormal projection retains geometric scale');
}
// Run the actual native-commit queue with a controlled stale parse.
const source=fs.readFileSync(require.resolve('../web/app.js'),'utf8');
const code=source.slice(source.indexOf('function commitWorld('),source.indexOf('function drawProjection('));
(async()=>{
 let release;const gate=new Promise(r=>release=r),commits=[];
 const state={queue:Promise.resolve(),revision:1,projection:false,packet:{},nativeFailed:false};
 const nodes=new Map();const $=id=>{if(!nodes.has(id))nodes.set(id,{});return nodes.get(id);};
 const browser={async createX3DFromString(xml){if(xml==='old')await gate;return xml;},async replaceWorld(s){commits.push(s);}};
 const ctx=vm.createContext({state,$,nativeBrowser:async()=>browser,drawProjection(){throw Error('Unexpected fallback');}});
 vm.runInContext(code,ctx);
 const first=ctx.commitWorld('old',0,1);await new Promise(r=>setImmediate(r));
 state.revision=2;const next=ctx.commitWorld('new',1,2);release();
 assert.equal(await first,false);assert.equal(await next,true);assert.deepEqual(commits,['new']);
 // Repeated imported identities replace the UI record, never append stale bytes.
 const importCode=source.slice(source.indexOf('async function importFile('),source.indexOf("$('importCloud').onclick"));
 const records=[{id:'same-import',title:'First input',kind:'tensor',frames:1},{id:'same-import',title:'New input',kind:'tensor',frames:1}];
 const packets=records.map(r=>JSON.stringify({id:r.id,title:r.title}));let call=0;
 const imported={local:true,bank:{cases:[]}};const chosen=[];const elements=new Map();
 const get=id=>{if(!elements.has(id))elements.set(id,{replaceChildren(){}});return elements.get(id);};
 const context=vm.createContext({state:imported,$:get,TextEncoder,stop(){},toast(){},error(e){throw Error(e);},
  el(){return {};},chooseCase:async id=>chosen.push(id),digest:async b=>crypto.createHash('sha256').update(b).digest('hex'),
  fetch:async()=>{const i=call++;return {ok:true,json:async()=>({packet_text:packets[i],record:{...records[i],stored_sha256:crypto.createHash('sha256').update(packets[i]).digest('hex')},message:'Imported'})};}});
 vm.runInContext(importCode,context);
 const file={arrayBuffer:async()=>new ArrayBuffer(0)};
 await context.importFile(file,'/api/import-cloud');await context.importFile(file,'/api/import-cloud');
 assert.equal(imported.bank.cases.length,1);assert.equal(imported.bank.cases[0].title,'New input');
 assert.deepEqual(chosen,['same-import','same-import']);
 console.log('PASS frame geometry refusals, projection scale, and obsolete native parse cannot replace a fresh frame');
 console.log('PASS repeated import replaces the current identity and retains exact canonical packet bytes');
})().catch(e=>{console.error(e);process.exitCode=1;});
