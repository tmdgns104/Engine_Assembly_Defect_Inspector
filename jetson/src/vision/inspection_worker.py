"""Persistent camera/model owner. Inspection durability stays in the Service.

Optional bounded diagnostic raw files are separate from inspection/Journal data.
"""
from src import config as parameters

import queue
import threading
import time
from time import perf_counter
import socket
import logging
import hashlib
from datetime import datetime, timezone

from src.camera.fresh_frame import FreshFrameError, FreshFrameSelector, TriggerContext
from src.camera.frame_integrity import FRAME_EVIDENCE_CONTRACT, measured_integrity
from src.contracts import CameraError
from src.contracts.interfaces import FatalDetectorError
from src.decision.slots import assess, pixel_box
from src.decision.calibration import ReferenceError, reference_proposal, station_fingerprint
from src.quality.image import assess_image
from src.recipe.package import load_package


def put_latest(channel, value):
    try:
        channel.put_nowait(value)
    except queue.Full:
        try:
            channel.get_nowait()
        except queue.Empty:
            pass
        try:
            channel.put_nowait(value)
        except queue.Full:
            pass


def encode_evidence(frame, observations, recipe, calibration, *, result=None):
    import cv2
    images = []
    for original in frame:
        ok, encoded = cv2.imencode(".png", original.image)
        if not ok:
            raise OSError("PNG_ENCODE_FAILED")
        images.append({"data": encoded.tobytes(), "kind": "raw", "width": original.width,
                       "height": original.height, "capture_at": original.captured_at.isoformat(), "view": "top",
                       "frame_id": getattr(original, 'frame_id', None)})
    last = frame[-1]
    overlay = last.image.copy()
    if observations[-1].get('engine_dynamic'):
        from src.vision.engine_inspector import draw_engine_overlay
        overlay=draw_engine_overlay(last.image,observations[-1],result)
        ok,encoded=cv2.imencode('.jpg',overlay)
        if not ok:raise OSError('OVERLAY_ENCODE_FAILED')
        images.append({'data':encoded.tobytes(),'kind':'overlay','width':last.width,'height':last.height,
            'capture_at':last.captured_at.isoformat(),'view':'top','frame_id':last.frame_id})
        return images
    for item in observations[-1]["detections"]:
        box = item["bounding_box"]
        x1,y1,x2,y2 = [round(box[k]) for k in ("x1","y1","x2","y2")]
        cv2.rectangle(overlay,(x1,y1),(x2,y2),(0,220,0),2)
        cv2.putText(overlay,f'{item["class_name"]} {item["confidence"]:.3f}',(x1,max(20,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,220,0),2)
    # 기준 등록은 자리 안내, 제품 검사는 실제 판정 상태만 표시한다.
    # 기존 네 인자 호출은 기준 안내 호출로 유지한다.
    regions = calibration["slots"] if calibration else {}
    reference_view = result is None or bool(calibration and not calibration.get('confirmed'))
    for slot in recipe["slots"]:
        if slot['id'] not in regions:
            continue
        if reference_view:
            label, color = 'REFERENCE', (230,50,230)
        else:
            state = result.get('slot_states', {}).get(slot['id'])
            if state == 'PRESENT':
                continue
            label, color = ('MISSING', (0,0,230)) if state == 'ABSENT_CONFIRMED' else ('UNASSESSED', (0,170,255))
        x1,y1,x2,y2 = map(round,pixel_box(regions[slot["id"]],last.width,last.height))
        cv2.rectangle(overlay,(x1,y1),(x2,y2),color,2)
        cv2.putText(overlay,label+" "+slot["id"],(x1,min(last.height-5,y2+20)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
    ok, encoded = cv2.imencode(".jpg", overlay)
    if not ok:
        raise OSError("OVERLAY_ENCODE_FAILED")
    images.append({"data": encoded.tobytes(), "kind": "overlay", "width": last.width,
                   "height": last.height, "capture_at": last.captured_at.isoformat(), "view": "top",
                   "frame_id": getattr(last, 'frame_id', None)})
    return images


def worker_main(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat, products=None, production_tracking=None, *, run_capture_signals=None):
    from src.camera.gstreamer_camera import GStreamerCamera
    from src.vision.detector_factory import create_detector
    import cv2
    camera = None
    detector = None
    engine = None
    primary_error = None
    from src.vision.diagnostic_capture import DiagnosticCapture
    diagnostic = DiagnosticCapture()
    profile = station.get('auto_profile')
    area_model = None
    area_window = None
    last_preview = 0
    def preview_frame(frame, metadata, observation=None):
        nonlocal last_preview
        if time.monotonic()-last_preview < parameters.PREVIEW_INTERVAL_SECONDS:
            return
        preview_image=frame.image
        if observation and observation.get('engine_dynamic'):
            from src.vision.engine_inspector import draw_engine_overlay
            preview_image=draw_engine_overlay(frame.image,observation)
        ok, jpeg = cv2.imencode('.jpg',preview_image,[cv2.IMWRITE_JPEG_QUALITY,parameters.PREVIEW_JPEG_QUALITY])
        if not ok:
            raise RuntimeError('PREVIEW_ENCODING_FAILED')
        jpeg_no_slots=jpeg
        if observation and observation.get('engine_dynamic'):
            ok,jpeg_no_slots=cv2.imencode('.jpg',draw_engine_overlay(frame.image,observation,show_slots=False),[cv2.IMWRITE_JPEG_QUALITY,parameters.PREVIEW_JPEG_QUALITY])
            if not ok:raise RuntimeError('PREVIEW_ENCODING_FAILED')
        put_latest(previews,{'jpeg':jpeg.tobytes(),'jpeg_no_slots':jpeg_no_slots.tobytes(),'generation':generation,'freshness':metadata,
            'scene':observation.get('engine_dynamic') if observation else None,
            'area_occupancy':observation.get('area_occupancy') if observation else None,
            'diagnostic_capture':diagnostic.status()})
        last_preview = time.monotonic()

    def detect_frame(frame, freshness, *, inspection=False):
        if engine:
            engine.detector.capture_diagnostics = diagnostic.recording and getattr(diagnostic,'requires_tensor',True)
        before = hashlib.sha256(frame.image.tobytes()).hexdigest()
        integrity = measured_integrity(frame.image, freshness.get('integrity'))
        freshness = dict(freshness, integrity=integrity)
        detected = None
        packet = None
        if integrity['valid']:
            detected = ({'frame_id':frame.frame_id,'detections':[],
                         'model_version':package.manifest['model_version'],'inference_ms':0.}
                        if engine else detector.detect(frame).to_dict())
            if hashlib.sha256(frame.image.tobytes()).hexdigest() != before:
                raise RuntimeError('INFERENCE_INPUT_MUTATED')
        if profile:
            from src.observation.detector_carrier import observe_carrier
            provider = observe_carrier(detected['detections'],frame.width,frame.height,profile) if detected else None
            packet = {'generation':generation,'frame_id':frame.frame_id,'sequence':freshness['sequence'],
                'camera_epoch':freshness['camera_epoch'],'monotonic_s':freshness['estimated_source_monotonic'],
                'received_monotonic':freshness['received_monotonic'],'freshness':freshness,
                'width':frame.width,'height':frame.height,'coordinate_space':'normalized_image',
                'integrity':integrity,'pixel_sha256':before,'provider':provider.to_dict() if provider else None,
                'inference_ms':detected['inference_ms'] if detected else None,
                'package_sha256':package.manifest_hash,'processed_monotonic':time.monotonic()}
            put_latest(products,packet)
        if not integrity['valid']:
            raise CameraError('FRAME_INTEGRITY_REJECTED: '+str(integrity))
        detected.update(width=frame.width,height=frame.height,freshness=freshness,
            quality=assess_image(frame.image,station['quality']),captured_at=frame.captured_at.isoformat(),
            input_pixel_sha256=before, frame_evidence_contract=FRAME_EVIDENCE_CONTRACT,
            worker_generation=generation)
        if area_model:
            measurement = area_model.evaluate(frame.image)
            area_metadata = dict(frame_id=frame.frame_id,sequence=freshness['sequence'],
                camera_epoch=freshness['camera_epoch'],generation=generation,integrity=integrity,
                monotonic_s=freshness['estimated_source_monotonic'],
                source_timestamp=freshness.get('source_pts_ns'))
            detected['area_occupancy'] = area_window.update(measurement,area_metadata,time.monotonic())
        if engine:
            if production_tracking is not None and production_tracking.is_set() and not inspection:
                detected['engine_dynamic']=engine.observe_product(frame,detected)
            else:
                engine.detect(frame,detected,parts_detector=detector)
            if production_tracking is not None and production_tracking.is_set():
                from src.observation.engine_envelope import envelope_provider
                product_detections=[d for d in detected['detections'] if d['class_name']=='product_envelope']
                provider=envelope_provider(product_detections,frame.width,frame.height,engine.estimator.cfg['decision_policy']['product_confidence'])
                packet={'generation':generation,'frame_id':frame.frame_id,'sequence':freshness['sequence'],
                    'camera_epoch':freshness['camera_epoch'],'monotonic_s':freshness['estimated_source_monotonic'],
                    'freshness':freshness,'width':frame.width,'height':frame.height,'integrity':integrity,
                    'provider':provider.to_dict(),'detections':product_detections,'package_sha256':package.manifest_hash,
                    'processed_monotonic':time.monotonic(),'stable':detected['engine_dynamic'].get('stable',False),
                    'product_detection_ms':detected['engine_dynamic']['stage_timings_ms']['product_detection_ms']}
                if area_model: packet['area_occupancy'] = detected['area_occupancy']
                if diagnostic.recording:
                    packet['diagnostic_clip_id'] = diagnostic.request['clip_id']
                put_latest(products,packet)
            if diagnostic.recording:
                from src.observation.engine_envelope import envelope_provider
                from src.vision.run_capture import part_inference_provenance
                products_for_record = [d for d in detected['detections'] if d['class_name']=='product_envelope']
                gate = engine.estimator.cfg['decision_policy']['product_confidence']
                diagnostic.observe(frame.frame_id, dict(frame_id=frame.frame_id,
                    processed_monotonic=time.monotonic(), inspection=inspection,
                    detector_frame_id=(getattr(engine.detector,'diagnostic_frame_id',None)
                        if getattr(diagnostic,'requires_tensor',True) else None),
                    inference_ms=detected['inference_ms'],
                    mode='PRODUCTION_TRACKING' if production_tracking is not None and production_tracking.is_set() and not inspection else 'FULL_INSPECTION_PATH',
                    generation=generation, package_sha256=package.manifest_hash,
                    input_pixel_sha256=before,
                    detections=(products_for_record if getattr(diagnostic,'requires_tensor',True) else detected['detections']),
                    **part_inference_provenance(detected),
                    provider=envelope_provider(products_for_record,frame.width,frame.height,gate).to_dict(),
                    product_confidence_threshold=gate, engine=detected['engine_dynamic'],
                    production_packet_emitted=packet is not None),
                    (getattr(engine.detector,'diagnostic_output',None)
                        if getattr(diagnostic,'requires_tensor',True) else None))
            preview_frame(frame,freshness,detected)
        return detected,packet

    def capture_frame():
        diagnostic.tick()
        value = camera.capture()
        diagnostic.capture(value.frame_id, value.image, dict(camera.frame_info))
        return value
    def pulse():
        while not stopping.wait(parameters.WORKER_HEARTBEAT_INTERVAL_SECONDS):
            heartbeat.value = time.monotonic()
    threading.Thread(target=pulse, daemon=True).start()
    try:
        from src.configuration import snapshot
        configuration = snapshot()
        package = load_package(package_root)
        if profile:
            from src.runtime.auto_profile import validate_profile
            validate_profile(profile,package)
        start = time.monotonic()
        detector = create_detector(package)
        if package.recipe.get('alignment_mode')=='engine_affine':
            if profile:raise ValueError('DYNAMIC_ENGINE_MANUAL_ONLY')
            from src.vision.engine_inspector import EngineInspector
            engine=EngineInspector(package)
            if production_tracking is not None:
                from pathlib import Path
                from src.observation.area_occupancy import load_area_occupancy, ClearWindow
                area_path = Path(__file__).resolve().parents[2]/'config/area_clearance.json'
                area_model = load_area_occupancy(area_path)
                area_window = ClearWindow()
        if "self_test" in package.manifest["files"]:
            from src.contracts import CameraFrame
            image = cv2.imread(str(package.root / package.manifest["files"]["self_test"]["path"]))
            if image is None:
                raise RuntimeError("PACKAGE_SELF_TEST_IMAGE_INVALID")
            frame = CameraFrame(image,"package-self-test",datetime.now(timezone.utc),image.shape[1],image.shape[0],"replay")
            detector.detect(frame)
        camera = GStreamerCamera(dict(package.capture, device=station["camera_device"]))
        if profile:
            from src.camera.continuous import ContinuousFrames
            camera = ContinuousFrames(camera,stopping,preview_frame)
        first = camera.capture()
        backend = detector.runtime_metadata()
        backend['configuration_sha256'] = configuration['sha256']
        if engine:backend['envelope']=engine.detector.runtime_metadata()
        backend.update(hostname=socket.gethostname(), camera_pipeline=camera.pipeline_text,
                       load_self_test_ms=(time.monotonic()-start)*1000)
        # READY must not expose the parent's stale pre-spawn heartbeat. The pulse
        # thread's first update can occur after the service consumes this message.
        heartbeat.value = time.monotonic()
        results.put({"type": "ready", "generation": generation, "backend": backend}, timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
        while not stopping.is_set():
            frame = capture_frame()
            if engine:
                detect_frame(frame,dict(camera.frame_info))
            elif not profile:
                preview_frame(frame,dict(camera.frame_info))
            else:
                try:
                    detect_frame(frame,dict(camera.frame_info))
                except CameraError as error:
                    logging.getLogger(__name__).warning('손상 프레임 거절: %s',error)
            try:
                job = commands.get_nowait()
            except queue.Empty:
                continue
            if job.get('type') in ('diagnostic_capture','field_raw_capture','run_capture'):
                try:
                    if job['action'] == 'stop':
                        diagnostic.stop()
                    else:
                        if diagnostic.phase in ('ARMED','RECORDING','WAIT_SAFE_FLUSH','SAVING') or (diagnostic.thread and not diagnostic.wait(0)):
                            raise ValueError('CAPTURE_ALREADY_ACTIVE_OR_SAVING')
                        if job['type']=='run_capture':
                            from src.vision.run_capture import RunCapture
                            if run_capture_signals is None:
                                raise ValueError('RUN_CAPTURE_SIGNALS_UNAVAILABLE')
                            if job.get('context',{}).get('camera_epoch') != camera.frame_info['camera_epoch']:
                                raise ValueError('RUN_CAPTURE_CAMERA_EPOCH_CHANGED')
                            diagnostic = RunCapture()
                        elif job['type']=='field_raw_capture':
                            from src.vision.field_raw_capture import FieldRawCapture
                            diagnostic = FieldRawCapture()
                        else:
                            diagnostic = DiagnosticCapture()
                        diagnostic.start(job['folder'], job['request'], dict(
                            worker_generation=generation, camera_owner_pid=__import__('os').getpid(),
                            camera_epoch=camera.frame_info['camera_epoch'],
                            raw_shape=list(frame.image.shape),
                            run_capture_approved=job.get('context',{}).get('run_capture_approved',False),
                            camera_pipeline=camera.pipeline_text, package_sha256=package.manifest_hash,
                            capture=package.capture, backend=backend, station=station,
                            conditions=job.get('context',{}),
                            field_raw_approval=job.get('context',{}).get('field_raw_approval',False),
                            publication_disabled=job.get('context',{}).get('publication_disabled',False)),
                            **({'signals':run_capture_signals} if job['type']=='run_capture' else {}))
                    results.put({'type':'diagnostic_capture','generation':generation,'status':diagnostic.status()}, timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
                except Exception as error:
                    results.put({'type':'diagnostic_capture','generation':generation,
                                 'status':dict(state='ERROR',error=str(error),clip_id=job.get('request',{}).get('clip_id'))},timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
                continue
            observations, frames = [], []
            motion_modes=('CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH')
            motion_mode=(job.get('production_binding',{}).get('inspection_motion_mode') in motion_modes
                and job.get('production_binding',{}).get('inspection_motion_mode')==
                    job.get('experiment_policy',{}).get('inspection_motion_mode'))
            from src.runtime.inspection_start import FULL_FRAME
            binding = job.get('production_binding', {})
            stationary_capture = bool(engine and job['request']['kind'] == 'inspect'
                and binding.get('plc_contract') == 'OPENER_CYCLIC'
                and binding.get('inspection_start_policy') == FULL_FRAME
                and binding.get('inspection_motion_mode') == 'STATIONARY'
                and job.get('experiment_policy', {}).get('inspection_motion_mode') == 'STATIONARY')
            if stationary_capture:
                engine.reset_motion()
            # The PLC edge accepts the request immediately, but may precede the
            # physical stop. Keep the existing motion test and acquire a settled
            # trio within the original deadline, instead of judging coasting.
            stationary_candidates = []
            stationary_rejections = []
            stationary_candidate_count = stationary_rejected_count = 0
            discarded_stable_frames = 0
            continuity_reset_count = 0

            def stationary_evidence(selected):
                return dict(policy='POST_REQUEST_STABLE_THREE_FRAMES',
                    candidate_count=stationary_candidate_count,
                    rejected_count=stationary_rejected_count,
                    rejected_frames=list(stationary_rejections),
                    rejected_metadata_truncated=max(0, stationary_rejected_count-len(stationary_rejections)),
                    discarded_stable_frames=discarded_stable_frames,
                    continuity_reset_count=continuity_reset_count,
                    selected_frame_ids=[o['frame_id'] for o in selected],
                    deadline_monotonic=selector.deadline if selector else job['deadline'])

            def fresh_evidence(selected):
                evidence = selector.evidence()
                if stationary_capture:
                    candidates = evidence['selected_frames']
                    selected_ids = {o['frame_id'] for o in selected}
                    # Fresh acquisition candidates and final inspection evidence
                    # are different sets once motion can reject a candidate.
                    evidence['acquisition_candidate_count'] = len(candidates)
                    evidence['acquisition_candidates'] = candidates[-32:]
                    evidence['selected_frames'] = [f for f in candidates if f['frame_id'] in selected_ids]
                if len(selected) == package.recipe['observation_count'] and not selector.terminal_reason:
                    evidence['capture_completed_monotonic'] = max(
                        f['selected_at_monotonic'] for f in evidence['selected_frames'])
                evidence['processing_deadline_monotonic'] = job['deadline']
                return evidence

            def check_processing():
                if selector:
                    check = selector.check_processing if 'capture_deadline' in job else selector.check_active
                    check(time.monotonic(), stopping.is_set() or cancellation.is_set())

            conveyor_rejections=[]
            def progress(stage):
                if engine is None:return
                try:
                    results.put_nowait({'type':'progress','generation':generation,'inspection_id':job['inspection_id'],
                        'stage':stage,'completed_frames':len(frames),'required_frames':package.recipe['observation_count']})
                except queue.Full:
                    pass  # Progress is optional; never drop a final result or fail inspection for UI telemetry.
            selector = None
            bound = job['request'].get('auto_frame_binding')
            after = job["accepted_monotonic"] + station["frame_spacing_seconds"]
            try:
                if station.get('fresh_frame'):
                    selector = FreshFrameSelector(TriggerContext(**job['trigger']), station['fresh_frame'],
                                                  station['max_frame_age_seconds'], station['frame_spacing_seconds'],
                                                  source_not_before=job.get('durable_admission_monotonic'))
                while len(frames) < package.recipe["observation_count"]:
                    if selector:
                        selector.check_active(time.monotonic(), stopping.is_set() or cancellation.is_set())
                    if stopping.is_set() or cancellation.is_set() or time.monotonic() > job["deadline"]:
                        raise TimeoutError("CANCELLED_OR_EXPIRED")
                    try:
                        progress('FRESH_FRAME_CAPTURE')
                        capture_started=perf_counter()
                        frame = capture_frame()
                        capture_elapsed=(perf_counter()-capture_started)*1000
                    except CameraError as error:
                        if selector:
                            selector.reject(str(error), getattr(camera, 'rejected_frame_info', {}),
                                            time.monotonic(), fatal=True)
                        raise
                    freshness = dict(camera.frame_info)
                    if selector:
                        freshness = selector.consider(freshness, time.monotonic(),
                                                      stopping.is_set() or cancellation.is_set())
                        if freshness is None:
                            continue
                    elif freshness["estimated_source_monotonic"] < after or freshness["age_seconds"] > station["max_frame_age_seconds"]:
                        continue
                    progress('PRODUCT_POSE_PART_SLOT_PROCESSING')
                    detected,packet = detect_frame(frame,freshness,inspection=True)
                    if engine:
                        detected['engine_dynamic']['inspection_id']=job['inspection_id']
                        detected['engine_dynamic']['stage_timings_ms']['camera_receive_ms']=capture_elapsed
                    if stationary_capture:
                        stationary_candidate_count += 1
                        stationary_candidates.append((frame, detected))
                        stationary_candidates = stationary_candidates[-3:]
                        value = detected['engine_dynamic']
                        if value.get('stable') is not True:
                            stationary_rejected_count += 1
                            stationary_rejections.append(dict(frame_id=frame.frame_id,
                                sequence=freshness['sequence'], camera_epoch=freshness['camera_epoch'],
                                source_pts_ns=freshness['source_pts_ns'],
                                source_monotonic=freshness['estimated_source_monotonic'],
                                motion_fraction=value.get('motion_fraction'),
                                motion_evidence=value.get('motion_evidence'),
                                reason='WAIT_FOR_STABLE_FRAME'))
                            stationary_rejections = stationary_rejections[-32:]
                            # A moving frame breaks the contiguous stable trio;
                            # a prior stable image cannot be reused after it.
                            if frames:
                                continuity_reset_count += 1
                            discarded_stable_frames += len(frames)
                            frames.clear(); observations.clear()
                            progress('WAIT_FOR_STABLE_FRAME')
                            continue
                    if motion_mode:
                        from src.vision.engine_inspector import conveyor_frame_gate
                        reason=conveyor_frame_gate(detected,job['production_binding']['inspection_zone'])
                        if reason:
                            conveyor_rejections.append({'frame_id':frame.frame_id,'reason_code':reason})
                            conveyor_rejections=conveyor_rejections[-32:]
                            continue
                    if bound:
                        from src.vision.auto_inspection import validate_bound_frame, automatic_coverage
                        bound = validate_bound_frame(bound,packet,profile)
                        detected['automatic_coverage'] = automatic_coverage(detected,package,job.get('calibration'),bound['bbox'],profile)
                        detected['auto_frame_binding'] = dict(bound)
                    # The source was selected before the capture deadline. Check
                    # cancellation/total processing now; the next capture still
                    # must pass the unchanged short selection window.
                    check_processing()
                    frames.append(frame); observations.append(detected)
                    after = freshness["estimated_source_monotonic"] + station["frame_spacing_seconds"]
                three_frames_ms=(time.monotonic()-job['accepted_monotonic'])*1000
                candidate = None
                if job["request"]["kind"] == "calibrate":
                    try:
                        if engine:
                            from src.vision.engine_inspector import dynamic_reference
                            candidate=dynamic_reference(observations,package,job['request']['view_assessment'])
                        else:
                            candidate = reference_proposal(observations,package)
                        candidate.update(source_inspection_id=job['inspection_id'], station_id=station['station_id'],
                                         cell_id=station['cell_id'], station_sha256=station_fingerprint(station))
                        result = {"decision": "REVIEW", "reason": "검사 자리와 제품 구도를 화면에서 확인하세요.", "defects": [], "unassessed": []}
                    except ReferenceError as error:
                        result = {"decision": "REVIEW", "reason": str(error), "reason_code": error.code,
                                  "defects": [], "unassessed": error.slots}
                else:
                    view = {'source':'AUTO_WORKER_DERIVED'} if bound else job['request']['view_assessment']
                    if engine:
                        from src.vision.engine_inspector import assess_dynamic
                        result=assess_dynamic(observations,view,job.get('calibration'),experiment_policy=job.get('experiment_policy'))
                    else:
                        result = assess(observations,package.recipe,view,job.get("calibration"))
                if job.get('production_binding'):
                    from src.vision.production_binding import verify_observations
                    result=verify_observations(result,observations,job['production_binding'],generation,package.manifest_hash)
                displayed_calibration = candidate if job['request']['kind'] == 'calibrate' else job.get('calibration')
                if job.get('experiment_policy'):
                    result.update(job['experiment_policy'])
                    result['visibility_policy']='EXPERIMENT_SESSION_NOT_PER_FRAME_HAND_EVIDENCE'
                if motion_mode:
                    first=observations[0]['freshness']['estimated_source_monotonic']
                    third=observations[-1]['freshness']['estimated_source_monotonic']
                    request_at=job['production_binding']['request_accepted_monotonic']
                    result.update(conveyor_frame_rejections=conveyor_rejections,
                        request_to_first_valid_frame_ms=(first-request_at)*1000,
                        first_to_third_valid_frame_ms=(third-first)*1000,
                        request_to_third_valid_frame_ms=(third-request_at)*1000,
                        inspection_valid_frame_fps=2/(third-first) if third>first else None)
                progress('CONSENSUS_AND_EVIDENCE_ENCODING')
                result.update(observations=observations,calibration_candidate=candidate,
                              calibration_used=displayed_calibration,backend=backend,
                              inference_ms=sum(item["inference_ms"] for item in observations),
                              worker_total_ms=(time.monotonic()-job["accepted_monotonic"])*1000,
                              visibility_limit=("자동 긍정 슬롯 근거만 사용; 미검출의 누락/가림 구분 미검증" if bound else
                                                "Human-assisted visibility; automatic occlusion/orientation recognition unverified"))
                if stationary_capture:
                    result['stationary_capture'] = stationary_evidence(observations)
                encoding_started=perf_counter()
                images = encode_evidence(frames,observations,package.recipe,displayed_calibration,result=result)
                result['evidence_encoding_ms']=(perf_counter()-encoding_started)*1000
                result['request_to_three_frames_ms']=three_frames_ms
                result['representative_frame_id']=frames[-1].frame_id
                if any(hashlib.sha256(f.image.tobytes()).hexdigest() != o['input_pixel_sha256'] for f,o in zip(frames,observations)):
                    raise RuntimeError('EVIDENCE_INPUT_MUTATED')
                if selector:
                    check_processing()
                    result['fresh_frame'] = fresh_evidence(observations)
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],"result":result,"images":images},timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
            except Exception as error:
                if stationary_capture and stationary_candidates:
                    # Preserve bounded, real originals on failure. They are
                    # diagnostic evidence, never a replacement successful trio.
                    frames = [item[0] for item in stationary_candidates]
                    observations = [item[1] for item in stationary_candidates]
                insufficient=(motion_mode and isinstance(error,FreshFrameError)
                              and error.reason=='DEADLINE_EXCEEDED' and len(frames)<3)
                if insufficient:
                    from src.vision.engine_inspector import conveyor_incomplete_result
                    failure=conveyor_incomplete_result(observations,conveyor_rejections)
                else:
                    failure={"decision":"ERROR","reason":f"{type(error).__name__}: {error}","defects":[],"unassessed":[]}
                failure['observations']=observations
                if stationary_capture:
                    failure['stationary_capture'] = stationary_evidence(observations)
                if not insufficient:
                    failure['reason_code']=str(error)
                failure_images=[]
                stationary_expired = (stationary_capture and isinstance(error, FreshFrameError)
                                      and error.reason == 'DEADLINE_EXCEEDED')
                if engine and frames and (insufficient or stationary_expired or not isinstance(error,(FreshFrameError,TimeoutError))) and not cancellation.is_set() and not stopping.is_set():
                    try:failure_images=encode_evidence(frames,observations,package.recipe,job.get('calibration'),result=failure)
                    except Exception as evidence_error:failure['evidence_error']=str(evidence_error)
                if failure['decision']!='ERROR' and not any(image['kind']=='raw' for image in failure_images):
                    failure.update(decision='ERROR',reason='CONVEYOR_ORIGINAL_EVIDENCE_UNAVAILABLE',
                                   reason_code='CONVEYOR_ORIGINAL_EVIDENCE_UNAVAILABLE')
                if selector:
                    failure['fresh_frame'] = fresh_evidence(observations)
                    if insufficient:
                        failure['capture_stop_reason']=error.reason
                    else:
                        failure['reason_code'] = error.reason if isinstance(error, FreshFrameError) else str(error)
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],
                             "result":failure,"images":failure_images},timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
                if isinstance(error, FatalDetectorError):
                    # Same FIFO: Service durably handles ERROR before entering recovery.
                    raise
    except Exception as error:
        primary_error = error
        try:
            results.put({"type":"fault","generation":generation,"error":f"{type(error).__name__}: {error}"},timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
        except queue.Full:
            pass
    finally:
        diagnostic.stop('WORKER_STOP')
        diagnostic.wait(3)
        stopping.set()
        cleanup_errors = []
        for name, resource in (("camera", camera), ("engine",engine), ("detector", detector)):
            # Generic legacy Detector implementations need not own native resources.
            # Factory-created RuntimeDetectors implement close explicitly.
            close = getattr(resource, "close", None)
            if close is None:
                continue
            try:
                close()
            except Exception as error:
                cleanup_errors.append(f"{name}: {type(error).__name__}: {error}")
                logging.getLogger(__name__).exception("Worker %s cleanup failed", name)
        if cleanup_errors and primary_error is None:
            try:
                results.put({"type":"fault", "generation":generation,
                             "error":"WORKER_CLEANUP_FAILED: " + "; ".join(cleanup_errors)}, timeout=parameters.WORKER_RESULT_QUEUE_TIMEOUT_SECONDS)
            except queue.Full:
                pass
