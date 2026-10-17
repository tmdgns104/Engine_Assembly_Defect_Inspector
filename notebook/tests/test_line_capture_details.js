// Selected saved ERROR cannot borrow a later PASS or assembly reason.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={};vm.createContext(context);
vm.runInContext(fs.readFileSync('jetson/apps/edge_service/line_details.js','utf8'),context);
const summarize=vm.runInContext('LineDetails.summarize',context);
const raw={inspection_id:'error-id',state:'COMPLETE',result:{decision:'ERROR',reason_code:'DEADLINE_EXCEEDED',
  fresh_frame:{terminal_reason:'DEADLINE_EXCEEDED'},observations:[{frame_id:'diagnostic'}],
  stationary_capture:{candidate_count:11,rejected_count:11,discarded_stable_frames:0}},
  production_publication:{inspection_id:'error-id',event:'PLC_CYCLIC_COMPLETION_OBSERVED'}};
let s=summarize(raw,{reason:'POSE_FAILURE'},{decision:'ERROR',reason:'EXISTING_ERROR_ASSEMBLY_REVIEW'});
assert.equal(s.details.reason,'DEADLINE_EXCEEDED');assert.equal(s.details.diagnostic,true);
assert.equal(s.details.plcComplete,true);assert.equal(s.details.capture.candidate_count,11);
assert.equal(s.details.capture.continuity_reset_count,undefined,'missing old count must not become zero');
raw.production_publication.inspection_id='later-pass';
assert.equal(summarize(raw,null,null).details.plcComplete,false);
assert.equal(summarize({result:{}},null,{reason:'OTHER_REASON'}).details.reason,'상세 원인 미기록');
assert.equal(summarize({result:{decision:'PASS',reason_code:'ALL_REQUIRED_PARTS_PRESENT_3_FRAMES'}},null,null).details.diagnostic,false);
console.log('saved raw cause / diagnostic originals / ID-bound PLC completion / missing historical details PASS');
