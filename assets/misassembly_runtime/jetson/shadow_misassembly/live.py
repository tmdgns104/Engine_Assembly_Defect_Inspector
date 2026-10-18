"""Bounded shadow bench: existing camera/envelope/tracker, independent classifier.

No production service, decision aggregator, PLC gateway or actuator is constructed.
This entrypoint belongs to the integrated project; it is verified in temporary staging.
"""
import argparse
from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

from offline import ROOT, BASELINE, CONFIG, PARTS, RecoveryPreprocessor, FixedPredictor, YOLO, cv2, torch, sync, write_image, sha
from policy import aggregate_frame
from live_observation import ThreeFrameObservation
from robustness import safe_inspection_zone, ShadowTrackRecovery
from src.camera.gstreamer_camera import GStreamerCamera
from src.camera.continuous import ContinuousFrames
from src.recipe.package import load_package
from src.vision.engine_inspector import EngineInspector
from src.quality.image import assess_image
from src.runtime.production_profile import tracker_config
from src.tracking.single_active import SingleActiveTracker
from src.tracking.contracts import TrackingFrame, ProductObservation, NormalizedBox


def write_json(path, value):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class ShadowModels:
    def __init__(self, *, robustness=False):
        assert torch.cuda.is_available(), 'CUDA_REQUIRED'
        if robustness:
            from robust_preprocessing import RobustShadowPreprocessor
            self.processor = RobustShadowPreprocessor(CONFIG)
        else:
            self.processor = RecoveryPreprocessor(CONFIG)
        self.robustness = robustness
        self.models = {part: YOLO(str(BASELINE/'full'/part/'weights/best.pt')) for part in PARTS}
        self.mappings = {p: {str(k): v for k, v in m.names.items()} for p, m in self.models.items()}
        for part in PARTS:
            assert self.mappings[part] == json.loads((BASELINE/'full'/part/'class_mapping.json').read_text())
        self.timings = {}
        for owner, name, key in [(self.processor.detector, 'predict', 'detection_ms'),
                                  (self.processor.estimator, '_estimate', 'pose_matching_ms'),
                                  (self.processor, 'extract', 'crop_ms')]:
            self._instrument(owner, name, key)

    def _instrument(self, owner, name, key):
        original = getattr(owner, name)
        def measured(*args, **kwargs):
            sync(); started = time.perf_counter()
            try: return original(*args, **kwargs)
            finally:
                sync(); self.timings[key] = self.timings.get(key, 0) + (time.perf_counter()-started)*1000
        setattr(owner, name, measured)

    def process(self, image):
        self.timings.clear(); sync(); started = time.perf_counter()
        preprocessing, canonical, crops = self.processor.process(image)
        pose = preprocessing.get('pose', {})
        zone = safe_inspection_zone(self.processor.cfg, pose.get('matrix') if pose.get('ok') else None,
                                    (image.shape[1], image.shape[0]))
        sync(); preprocessing_ms = (time.perf_counter()-started)*1000
        record = dict(preprocessing=preprocessing, parts={}, safe_inspection_zone=zone)
        # In robustness mode an incomplete essential footprint is guidance, not a
        # reason to classify remaining slots. Crops stay available as evidence.
        can_classify = not self.robustness or (zone['inside'] and preprocessing['status']=='VALID')
        for part in PARTS:
            value = dict(valid=part in crops and can_classify, predicted_state=None, class_scores=None,
                         class_mapping=self.mappings[part])
            if part in crops and can_classify:
                sync(); step = time.perf_counter()
                prediction = self.models[part].predict([crops[part]], predictor=FixedPredictor,
                    imgsz=224, device=0, quantize=32, verbose=False)[0]
                sync(); self.timings[part+'_ms'] = (time.perf_counter()-step)*1000
                scores = prediction.probs.data.cpu().numpy()
                value.update(predicted_state=self.mappings[part][str(int(scores.argmax()))],
                    class_scores={self.mappings[part][str(i)]: float(v) for i, v in enumerate(scores)},
                    pixel_sha256=hashlib.sha256(crops[part].tobytes()).hexdigest())
            record['parts'][part] = value
        sync(); self.timings['total_inspection_ms'] = (time.perf_counter()-started)*1000
        self.timings['alignment_and_preprocess_other_ms'] = preprocessing_ms-self.timings.get('detection_ms',0)-self.timings.get('crop_ms',0)
        record['timings_ms'] = dict(self.timings)
        record['shadow_state'] = aggregate_frame(record)
        return record, canonical, crops


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--port', type=int, default=18872)
    parser.add_argument('--robustness', action='store_true', help='Opt-in experimental shadow guidance/re-acquisition')
    args = parser.parse_args()
    assert 1 <= args.seconds <= 3600, 'Bounded session required'
    gate = json.loads((ROOT/'offline_gate.json').read_text())
    assert gate['offline_gate_passed'] and gate['samples'] == 155, 'OFFLINE_PARITY_REQUIRED'
    if args.robustness:
        robustness_gate = json.loads((ROOT/'robustness_gate.json').read_text())
        assert robustness_gate['offline_regression_passed'], 'ROBUSTNESS_OFFLINE_REGRESSION_REQUIRED'
    args.output.mkdir(parents=True, exist_ok=False)
    station = json.loads((ROOT/'config/station.json').read_text())
    package = load_package(ROOT/'assets/products/ENGINE_Z3005_5/dynamic_parts_005')
    (args.output/'index.html').write_text(Path(__file__).with_name('live.html').read_text(encoding='utf-8'), encoding='utf-8')
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw): super().__init__(*a, directory=str(args.output), **kw)
        def log_message(self, *a): pass
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stop = threading.Event(); camera = None; engine = None; start = time.monotonic()
    counter = dict(camera=0, tracking=0, inspections=0)
    status = dict(status='LOADING', shadow_state='REVIEW', production='NOT_RUN', plc_output=False)
    write_json(args.output/'status.json', status)
    try:
        models = ShadowModels(robustness=args.robustness); engine = EngineInspector(package)
        zone = dict(polygon_normalized=[[0,0],[1,0],[1,1],[0,1]], entry_policy='product_center')
        tracker = (ShadowTrackRecovery if args.robustness else SingleActiveTracker)(tracker_config(zone))
        history = ThreeFrameObservation(); last_inspection = -1.; last_record = None
        tracking_times = deque(maxlen=300)
        def received(frame, metadata): counter['camera'] += 1
        camera = ContinuousFrames(GStreamerCamera(dict(package.capture, device=station['camera_device'])), stop, received)
        assert (camera.camera.width, camera.camera.height) == (1280,720), 'RECOVERY_RESOLUTION_MISMATCH'
        ready_at = time.monotonic()
        write_json(args.output/'session.json', dict(mode='SHADOW_ONLY', production='NOT_RUN', plc_output=False,
            camera_config=package.capture, tracker_config=asdict(tracker.config), source='existing integrated camera/envelope/tracker code',
            trigger='one new frame at most once per second when existing tracker INSPECTION_READY; no production completion emitted',
            visibility_limit='Global quality only; per-slot hand occlusion not proven; difficult-condition tests required',
            confidence_policy='Frozen argmax, no new operating threshold; uncalibrated confidence retained',
            models={p:sha(BASELINE/'full'/p/'weights/best.pt') for p in PARTS}, config_sha256=sha(CONFIG)))
        while time.monotonic()-start < args.seconds and not (args.output/'STOP').exists():
            frame = camera.capture(); metadata = dict(camera.frame_info)
            quality = assess_image(frame.image, station['quality'])
            observation = dict(quality=quality, freshness=metadata)
            detection = engine.observe_product(frame, observation)
            products = detection['products']
            boxes = tuple(ProductObservation(NormalizedBox(*[max(0.,min(1.,d['bounding_box'][k]/scale)) for k,scale in
                 [('x1',frame.width),('y1',frame.height),('x2',frame.width),('y2',frame.height)]]), 'EXISTING_ENGINE_ENVELOPE') for d in products)
            tracking_frame = TrackingFrame(frame.frame_id, metadata['sequence'], metadata['estimated_source_monotonic'], boxes)
            tracked = tracker.step(tracking_frame, quality_valid=quality['valid'] and metadata['integrity']['valid']) if args.robustness else tracker.step(tracking_frame)
            if args.robustness:
                with (args.output/'tracking_observations.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                        frame=asdict(tracking_frame),quality_valid=quality['valid'],update=asdict(tracked),
                        recovery=tracker.last_event))+'\n')
            counter['tracking'] += 1; tracking_times.append(time.monotonic())
            now = time.monotonic()
            # The baseline keeps LOST sticky. The opt-in adapter retires a lost ID
            # only after three fresh coherent observations, assigning a new ID.
            eligible = tracked.state.value == 'INSPECTION_READY' and quality['valid'] and metadata['integrity']['valid']
            if eligible and now-last_inspection >= 1.0 and counter['inspections'] < 500:
                last_inspection = now
                record, canonical, crops = models.process(frame.image)
                declaration_path = args.output/'scenario.json'
                declaration = json.loads(declaration_path.read_text()) if declaration_path.exists() else None
                record.update(timestamp=datetime.now(timezone.utc).isoformat(), frame_id=frame.frame_id,
                    source_pts_ns=metadata['source_pts_ns'], camera_epoch=metadata['camera_epoch'], track_id=tracked.active_track_id,
                    raw_pixel_sha256=hashlib.sha256(frame.image.tobytes()).hexdigest(), quality=quality,
                    human_declared_test_state=declaration, scenario_id=declaration.get('scenario') if declaration else 'PREFLIGHT_UNDECLARED',
                    existing_production_result='NOT_RUN', tracking_detection=detection,
                    timing_scope='Jetson inference GPU synchronized; file encoding/write excluded')
                compact = dict(record, parts={p:{'predicted_state':v['predicted_state']} for p,v in record['parts'].items()})
                record['three_frames'] = history.add(compact)
                folder = args.output/'evidence'/frame.frame_id; folder.mkdir(parents=True)
                record['raw_sha256'] = write_image(folder/'raw.png', frame.image)
                record['raw_path'] = str((folder/'raw.png').relative_to(args.output))
                if canonical is not None:
                    write_image(folder/'canonical.png', canonical); record['canonical_path'] = str((folder/'canonical.png').relative_to(args.output))
                for part, crop in crops.items():
                    record['parts'][part]['crop_sha256'] = write_image(folder/(part+'.png'), crop)
                    record['parts'][part]['crop_path'] = str((folder/(part+'.png')).relative_to(args.output))
                counter['inspections'] += 1
                with (args.output/'observations.jsonl').open('a',encoding='utf-8') as stream: stream.write(json.dumps(record)+'\n')
                last_record = record
            current_state = last_record['shadow_state'] if last_record and last_record['track_id'] == tracked.active_track_id and eligible else 'REVIEW'
            # Never display a previous PASS as current when tracking/quality/pose evidence is stale.
            if not last_record or now-last_inspection > 2: current_state = 'REVIEW'
            overlay = frame.image.copy()
            if args.robustness and last_record and now-last_inspection<=2:
                safe = last_record['safe_inspection_zone']
                bounds = safe.get('center_bounds_xyxy')
                if bounds and bounds[0]<=bounds[2] and bounds[1]<=bounds[3]:
                    cv2.rectangle(overlay,tuple(round(v) for v in bounds[:2]),tuple(round(v) for v in bounds[2:]),(0,200,80),2)
                cv2.putText(overlay,'SAFE INSPECTION ZONE: '+', '.join(safe['guidance']),(15,65),0,.65,(0,200,80),2)
            for item in products:
                box=item['bounding_box'];x1,y1,x2,y2=[round(box[k]) for k in ['x1','y1','x2','y2']]
                cv2.rectangle(overlay,(x1,y1),(x2,y2),(0,210,240),2)
                cv2.putText(overlay,f"Track {tracked.active_track_id} envelope {item['confidence']:.3f}",(x1,max(25,y1)),0,.65,(0,210,240),2)
            cv2.putText(overlay,'SHADOW '+current_state+' / PLC OFF',(15,35),0,.85,(0,210,240),2)
            ok, encoded=cv2.imencode('.jpg',overlay,[cv2.IMWRITE_JPEG_QUALITY,85]);assert ok
            (args.output/'preview.pending').write_bytes(encoded.tobytes());(args.output/'preview.pending').replace(args.output/'preview.jpg')
            elapsed=max(time.monotonic()-ready_at,.001)
            status=dict(status='RUNNING', shadow_state=current_state, tracker=asdict(tracked), frame_id=frame.frame_id,
                timestamp=datetime.now(timezone.utc).isoformat(), latest_inspection=last_record, quality=quality,
                rates=dict(camera_fps=counter['camera']/elapsed,tracking_fps=counter['tracking']/elapsed,
                    inspection_trigger_hz=counter['inspections']/elapsed), counts=dict(counter), production='NOT_RUN', plc_output=False)
            write_json(args.output/'status.json',status)
            time.sleep(.05)
    except Exception as error:
        status.update(status='ERROR',shadow_state='ERROR',error=type(error).__name__+': '+str(error))
        write_json(args.output/'status.json', status)
        raise
    finally:
        stop.set()
        if camera is not None: camera.close()
        if engine is not None: engine.close()
        server.shutdown()
        write_json(args.output/'stopped.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),counts=counter,status=status))


if __name__ == '__main__': main()
