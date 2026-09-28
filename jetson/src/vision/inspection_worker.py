"""Persistent camera/model owner. Inspection durability stays in the Service.

Optional bounded diagnostic raw files are separate from inspection/Journal data.
"""

import queue
import threading
import time
from time import perf_counter
import socket
import logging
import hashlib
from datetime import datetime, timezone

from src.camera.fresh_frame import FreshFrameError, FreshFrameSelector, TriggerContext
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


def worker_main(package_root, station, generation, commands, results, previews, stopping, cancellation, heartbeat, products=None, production_tracking=None):
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
        if time.monotonic()-last_preview < .1:
            return
        preview_image=frame.image
        if observation and observation.get('engine_dynamic'):
            from src.vision.engine_inspector import draw_engine_overlay
            preview_image=draw_engine_overlay(frame.image,observation)
        ok, jpeg = cv2.imencode('.jpg',preview_image,[cv2.IMWRITE_JPEG_QUALITY,75])
        if not ok:
            raise RuntimeError('PREVIEW_ENCODING_FAILED')
        jpeg_no_slots=jpeg
        if observation and observation.get('engine_dynamic'):
            ok,jpeg_no_slots=cv2.imencode('.jpg',draw_engine_overlay(frame.image,observation,show_slots=False),[cv2.IMWRITE_JPEG_QUALITY,75])
            if not ok:raise RuntimeError('PREVIEW_ENCODING_FAILED')
        put_latest(previews,{'jpeg':jpeg.tobytes(),'jpeg_no_slots':jpeg_no_slots.tobytes(),'generation':generation,'freshness':metadata,
            'scene':observation.get('engine_dynamic') if observation else None,
            'area_occupancy':observation.get('area_occupancy') if observation else None,
            'diagnostic_capture':diagnostic.status()})
        last_preview = time.monotonic()

    def detect_frame(frame, freshness, *, inspection=False):
        if engine:
            engine.detector.capture_diagnostics = diagnostic.recording
        before = hashlib.sha256(frame.image.tobytes()).hexdigest()
        integrity = freshness.get('integrity', {'valid':True})
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
            input_pixel_sha256=before)
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
                products_for_record = [d for d in detected['detections'] if d['class_name']=='product_envelope']
                gate = engine.estimator.cfg['decision_policy']['product_confidence']
                diagnostic.observe(frame.frame_id, dict(frame_id=frame.frame_id,
                    processed_monotonic=time.monotonic(), inspection=inspection,
                    mode='PRODUCTION_TRACKING' if production_tracking is not None and production_tracking.is_set() and not inspection else 'FULL_INSPECTION_PATH',
                    generation=generation, package_sha256=package.manifest_hash,
                    input_pixel_sha256=before, detections=products_for_record,
                    provider=envelope_provider(products_for_record,frame.width,frame.height,gate).to_dict(),
                    product_confidence_threshold=gate, engine=detected['engine_dynamic'],
                    production_packet_emitted=packet is not None),
                    getattr(engine.detector,'diagnostic_output',None))
            preview_frame(frame,freshness,detected)
        return detected,packet

    def capture_frame():
        diagnostic.tick()
        value = camera.capture()
        diagnostic.capture(value.frame_id, value.image, dict(camera.frame_info))
        return value
    def pulse():
        while not stopping.wait(.5):
            heartbeat.value = time.monotonic()
    threading.Thread(target=pulse, daemon=True).start()
    try:
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
        if engine:backend['envelope']=engine.detector.runtime_metadata()
        backend.update(hostname=socket.gethostname(), camera_pipeline=camera.pipeline_text,
                       load_self_test_ms=(time.monotonic()-start)*1000)
        # READY must not expose the parent's stale pre-spawn heartbeat. The pulse
        # thread's first update can occur after the service consumes this message.
        heartbeat.value = time.monotonic()
        results.put({"type": "ready", "generation": generation, "backend": backend}, timeout=2)
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
            if job.get('type') == 'diagnostic_capture':
                try:
                    if job['action'] == 'stop':
                        diagnostic.stop()
                    else:
                        if diagnostic.thread and not diagnostic.wait(0):
                            raise ValueError('CAPTURE_ALREADY_ACTIVE_OR_SAVING')
                        diagnostic = DiagnosticCapture()
                        diagnostic.start(job['folder'], job['request'], dict(
                            worker_generation=generation, camera_owner_pid=__import__('os').getpid(),
                            camera_pipeline=camera.pipeline_text, package_sha256=package.manifest_hash,
                            capture=package.capture, backend=backend, station=station,
                            conditions=job.get('context',{})))
                    results.put({'type':'diagnostic_capture','generation':generation,'status':diagnostic.status()}, timeout=2)
                except Exception as error:
                    results.put({'type':'diagnostic_capture','generation':generation,
                                 'status':dict(state='ERROR',error=str(error),clip_id=job.get('request',{}).get('clip_id'))},timeout=2)
                continue
            observations, frames = [], []
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
                                                  station['max_frame_age_seconds'], station['frame_spacing_seconds'])
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
                    if bound:
                        from src.vision.auto_inspection import validate_bound_frame, automatic_coverage
                        bound = validate_bound_frame(bound,packet,profile)
                        detected['automatic_coverage'] = automatic_coverage(detected,package,job.get('calibration'),bound['bbox'],profile)
                        detected['auto_frame_binding'] = dict(bound)
                    # Inference may outlive the window or cancellation. Never publish that cycle.
                    if selector:
                        selector.check_active(time.monotonic(), stopping.is_set() or cancellation.is_set())
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
                progress('CONSENSUS_AND_EVIDENCE_ENCODING')
                result.update(observations=observations,calibration_candidate=candidate,
                              calibration_used=displayed_calibration,backend=backend,
                              inference_ms=sum(item["inference_ms"] for item in observations),
                              worker_total_ms=(time.monotonic()-job["accepted_monotonic"])*1000,
                              visibility_limit=("자동 긍정 슬롯 근거만 사용; 미검출의 누락/가림 구분 미검증" if bound else
                                                "Human-assisted visibility; automatic occlusion/orientation recognition unverified"))
                encoding_started=perf_counter()
                images = encode_evidence(frames,observations,package.recipe,displayed_calibration,result=result)
                result['evidence_encoding_ms']=(perf_counter()-encoding_started)*1000
                result['request_to_three_frames_ms']=three_frames_ms
                result['representative_frame_id']=frames[-1].frame_id
                if any(hashlib.sha256(f.image.tobytes()).hexdigest() != o['input_pixel_sha256'] for f,o in zip(frames,observations)):
                    raise RuntimeError('EVIDENCE_INPUT_MUTATED')
                if selector:
                    selector.check_active(time.monotonic(), stopping.is_set() or cancellation.is_set())
                    result['fresh_frame'] = selector.evidence()
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],"result":result,"images":images},timeout=2)
            except Exception as error:
                failure = {"decision":"ERROR","reason":f"{type(error).__name__}: {error}","defects":[],"unassessed":[]}
                failure['observations']=observations
                failure['reason_code']=str(error)
                failure_images=[]
                if engine and frames and not isinstance(error,(FreshFrameError,TimeoutError)) and not cancellation.is_set() and not stopping.is_set():
                    try:failure_images=encode_evidence(frames,observations,package.recipe,job.get('calibration'),result=failure)
                    except Exception as evidence_error:failure['evidence_error']=str(evidence_error)
                if selector:
                    failure['fresh_frame'] = selector.evidence()
                    failure['reason_code'] = error.reason if isinstance(error, FreshFrameError) else str(error)
                results.put({"type":"result","generation":generation,"inspection_id":job["inspection_id"],
                             "result":failure,"images":failure_images},timeout=2)
                if isinstance(error, FatalDetectorError):
                    # Same FIFO: Service durably handles ERROR before entering recovery.
                    raise
    except Exception as error:
        primary_error = error
        try:
            results.put({"type":"fault","generation":generation,"error":f"{type(error).__name__}: {error}"},timeout=2)
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
                             "error":"WORKER_CLEANUP_FAILED: " + "; ".join(cleanup_errors)}, timeout=2)
            except queue.Full:
                pass
