/* Read-only explanation of one saved inspection. Never influences decisions. */
const slotNames = {pipe_left:'LEFT PIPE',pipe_right:'RIGHT PIPE',exhaust:'EXHAUST',symbol:'SYMBOL'};
let selectedFrame = 0, savedLoad = 0;
const recorded = value => value === undefined || value === null ? '기록 없음' : String(value);
const numberText = value => typeof value === 'number' ? value.toFixed(3) : '기록 없음';
function frameReason(frame) {
  const pose = frame.pose || {}, diagnostic = pose.diagnostics;
  const gates = diagnostic?.failed_conditions;
  return (frame.reason_code || '기록 없음') + (gates?.length ? ' / '+gates.join(', ') : '');
}
function finalExplanation(result) {
  if (!result) return '검사 요청 접수 · 처리 중';
  const frames = result.observations?.map(o=>o.engine_dynamic || {}) || result.frames || [];
  let blockers = result.blocking_frames;
  let source = '';
  if (!blockers) {
    // Old records have no new diagnostics. Derive only exact recorded reasons;
    // do not pretend thresholds or reference attempts were recorded.
    blockers = frames.flatMap((f,i)=>f.reason_code === result.reason_code ? [{frame_number:i+1,reason_code:f.reason_code}] : []);
    source = ' (과거 프레임 기록에서 대조; 새 진단 기록 없음)';
  }
  const cause = blockers.length ? blockers.map(b=>'프레임 '+b.frame_number+' · '+b.reason_code).join(' / ') : '3프레임 합의 · '+recorded(result.reason_code);
  return 'FINAL '+result.decision+' — '+cause+source;
}
function explainFrame(observation) {
  const frame = observation.engine_dynamic || {}, pose = frame.pose || {}, selection = frame.product_selection;
  const diagnostic = pose.diagnostics, stages = frame.detector_stages;
  const lines = [
    '제품: '+(selection ? selection.detail+' / 유효 '+selection.valid_count+'개 / 기준 ≥ '+numberText(selection.confidence_threshold) : '선택 단계·임계값 기록 없음'),
    '제품 후보 confidence (NMS 후): '+((selection?.candidates || (observation.detections || []).filter(d=>d.class_name==='product_envelope')).map(d=>numberText(d.confidence)+(d.accepted===true?' [선택 기준 통과]':d.accepted===false?' [미달]':'')).join(', ') || '후보 없음 / 기록 없음'),
    '검출 단계: '+(stages ? 'raw '+stages.raw_candidate_count+' → confidence > '+stages.detector_confidence_threshold+' : '+stages.pre_nms_eligible_count+' → NMS '+stages.post_nms_count : '기록 없음'),
    'Pose: '+(pose.reliable === true ? 'OK · angle '+numberText(pose.angle_deg)+'°' : '신뢰 불가 · 각도 미사용')+' / '+frameReason(frame),
    'inliers '+recorded(pose.inliers)+' / matches '+recorded(pose.matches)+' / reprojection '+numberText(pose.reprojection_error_px)+' px / scale '+numberText(pose.scale),
    '적용 Pose 기준: '+(diagnostic ? JSON.stringify(diagnostic.thresholds) : '기록 없음'),
    '품질: '+recorded(frame.quality_valid)+' / 모션: '+(frame.stable === true ? 'STABLE (손 없음의 증거 아님)' : frame.stable === false ? '움직임/대기' : '기록 없음'),
    ...Object.entries(slotNames).map(([key,name])=>name+': '+(frame.slot_states?.[key] || '기록 없음')),
    ...(frame.assignment_diagnostics || []).map(d=>'검출 #'+d.detection_index+' '+d.class_name+' '+numberText(d.confidence)+' → '+(d.assigned_slot || '미배정')+' / '+d.reason+' / '+recorded(d.position_detail)),
  ];
  if (diagnostic?.failed_conditions?.includes('SCALE_RANGE')) lines.push('조치: 엔진 크기가 기준 범위를 벗어났습니다. 카메라와의 거리·평면 자세를 조정하세요.');
  if (selection?.detail==='CANDIDATES_BELOW_THRESHOLD' || selection?.detail==='NO_RETURNED_CANDIDATES') lines.push('조치: 엔진 전체가 보이는 위치에서 조명·크기·각도를 확인하세요. 후보 박스가 실제 엔진인지 확인하세요.');
  return lines.join('\n');
}
async function selectSavedFrame(index) {
  selectedFrame = index;
  const ticket = ++savedLoad, detail = selected;
  const observation = detail?.result?.observations?.[index];
  const canvas = el('savedCanvas');
  canvas.hidden=true; // Never label the previous canvas as the newly selected frame while loading.
  for (const [i,button] of [...el('frameThumbs').children].entries()) button.setAttribute('aria-pressed',String(i===index));
  if (!observation) {canvas.hidden=true;el('selectedFrame').textContent='프레임 기록 없음';el('geometryDetails').textContent='기록 없음';el('frameDetails').textContent='프레임 기록 없음';return;}
  const asset = detail.result.assets?.find(a=>a.kind==='raw' && a.frame_id===observation.frame_id);
  el('selectedFrame').textContent='현재 표시: 프레임 '+(index+1)+' / frame_id '+observation.frame_id+' / Pose '+(observation.engine_dynamic?.pose?.reliable ? 'OK':'신뢰 불가');
  el('frameDetails').textContent=explainFrame(observation);
  el('geometryDetails').textContent=JSON.stringify({assignment:observation.engine_dynamic?.assignment_diagnostics || '기록 없음',pose:observation.engine_dynamic?.pose?.diagnostics || '기록 없음',product:observation.engine_dynamic?.product_selection || '기록 없음',freshness:observation.freshness,stage_timings_ms:observation.engine_dynamic?.stage_timings_ms || '기록 없음'},null,2);
  if (!asset) {canvas.hidden=true;return;}
  const image = new Image();
  image.src='/api/v1/assets/'+asset.asset_id;
  await image.decode();
  if (ticket!==savedLoad || selected?.inspection_id!==detail.inspection_id) return;
  canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;canvas.hidden=false;
  const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
  function polygon(points,color,dashed=false) {
    if (!Array.isArray(points) || points.length<3) return;
    ctx.strokeStyle=color;ctx.lineWidth=3;ctx.setLineDash(dashed?[9,6]:[]);ctx.beginPath();
    points.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke();ctx.setLineDash([]);
  }
  for (const d of observation.detections || []) {
    const b=d.bounding_box || d.bbox;
    const box=Array.isArray(b)?b:[b.x1,b.y1,b.x2,b.y2];
    const points=d.detection_polygon || [[box[0],box[1]],[box[2],box[1]],[box[2],box[3]],[box[0],box[3]]];
    polygon(points,d.class_name==='product_envelope'?'#16cbea':'#70edb4');
  }
  const frame=observation.engine_dynamic || {};
  if (el('slotsVisible').checked && frame.pose?.reliable) for (const points of Object.values(frame.slot_polygons || {})) polygon(points,'#d99fff',true);
}
function renderSavedFrames(detail) {
  el('finalExplanation').textContent=finalExplanation(detail.result);
  el('frameThumbs').replaceChildren();
  const observations=detail.result?.observations || [];
  observations.forEach((observation,index)=>{
    const button=document.createElement('button');button.className='frameThumb';
    const asset=detail.result.assets?.find(a=>a.kind==='raw' && a.frame_id===observation.frame_id);
    if (asset) {const image=document.createElement('img');image.src='/api/v1/assets/'+asset.asset_id;image.alt='프레임 '+(index+1)+' 원본 썸네일';button.append(image);}
    const text=document.createElement('span');text.textContent='프레임 '+(index+1)+' · '+frameReason(observation.engine_dynamic || {});button.append(text);
    button.onclick=()=>selectSavedFrame(index).catch(e=>message(e.message));el('frameThumbs').append(button);
  });
  el('saved').hidden=true;
  selectSavedFrame(Math.min(selectedFrame,Math.max(0,observations.length-1))).catch(e=>message(e.message));
}
function renderScene(current) {
  const frame=current.scene;
  el('sceneDetails').textContent=frame ? 'PREVIEW · frame_id '+frame.frame_id+'\n'+explainFrame({engine_dynamic:frame}) : '현재 장면 정보 없음';
  const p=current.progress;
  const stages={FRESH_FRAME_CAPTURE:'새 프레임 수신',PRODUCT_POSE_PART_SLOT_PROCESSING:'제품·Pose·부품·Slot 처리',CONSENSUS_AND_EVIDENCE_ENCODING:'3프레임 합의·Evidence 인코딩'};
  if (current.active_inspection_id) message('검사 요청 접수 · 처리 중: '+(p?stages[p.stage]+' / '+p.completed_frames+'/'+p.required_frames+'장 완료':'Worker 대기')+' / '+current.active_inspection_id);
}
