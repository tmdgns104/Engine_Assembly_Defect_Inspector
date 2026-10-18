/* Saved evidence and exceptional recovery. Neither path starts an inspection. */
'use strict';
const LineDetails = (() => {
  const parts={pipe_left:'왼쪽 파이프',pipe_right:'오른쪽 파이프',exhaust:'은색 배기 부품',symbol:'문양 부품'};
  const states={CORRECT:'정상 방향',MISSING:'결품 검출',MISSING_CONFIRMED:'결품 확인',PRESENT:'존재 확인',
    REVERSED:'역방향 오조립',SIDEWAYS:'옆 방향 오조립',UPSIDE_DOWN:'뒤집힘 오조립',
    NOT_RUN:'미실행',NOT_EVALUATED:'미평가',UNCERTAIN:'판정 불확실',CONFLICT:'프레임 간 불일치'};
  const reasons={PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN:'이전 제품 이탈·새 제품 식별을 확인하지 못해 촬영하지 않았습니다.',
    PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN:'이전 실행의 제품 문맥이 남아 있습니다.',
    POSE_QUALITY_REJECTED:'몸체 정렬 기준을 통과하지 못해 부품 방향 분류를 실행하지 않았습니다.',
    NO_VALID_BOUND_RAW_FRAMES:'현재 요청과 연결된 유효 원본이 없습니다.',
    ENGINE_OR_HAND_MOTION:'검사 영상 사이 움직임이 확인됐습니다.',
    FRESH_STOPPED_NO_OUTPUT_CONTEXT_REQUIRED:'현장 STOP, Request OFF, Result/Done 0 및 신선한 PLC 연결이 필요합니다.',
    EXPLICIT_IDLE_OWNERS_REQUIRED:'카메라·검사·조립·저장 작업이 정상 유휴 상태여야 합니다.',
    OWNER_ERROR_BLOCKS_CONTEXT_RECOVERY:'카메라·검사기 오류가 남아 있습니다. 문맥 정리로 이 오류를 해제할 수 없습니다.',
    UNFINISHED_INSPECTION_BLOCKS_CONTEXT_RECOVERY:'실제 미완료 검사가 있습니다. 별도 중단 복구가 필요하며 이 버튼으로 지우지 않습니다.',
    CONTEXT_RECOVERY_ALREADY_RECORDED:'이 제품의 문맥은 이미 정리됐습니다. 다른 차단 원인을 확인하세요.',
    LATEST_PRODUCT_CONTEXT_REQUIRED:'정리할 과거 제품 문맥이 없거나 대상이 바뀌었습니다.',
    LOCAL_SAME_ORIGIN_RESET_REQUIRED:'Jetson의 현장 화면에서 Reset을 실행해 주세요. 다른 사이트의 요청은 허용하지 않습니다.',
    MAINTENANCE_RECOVERY_DISABLED:'현재 실행에서 유지보수 복구가 비활성 상태입니다.',
    PLC_CHANGED_DURING_CONTEXT_RECOVERY:'처리 중 PLC 상태가 바뀌어 복구를 취소했습니다.',
    JOURNAL_INTEGRITY_FAILED:'검사 원장 무결성 오류입니다. 재시험 전에 저장소 점검이 필요합니다.'};
  const byId=id=>document.getElementById(id);
  const label=value=>states[value]||value||'미실행';
  const explain=value=>reasons[value]||value||'기록 없음';
  const add=(parent,tag,text,className)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;parent.append(e);return e};
  const fixed=value=>Number.isFinite(value)?value.toFixed(2):'기록 없음';
  let selectedId=null,followLatest=true,loadedKey=null,loadGeneration=0,controller=null;
  let recovery=null,recoveryBusy=false;

  function summarize(raw,assembly,final){
    const observations=raw?.result?.observations||[];
    const frames=assembly?.frames||[];
    const noCapture=final?.source==='NO_ACTUAL_INSPECTION'||(!observations.length&&raw?.state==='COMPLETE');
    // Only recorded three-frame agreement can become an assembly part summary.
    const checkedPolicy=['BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1','BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2'].includes(final?.policy);
    const qualified=!checkedPolicy||['PASS','FAIL'].includes(final?.assembly_inspector);
    const agreement=qualified&&['PASS_CANDIDATE','FAIL_CANDIDATE'].includes(assembly?.three_frames?.state)
      &&frames.length===3&&new Set(frames.map(f=>f.frame_id)).size===3
      &&frames.every(f=>observations.some(o=>o.frame_id===f.frame_id));
    const rows=Object.entries(parts).map(([key,name])=>{
      const perFrame=frames.map(f=>f.parts?.[key]?.valid===true?f.parts[key].predicted_state:null);
      let assemblyState='NOT_RUN';
      if(perFrame.some(Boolean))assemblyState=agreement&&perFrame.every(v=>v&&v===perFrame[0])?perFrame[0]:
        new Set(perFrame.filter(Boolean)).size>1?'CONFLICT':'UNCERTAIN';
      return {key,name,presence:noCapture?'NOT_RUN':raw?.result?.slot_states?.[key]||'NOT_EVALUATED',assembly:assemblyState,perFrame};
    });
    const basic=raw?.result||{},capture=basic.stationary_capture,fresh=basic.fresh_frame;
    const diagnostic=basic.decision==='ERROR'&&Boolean(fresh?.terminal_reason);
    const publication=raw?.production_publication;
    const samePublication=Boolean(raw?.inspection_id&&publication?.inspection_id===raw.inspection_id);
    const details={decision:basic.decision||'미기록',reason:basic.reason_code||basic.reason||'상세 원인 미기록',
      terminal:fresh?.terminal_reason||null,capture,diagnostic,
      plcComplete:samePublication&&publication.event==='PLC_CYCLIC_COMPLETION_OBSERVED'};
    return {observations,frames,rows,noCapture,details};
  }

  function image(parent,title,url){
    const fig=add(parent,'figure'),img=add(fig,'img');img.alt=title;img.loading='lazy';img.src=url;
    add(fig,'figcaption',title);img.onerror=()=>{img.hidden=true;add(fig,'p','저장 이미지를 불러오지 못했습니다.')};
  }

  function presenceLabel(state){
    return {PRESENT:'미결합 없음 · 부품 확인',MISSING_CONFIRMED:'미결합 · 부품 없음',
      MISSING:'미결합 의심 · 확인 필요',UNCERTAIN:'부품 확인 불확실',NOT_EVALUATED:'부품 미평가',
      NOT_RUN:'부품 검사 미실행'}[state]||'부품 확인 불확실';
  }

  // Saved camera-coordinate slots only: this crop is a display, never a detector input.
  function partCrop(raw,key){
    if(!raw?.inspection_id||!Object.hasOwn(parts,key))return null;
    const observations=raw.result?.observations||[],assets=raw.result?.assets||[];
    const preferred=raw.result?.representative_frame_id;
    const ordered=[...observations].sort((a,b)=>Number(b.frame_id===preferred)-Number(a.frame_id===preferred));
    for(const o of ordered){
      const e=o.engine_dynamic,poly=e?.slot_polygons?.[key],w=o.width,h=o.height;
      if(e?.inspection_id!==raw.inspection_id||e?.frame_id!==o.frame_id||e?.pose?.reliable!==true)continue;
      if(!Number.isInteger(w)||!Number.isInteger(h)||w<=0||h<=0||!Array.isArray(poly)||poly.length!==4)continue;
      if(!poly.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&p[0]>=0&&p[0]<=w&&p[1]>=0&&p[1]<=h))continue;
      const area=Math.abs(poly.reduce((s,p,i)=>s+p[0]*poly[(i+1)%4][1]-poly[(i+1)%4][0]*p[1],0))/2;
      if(area<=1)continue;
      const x=Math.floor(Math.min(...poly.map(p=>p[0]))),y=Math.floor(Math.min(...poly.map(p=>p[1])));
      const width=Math.ceil(Math.max(...poly.map(p=>p[0])))-x,height=Math.ceil(Math.max(...poly.map(p=>p[1])))-y;
      const asset=assets.find(a=>a.kind==='raw'&&a.frame_id===o.frame_id&&/^[0-9a-f]{32}$/.test(a.asset_id));
      if(!asset)continue;
      return {url:'/api/v1/assets/'+asset.asset_id,frameId:o.frame_id,number:observations.indexOf(o)+1,
        total:observations.length,x,y,width,height,imageWidth:w,imageHeight:h,polygon:poly};
    }
    return null;
  }

  function showPartCrop(parent,crop,name){
    if(!crop){add(parent,'p','저장된 검사 위치 사진 없음 · 원본/위치 근거 확인 필요','part-crop-empty muted');return;}
    const fig=add(parent,'figure',undefined,'part-crop'),canvas=add(fig,'canvas');
    canvas.hidden=true;canvas.setAttribute('role','img');canvas.setAttribute('aria-label',name+' 저장 원본의 검사 위치');
    const caption=add(fig,'figcaption','검사 위치 사진 불러오는 중');
    const img=document.createElement('img');
    const fail=()=>{canvas.hidden=true;caption.textContent='검사 위치 사진을 불러오지 못했습니다.'};
    img.onerror=fail;
    img.onload=()=>{
      if(img.naturalWidth!==crop.imageWidth||img.naturalHeight!==crop.imageHeight){fail();return;}
      // Fixed display size bounds browser memory; original pixels/records remain unchanged.
      const scale=Math.min(1,360/Math.max(crop.width,crop.height));
      canvas.width=Math.max(1,Math.round(crop.width*scale));canvas.height=Math.max(1,Math.round(crop.height*scale));
      const ctx=canvas.getContext('2d');if(!ctx){fail();return;}
      ctx.drawImage(img,crop.x,crop.y,crop.width,crop.height,0,0,canvas.width,canvas.height);
      ctx.strokeStyle='#71baff';ctx.lineWidth=2;ctx.beginPath();
      crop.polygon.forEach((p,i)=>ctx[i?'lineTo':'moveTo']((p[0]-crop.x)*canvas.width/crop.width,(p[1]-crop.y)*canvas.height/crop.height));
      ctx.closePath();ctx.stroke();canvas.hidden=false;
      caption.textContent=`저장 원본 ${crop.number}/${crop.total} · 파란 선: 검사 위치`;
      fig.title='원본 프레임: '+crop.frameId;
    };
    img.src=crop.url;
  }

  function renderEvidence(raw,assembly,final){
    const host=byId('inspection-detail');host.replaceChildren();
    const data=summarize(raw,assembly,final);
    add(host,'p','선택 검사 ID: '+selectedId,'muted break');
    const stages=add(host,'div',undefined,'inspection-stages');
    const validPose=data.frames.filter(f=>f.preprocessing?.status==='VALID').length;
    const classified=data.frames.filter(f=>Object.values(f.parts||{}).some(p=>p.valid===true)).length;
    for(const [name,value] of [['요청 연결',raw?'기록 있음':'기록 없음'],['원본 저장',data.observations.length+'프레임'],
      ['몸체 정렬',data.frames.length?validPose+'/'+data.frames.length+' 통과':'미실행'],
      ['부품 분류',classified?classified+'프레임 처리':'미실행'],
      ['통합 판정',final?.decision||'미완료']]){
      const stage=add(stages,'div',undefined,'step');add(stage,'span',name);add(stage,'strong',value);
    }
    if(data.noCapture)add(host,'p','검사 미실행 · '+explain(final?.reason||raw?.result?.reason),'notice');
    const detail=data.details;
    add(host,'p','기본 검사: '+detail.decision+' · '+detail.reason,'notice');
    if(detail.terminal)add(host,'p','촬영 종료 원인: '+detail.terminal);
    if(detail.capture){
      const c=detail.capture,known=value=>Number.isInteger(value)?value:'미기록';
      add(host,'p',`촬영 후보 ${known(c.candidate_count)}장 · 거부 ${known(c.rejected_count)}장 · 연속성 초기화 ${known(c.continuity_reset_count)}회 · 폐기된 안정 후보 ${known(c.discarded_stable_frames)}장`);
    }
    if(detail.diagnostic)add(host,'p','저장된 사진은 실패 원인 확인용입니다. 안정된 연속 3장 검사 완료로 집계하지 않습니다.','notice');
    add(host,'p','PLC: '+(detail.plcComplete?'해당 검사의 Result·Done·Request 해제 완료 관측':'해당 검사 거래 완료 관측 미기록')+
      ' · PLC 프로그램 내부 소비 확인과는 구분됩니다.','muted');
    add(host,'p','오조립 참고 분석: '+label(final?.assembly_inspector)+' · '+explain(final?.assembly_reason),'muted');
    if(final?.policy==='BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2')
      add(host,'p','이 검사의 최종 PASS/FAIL은 필수 부품 결합 유무 기준입니다. 오조립 분류는 최종 판정과 PLC OK/NG에 반영하지 않습니다.','muted');
    add(host,'p','존재 검사와 방향·조립 분류는 별도 결과입니다. 아래 내용은 선택한 검사에 저장된 증거이며 현재 미리보기의 판정이 아닙니다.','muted');
    const cards=add(host,'div',undefined,'part-grid');
    for(const row of data.rows){
      const card=add(cards,'section',undefined,'part-card');add(card,'h3',row.name);
      const tone=row.presence==='PRESENT'?'PASS':row.presence==='MISSING_CONFIRMED'?'FAIL':'REVIEW';
      add(card,'strong',presenceLabel(row.presence),'presence-result '+tone);
      showPartCrop(card,data.noCapture?null:partCrop(raw,row.key),row.name);
      add(card,'p','오조립 참고: '+label(row.assembly),'assembly-reference muted');
      add(card,'p',row.perFrame.length?'참고 분류: '+row.perFrame.map(label).join(' / '):'참고 분류 입력 없음','assembly-reference muted');
    }
    add(host,'p','위 사진은 저장 원본에서 검사 위치만 확대한 대표 사진입니다. 미결합 판정은 저장된 전체 검사 결과이며, 사진 확대나 오조립 참고 표시는 판정에 영향을 주지 않습니다.','muted');
    add(host,'h3','실제 저장된 검사 과정');
    add(host,'p','몸체의 전체 자세를 기준 좌표에 맞춘 뒤 네 부품 영역을 잘라 분류합니다. 검사 부품을 각각 정상 방향으로 돌리지 않습니다. 정렬 실패 시 crop·분류는 미실행으로 남습니다.','muted');
    const ids=[...new Set([...data.observations.map(o=>o.frame_id),...data.frames.map(f=>f.frame_id)])];
    ids.forEach((frameId,index)=>{
      const observation=data.observations.find(o=>o.frame_id===frameId);
      const frame=data.frames.find(f=>f.frame_id===frameId);
      const section=add(host,'details',undefined,'evidence-frame');
      section.open=index===0;
      const p=frame?.preprocessing||{};
      add(section,'summary',`프레임 ${index+1} · ${p.status==='VALID'?'정렬 통과':frame?'정렬 확인 필요':'조립 미실행'} · ${frameId}`);
      const images=add(section,'div',undefined,'images');
      const rawAsset=raw?.result?.assets?.find(a=>a.kind==='raw'&&a.frame_id===frameId);
      const prefix='/api/v1/runtime/shadow/'+encodeURIComponent(selectedId)+'/images/';
      if(rawAsset)image(images,detail.diagnostic?'① 실패 진단 원본':'① 검사 원본','/api/v1/assets/'+encodeURIComponent(rawAsset.asset_id));
      else if(frame?.raw_path)image(images,'① 검사 원본',prefix+encodeURIComponent(frame.raw_path));
      const canonical=frame?.images?.canonical;
      if(canonical)image(images,'② 몸체 전체 정렬',prefix+encodeURIComponent(canonical.path));
      else add(images,'p','② 정렬 영상 없음 · '+explain(p.reason||assembly?.reason));
      for(const [key,name] of Object.entries(parts)){
        if(frame?.images?.[key])image(images,'③ '+name+' crop · '+label(frame.parts?.[key]?.predicted_state),prefix+encodeURIComponent(frame.images[key].path));
      }
      const pose=p.pose||{},baseline=p.baseline_pose||{};
      add(section,'p','정렬 경로: '+(p.pose_route||'기록 없음')+' · 대응점 '+(pose.good_matches??baseline.good_matches??'기록 없음')+
        ' · 인라이어 '+(pose.inliers??baseline.inliers??'기록 없음')+' · 오차 '+fixed(pose.median_error_px??baseline.median_error_px)+' px');
      add(section,'p','정렬 사유: '+explain(p.reason)+' · '+(p.baseline_reason||''));
      add(section,'p','고정 몸체 마스크·대응점 표시 영상은 현재 저장되지 않습니다. 저장되지 않은 그림이나 진단 후보 crop을 운영 증거로 표시하지 않습니다.','muted');
      const table=add(section,'div',undefined,'part-grid');
      for(const [key,name] of Object.entries(parts)){
        const part=frame?.parts?.[key],item=add(table,'p');
        const scores=part?.valid===true?Object.entries(part.class_scores||{}).map(([k,v])=>label(k)+' '+(Number.isFinite(v)?(v*100).toFixed(1)+'%':'미기록')).join(' · '):'분류 미실행';
        item.textContent=name+': '+scores;
      }
      add(section,'p','모델 점수는 정답 확률을 보장하지 않습니다. 최종 판정은 저장된 3프레임 정책 결과를 따릅니다.','muted');
      const technical=add(section,'details');add(technical,'summary','좌표·품질·판정 근거');
      add(technical,'pre',JSON.stringify({presence:observation?.engine_dynamic,preprocessing:p,parts:frame?.parts,three_frames:frame?.three_frames},null,2));
    });
    if(!ids.length)add(host,'p','촬영 원본과 조립 crop이 없습니다. 결품 또는 오조립 여부를 판단할 수 없습니다.');
  }

  async function json(url,signal){
    const response=await fetch(url,{signal,cache:'no-store'});
    if(!response.ok)throw Error('조회 실패 HTTP '+response.status);
    return response.json();
  }
  async function select(id,manual=false){
    if(manual)followLatest=false;
    if(!id||!/^[0-9a-f]{32}$/.test(id))return;
    if(loadedKey===id)return;
    selectedId=id;loadedKey=id;const ticket=++loadGeneration;
    controller?.abort();controller=new AbortController();const requestController=controller;
    const timer=setTimeout(()=>requestController.abort(),6000);
    byId('inspection-detail').replaceChildren();byId('inspection-detail').textContent='선택한 검사 증거 조회 중 · '+id;
    try{
      const encoded=encodeURIComponent(id);
      const [raw,assembly,final]=await Promise.all([
        json('/api/v1/inspections/'+encoded,requestController.signal),
        json('/api/v1/runtime/shadow/'+encoded,requestController.signal),
        json('/api/v1/line/final/'+encoded,requestController.signal)]);
      if(ticket!==loadGeneration)return;
      if(raw.inspection_id!==id||(assembly.inspection_id&&assembly.inspection_id!==id)||(final.inspection_id&&final.inspection_id!==id))throw Error('검사 ID 불일치');
      renderEvidence(raw,assembly,final);
    }catch(error){if(ticket===loadGeneration){byId('inspection-detail').textContent=error.message+' · 증거 다시 조회를 눌러 주세요.'}}
    finally{clearTimeout(timer)}
  }

  function updateLatest(result){if(followLatest&&result?.inspection_id!==loadedKey)select(result?.inspection_id)}
  async function refreshRecovery(){
    recovery=null;byId('recovery-submit').disabled=true;
    byId('recovery-state').textContent='현재 PLC·작업·과거 제품 문맥 확인 중…';
    try{
      recovery=await json('/api/v1/maintenance/product-context/status',AbortSignal.timeout(4000));
      byId('recovery-state').textContent=explain(recovery.reason)+(recovery.inspection_id?' · 대상 '+recovery.inspection_id:'');
      if(recovery.eligible)byId('recovery-state').textContent='프로그램의 STOP·무출력·작업 종료 확인됨. 실제 벨트 정지와 모형 정리를 확인했다면 아래 Reset을 누르세요. 대상 '+recovery.inspection_id;
    }catch(error){byId('recovery-state').textContent=error.message}
    recoveryEnabled();
  }
  function recoveryEnabled(){
    byId('recovery-submit').disabled=recoveryBusy||!recovery?.eligible;
  }
  async function submitRecovery(){
    if(byId('recovery-submit').disabled)return;
    recoveryBusy=true;recoveryEnabled();
    try{
      const response=await fetch('/api/v1/maintenance/product-context/close',{method:'POST',
        headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(6000),
        body:JSON.stringify({identifier:recovery.inspection_id,actor:'FIELD_HMI_OPERATOR',
          reason:'OPERATOR_CONFIRMED_STOP_AND_PRODUCT_OFF_LINE',confirmations:['PHYSICAL_STOP','PRODUCT_REMOVED_OR_HELD_OFF_LINE','CLOSE_CONTEXT_WITHOUT_RESULT']})});
      const value=await response.json();
      if(!response.ok)throw Error(explain(value.error||'복구 거부'));
      byId('recovery-state').textContent='이전 제품 문맥 정리 완료 · 기록 보존 · 결과 재송신 없음. 현재 화면의 준비 상태를 다시 확인하세요. 복구 기록 '+value.recovery_id;
    }catch(error){byId('recovery-state').textContent='복구 완료 미확인 · '+error.message+' 자동 재시도하지 않습니다. 상태 다시 확인을 눌러 주세요.'}
    finally{recovery=null;recoveryBusy=false;recoveryEnabled()}
  }
  function init(){
    byId('recovery-open').onclick=()=>{byId('recovery-dialog').showModal();refreshRecovery()};
    byId('recovery-close').onclick=()=>byId('recovery-dialog').close();
    byId('recovery-refresh').onclick=()=>{if(!recoveryBusy)refreshRecovery()};
    byId('recovery-submit').onclick=submitRecovery;
    byId('evidence-retry').onclick=()=>{loadedKey=null;select(selectedId)};
    byId('evidence-latest').onclick=()=>{followLatest=true;loadedKey=null;updateLatest(window.lineLatestResult)};
  }
  return {init,select,updateLatest,summarize,explain,label,partCrop,presenceLabel};
})();
