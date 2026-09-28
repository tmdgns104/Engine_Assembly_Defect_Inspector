/* Same HMI and vision service. Session acknowledgement is not hand evidence. */
const labPanel=document.createElement('section');
labPanel.className='card';
labPanel.innerHTML=`<h2>실험 모드 · 실제 PLC 출력 없음</h2>
<p>손을 빼고 엔진이 정지한 상태에서 시험하세요. 정지는 손 없음의 증거가 아닙니다. 실험 PASS도 생산 승인이 아닙니다.</p>
<label><input type="checkbox" id="labAcknowledged">실험 모드임을 확인했습니다 (세션 시작 확인 / 프레임별 가시성 승인 아님)</label><br>
<button id="liveStart">Live 시작 / 복구</button><button id="liveStop">Live 중지</button>
<button id="manualMode">MANUAL 수동 모드</button><button id="labStart">자동 실험 시작</button><button id="labStop">자동 실험 / MOCK 중지</button>
<button id="reinspect">현재 엔진 재검사</button><button id="latestEvidence">최근 Evidence 보기</button>
<p id="labState"></p><p>LAB_AUTO: 검출된 진입마다 한 번 저장합니다. 계속 놓인 엔진은 재검사를 누르세요. 처음부터 검출되지 않는 엔진은 진입을 알 수 없으므로 MANUAL/MOCK로 미검출을 시험하세요.</p>
<h3>모의 PLC · 실제 PLC 미연결</h3><button id="mockMode">MOCK_PLC 시작</button>
<button id="requestOn">Inspection_Request ON</button><button id="requestOff">Inspection_Request OFF</button><button id="mockResync">Request OFF 확인 후 재동기화</button>
<pre id="plcState"></pre><p>Jetson_Result: 현재 계약: False=OK(PASS), True=NG(FAIL/REVIEW/ERROR). Production AUTO 화면에서 시험하세요. 과거 LAB 기록의 반대 극성은 당시 기록입니다.</p>
<p id="performance"></p>
<details><summary>MOCK 오류 시험 (실제 통신 없음)</summary><button data-lab-fault="result_fail">다음 Result 쓰기 실패</button><button data-lab-fault="done_fail">다음 Done 쓰기 실패</button><button data-lab-fault="done_unknown">다음 Done 응답 불명확</button><button data-lab-fault="disconnect">모의 연결 끊기</button><button data-lab-fault="reconnect">모의 재연결</button></details>`;
document.querySelector('main').insertBefore(labPanel,document.querySelector('.grid'));
let lastLabInspection=null, lastPublication=null;
const labStates={STOPPED:'중지',WAIT_PRODUCT:'엔진 진입 대기',WAIT_STABLE:'정지·Pose 확인 대기 (최대 8초)',INSPECTING:'실제 fresh 3프레임 검사 중',RESULT_HOLD:'결과 보존',WAIT_PRODUCT_EXIT:'엔진 이탈 대기',RESYNC:'재동기화 필요 / 유효한 Request OFF 확인',ARMED:'Request 상승 에지 대기',WAIT_REQUEST_CLEAR:'Done 유지 · Request OFF 대기 (최대 20초)'};
async function labCommand(action,body={}){
  try{const value=await api('lab/'+action,body);message('실험 제어: '+(labStates[value.state]||value.state));return value;}
  catch(error){message(error.message);return null;}
}
async function chooseLab(mode){
  const value=await labCommand('mode',{mode,confirmed:el('labAcknowledged').checked});
  if(value)el('labAcknowledged').checked=false;
}
function renderLab(status){
  const lab=status.lab;if(!lab)return;
  el('labState').textContent=`${lab.source_mode} · ${labStates[lab.state]||lab.state} · ${lab.reason||''} · 사람 수용: PENDING · 실제 출력: 비활성`;
  const g=lab.mock,p=lab.publication;
  const perf=status.performance||{},timing=perf.latest_inspection_timing;
  el('performance').textContent=`카메라 센서 FPS: 미측정 / 서비스 처리 프레임: ${perf.processed_preview_fps?.toFixed(2)||'-'} FPS (${perf.processed_preview_samples||0}장) / HMI 조회 주기: 750ms / 최근 검사 완료: ${timing?(timing.request_to_durable_result_ms/1000).toFixed(2)+'초 · '+timing.inspection_id:'없음'}`;
  el('plcState').textContent=`MOCK ${g.connected?'연결':'읽기 실패'} / Request=${g.Inspection_Request} / Result=${g.Jetson_Result} / Done=${g.Jetson_Done}\n모의 전송: ${p.publication_status||'없음'} / vision=${p.vision_decision||'-'} / 검사=${p.inspection_id||'-'}`;
  el('inspect').disabled=el('inspect').disabled||lab.source_mode!=='MANUAL';
  el('calibrate').disabled=el('calibrate').disabled||lab.source_mode!=='MANUAL';
  el('reinspect').disabled=!!status.active_inspection_id||lab.source_mode==='MOCK_PLC'||!status.ready;
  for(const id of ['requestOn','requestOff','mockResync'])el(id).disabled=status.production_enabled||lab.source_mode!=='MOCK_PLC';
  if(status.production_enabled){el('mockMode').textContent='Production MOCK 화면 열기';el('mockMode').onclick=()=>location.href='/auto';el('plcState').textContent='현재 MOCK 값은 Production AUTO 화면에서 확인하세요.';for(const button of document.querySelectorAll('[data-lab-fault]'))button.disabled=true;}
  if(lab.latest_inspection_id && lab.latest_inspection_id!==lastLabInspection){
    lastLabInspection=lab.latest_inspection_id;show(lastLabInspection).then(history).catch(e=>message(e.message));
  }
  const publication=JSON.stringify(p);
  if(publication!==lastPublication){
    lastPublication=publication;
    if(p.inspection_id&&selected?.inspection_id===p.inspection_id)show(p.inspection_id).catch(e=>message(e.message));
  }
}
function renderExperiment(detail){
  const result=detail.result,mode=detail.request.source_mode||'MANUAL';
  if(mode!=='MANUAL'){
    el('record').textContent+=` / 실험 ${mode} / HUMAN ACCEPTANCE: PENDING / 실제 출력 없음`;
    const p=detail.production_publication||detail.lab_publication;
    el('reason').textContent+=` · 모의 전송: ${p?.publication_status||'기록 없음/처리 대기'} (비전 판정과 별개)`;
  }
}
el('labStart').onclick=()=>chooseLab('LAB_AUTO');
el('mockMode').onclick=()=>chooseLab('MOCK_PLC');
el('manualMode').onclick=()=>chooseLab('MANUAL');
el('labStop').onclick=()=>labCommand('stop');
el('reinspect').onclick=()=>current?.lab?.source_mode==='LAB_AUTO'?labCommand('reinspect'):submit('inspect');
el('requestOn').onclick=()=>labCommand('request',{value:true});
el('requestOff').onclick=()=>labCommand('request',{value:false});
el('mockResync').onclick=()=>labCommand('resync');
el('latestEvidence').onclick=async()=>{try{const rows=await api('inspections?limit=1');if(rows.length)await show(rows[0].inspection_id);}catch(e){message(e.message);}};
for(const [id,action] of [['liveStart','start'],['liveStop','stop']])el(id).onclick=async()=>{try{message(JSON.stringify(await api('live/'+action,{})));}catch(e){message(e.message);}};
for(const button of document.querySelectorAll('[data-lab-fault]'))button.onclick=()=>labCommand('fault',{kind:button.dataset.labFault});
el('live').onerror=()=>{el('live').removeAttribute('src');el('camera').textContent='현재 프레임 수신 실패 · 이전 영상을 현재 Live로 표시하지 않습니다.';};
