// Browser-loop contract with a deterministic clock. No camera, network or PLC.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('jetson/apps/edge_service/line_hmi.html', 'utf8');
const script = html.split('<script>')[1].split('</script>')[0].replace(/__MAINTENANCE_\w+__/g, '');

async function scenario(mode) {
  let now=0, counter=0, requests=0, inFlight=0, maxInFlight=0, statusCalls=0;
  const timers=new Map(), urls=new Set(), displayed=[], calls=[], elements=new Map();
  const later=(fn,ms=0)=>{const id=++counter;timers.set(id,{at:now+ms,fn});return id};
  const after=(ms,value)=>new Promise(resolve=>later(()=>resolve(value),ms));
  const element=id=>{
    if(!elements.has(id))elements.set(id,{
      dataset:{}, classList:{add(){},toggle(_,value){this.offline=value}},
      addEventListener(){},
      set src(value){this.value=value;later(()=>{displayed.push({at:now,id:this.dataset.frameId});this.onload?.()},5)}
    });
    return elements.get(id);
  };
  const sandbox={console,Date,performance:{now:()=>now},document:{hidden:false,getElementById:element},
    setTimeout:later,clearTimeout:id=>timers.delete(id),AbortSignal:{timeout:()=>null},
    URL:{createObjectURL:()=>{const id='blob:'+counter;urls.add(id);return id},revokeObjectURL:id=>urls.delete(id)},
    Image:class{decode(){return mode==='decode_failure'?Promise.reject(Error('bad image')):after(20)}},
    fetch:async(url,options)=>{
      if(url.includes('/line/view')){statusCalls++;return new Promise(()=>{})} // blocked status
      calls.push({at:now,headers:options.headers});requests++;inFlight++;maxInFlight=Math.max(maxInFlight,inFlight);
      const id=mode==='duplicates'?'frame-one':'frame-'+requests;
      await after(30);inFlight--;
      const same=options.headers['If-None-Match']===id;
      return {status:same?304:200,ok:true,headers:{has:()=>true,get:name=>name==='X-Frame-Id'||name==='ETag'?id:'100'},blob:()=>after(5,{})};
    }};
  vm.createContext(sandbox);vm.runInContext(script,sandbox);
  for(let steps=0;steps<1200&&now<3500;steps++) {
    for(let n=0;n<20;n++)await Promise.resolve();
    const entry=[...timers].sort((a,b)=>a[1].at-b[1].at)[0];
    if(!entry)break;
    now=entry[1].at;timers.delete(entry[0]);entry[1].fn();
    assert(urls.size<=2,'old object URLs accumulated');
  }
  assert.equal(statusCalls,1,'blocked status caused repeated heavy polls');
  assert.equal(maxInFlight,1,'overlapping image requests');
  assert(requests>5,'image loop waited for heavy status');
  if(mode==='normal'){
    assert(displayed.length>=30,'latest image target not reached under light I/O');
    assert.equal(new Set(displayed.map(f=>f.id)).size,displayed.length);
    for(let i=1;i<calls.length;i++)assert(calls[i].at-calls[i-1].at>=100);
  }
  if(mode==='duplicates'){
    assert.equal(displayed.length,1,'duplicate JPEG was displayed as a new frame');
    assert.equal(element('camera-wrap').classList.offline,true,'frozen frame stayed fresh');
  }
  if(mode==='decode_failure')assert.equal(displayed.length,0,'bad JPEG was displayed');
  console.log(mode, {requests,displayed:displayed.length,maxInFlight,statusCalls});
}
(async()=>{for(const mode of ['normal','duplicates','decode_failure'])await scenario(mode)})().catch(e=>{console.error(e);process.exitCode=1});
