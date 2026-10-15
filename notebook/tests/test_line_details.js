// UI evidence uses saved fields, never a new decision or a reset on page load.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const script=fs.readFileSync('jetson/apps/edge_service/line_details.js','utf8');
const sandbox={};vm.createContext(sandbox);vm.runInContext(script,sandbox);
const summarize=vm.runInContext('LineDetails.summarize',sandbox);
const observations=[0,1,2].map(i=>({frame_id:'f'+i}));
const raw={state:'COMPLETE',result:{observations,slot_states:{pipe_left:'PRESENT',exhaust:'MISSING_CONFIRMED'}}};
const assembly={state:'COMPLETE',three_frames:{state:'FAIL_CANDIDATE'},frames:observations.map(o=>({...o,parts:{
  pipe_left:{valid:true,predicted_state:'SIDEWAYS'},exhaust:{valid:true,predicted_state:'MISSING'}}}))};
let s=summarize(raw,assembly,{});
assert.equal(s.rows[0].assembly,'SIDEWAYS');assert.equal(s.rows[2].presence,'MISSING_CONFIRMED');assert.equal(s.rows[2].assembly,'MISSING');
assembly.frames[1].parts.pipe_left.predicted_state='CORRECT';
assert.equal(summarize(raw,assembly,{}).rows[0].assembly,'CONFLICT');
assembly.frames[0].parts.exhaust.valid=false;
assert.equal(summarize(raw,assembly,{}).rows[2].assembly,'UNCERTAIN');
assembly.frames[1].frame_id='not-same-request';
assert.notEqual(summarize(raw,assembly,{}).rows[2].assembly,'MISSING');
const stopped=summarize({state:'COMPLETE',result:{observations:[]}},null,{source:'NO_ACTUAL_INSPECTION'});
assert.equal(stopped.noCapture,true);assert(stopped.rows.every(p=>p.assembly==='NOT_RUN'&&p.presence==='NOT_RUN'));
const rejected={state:'COMPLETE',frames:observations.map(o=>({...o,preprocessing:{status:'FAILED'},parts:{pipe_left:{valid:false,predicted_state:null}}}))};
assert(summarize(raw,rejected,{}).rows.every(p=>p.assembly==='NOT_RUN'));
assert(!script.includes('innerHTML'),'stored content must not be HTML');
assert(!script.includes('localStorage')&&!script.includes('sessionStorage'),'no persistent maintenance secret');
assert(!script.includes('Authorization')&&!script.includes('recovery-token'),'Reset must not require a software code');
assert(script.includes('confirmations:')&&script.includes('PHYSICAL_STOP'));
assert(!script.includes('automatic_arm')&&!script.includes('initial_arm'));
console.log('line evidence: missing / misassembly / conflicting frames / invalid evidence / no capture / unsafe rendering guards PASS');

async function recoveryUI(){
  const elements=new Map(),calls=[];
  const get=id=>{if(!elements.has(id))elements.set(id,{value:'',checked:false,disabled:false,
    textContent:'',showModal(){},close(){},addEventListener(name,fn){this[name]=fn}});return elements.get(id)};
  const ctx={document:{getElementById:get},AbortSignal:{timeout:()=>null},
    fetch:async(url,options={})=>{
      calls.push({url,options});return {ok:true,json:async()=>options.method==='POST'?{recovery_id:'receipt'}:
        {eligible:true,inspection_id:'a'.repeat(32)}};
    }};
  vm.createContext(ctx);vm.runInContext(script,ctx);vm.runInContext('LineDetails.init()',ctx);
  assert.equal(calls.length,0,'page load must not preflight or reset');
  get('recovery-open').onclick();for(let i=0;i<12;i++)await Promise.resolve();
  assert.equal(calls.length,1);assert.equal(calls.filter(c=>c.options.method==='POST').length,0,'opening dialog is not physical confirmation');
  assert.equal(get('recovery-submit').disabled,false);
  const first=get('recovery-submit').onclick();await get('recovery-submit').onclick();await first;
  assert.equal(calls.filter(c=>c.options.method==='POST').length,1,'double click created a second mutation');
  const posted=JSON.parse(calls[1].options.body);assert.equal(posted.identifier,'a'.repeat(32));
  assert.deepEqual(posted.confirmations,['PHYSICAL_STOP','PRODUCT_REMOVED_OR_HELD_OFF_LINE','CLOSE_CONTEXT_WITHOUT_RESULT']);
  assert.equal(calls[1].options.headers.Authorization,undefined);
  assert.equal(get('recovery-submit').disabled,true);
  console.log('reset UI: no page-load writes, physical-confirmation button, no code/token, single POST, no automatic retry PASS');
}
recoveryUI().catch(error=>{console.error(error);process.exitCode=1});
