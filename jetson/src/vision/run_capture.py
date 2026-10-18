"""Opt-in operating diagnostics owned by the existing camera Worker.

Acquisition only copies bounded raw pixels and already-computed metadata.
Encoding and file writes require a renewable STOP/idle lease from Runtime.
No inference, camera open, inspection command, or PLC write lives here.
"""
from src import config as parameters
import hashlib
import json
import math
from pathlib import Path
import shutil
import threading
import time

import cv2
import numpy as np

from src.vision.diagnostic_capture import DiagnosticCapture, RESERVE_BYTES, validate_request

MEMORY_RESERVE = parameters.RUN_CAPTURE_MEMORY_RESERVE
SCRATCH_BYTES = parameters.RUN_CAPTURE_SCRATCH_BYTES
BOOKKEEPING_BYTES = parameters.RUN_CAPTURE_BOOKKEEPING_BYTES
MAX_IMAGE_BYTES = parameters.RUN_CAPTURE_MAX_IMAGE_BYTES


def part_inference_provenance(observation):
    """No detections and inference skipped are different diagnostic evidence."""
    elapsed=observation.get('engine_dynamic',{}).get('stage_timings_ms',{}).get('part_detection_ms')
    return dict(parts_computation='COMPUTED' if elapsed is not None else 'NOT_COMPUTED',
        part_inference_input=observation.get('part_inference_input'),
        part_input_transform=observation.get('part_input_transform'))


class RunCaptureSignals:
    """Single Runtime writer; lock-free scalar reads never occupy request queues."""
    def __init__(self, context):
        self.started_at = context.RawValue('d', 0.)
        self.stop_code = context.RawValue('i', 0)
        self.flush_until = context.RawValue('d', 0.)

    def reset(self):
        self.started_at.value = self.flush_until.value = 0.
        self.stop_code.value = 0


def validate_run_request(body):
    if set(body)-{'clip_id','duration_seconds','max_frames','max_bytes','condition'}:
        raise ValueError('UNKNOWN_RUN_CAPTURE_INPUT')
    request = dict(duration_seconds=parameters.RUN_CAPTURE_SECONDS, max_frames=parameters.RUN_CAPTURE_FRAMES, max_bytes=parameters.RUN_CAPTURE_BYTES)
    request.update(body)
    for key, maximum in (('duration_seconds',parameters.RUN_CAPTURE_SECONDS),('max_frames',parameters.RUN_CAPTURE_FRAMES),('max_bytes',parameters.RUN_CAPTURE_BYTES)):
        value = request[key]
        if type(value) not in (int,float) or not math.isfinite(value) or not 1 <= value <= maximum:
            raise ValueError('RUN_CAPTURE_LIMIT:'+key)
    return validate_request(request)


class RunCapture(DiagnosticCapture):
    requires_tensor = False

    def start(self, folder, request, context, *, signals, encoder=None,
              free_bytes=None, memory_available=None):
        if self.phase != 'IDLE' or context.get('run_capture_approved') is not True:
            raise ValueError('RUN_CAPTURE_NOT_AUTHORIZED_OR_ALREADY_USED')
        request = validate_run_request(request)
        if request['max_bytes'] <= SCRATCH_BYTES+BOOKKEEPING_BYTES:
            raise ValueError('RUN_CAPTURE_MEMORY_BUDGET_TOO_SMALL')
        available = memory_available
        if available is None and Path('/proc/meminfo').exists():
            available = next(int(line.split()[1])*1024 for line in
                Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
        total_budget=context.get('conditions',{}).get('total_memory_limit_bytes',request['max_bytes'])
        if available is not None and available < max(total_budget,request['max_bytes'])+MEMORY_RESERVE:
            raise OSError('RUN_CAPTURE_MEMORY_RESERVE_REQUIRED')
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(self.folder).free if free_bytes is None else free_bytes
        if free < RESERVE_BYTES+request['max_bytes']:
            raise OSError('CAPTURE_DISK_RESERVE_REQUIRED')
        shape=context.get('raw_shape')
        if (not isinstance(shape,(list,tuple)) or len(shape)!=3 or shape[2]!=3
                or any(type(v) is not int or v<=0 for v in shape) or math.prod(shape)>MAX_IMAGE_BYTES):
            raise ValueError('RUN_CAPTURE_VERIFIED_RAW_SHAPE_REQUIRED')
        # Touch each page during STOP. Per-frame allocation/page faults can
        # otherwise consume the capture hook's 5 ms budget on the Jetson.
        metadata_per_frame=16384+65536+2048
        capacity=min(request['max_frames'],(request['max_bytes']-SCRATCH_BYTES-BOOKKEEPING_BYTES)//
                     (math.prod(shape)+metadata_per_frame))
        if capacity<1: raise ValueError('RUN_CAPTURE_MEMORY_BUDGET_TOO_SMALL')
        self._pool=np.empty((capacity,*shape),dtype=np.uint8)
        self._pool.fill(0)
        self.preallocated_raw_bytes=self._pool.nbytes
        self.request, self.context, self.signals = request, context, signals
        self.max_frames, self.max_bytes = request['max_frames'], request['max_bytes']
        self.armed_at = time.monotonic()
        self.started_monotonic = None
        self.deadline = self.armed_at+60
        self._images = {}
        self._metadata_bytes = 0
        self._last_pts = None
        self.pre_start_frames = 0
        self.encoder = encoder or (lambda image: cv2.imencode('.png',image,
            [cv2.IMWRITE_PNG_COMPRESSION,1,cv2.IMWRITE_PNG_STRATEGY,cv2.IMWRITE_PNG_STRATEGY_RLE]))
        # Preparation runs while physically stopped. No payload IO during RUN.
        with (self.folder/'request.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(request=request, context=context, armed_monotonic=self.armed_at,
                payload_policy='MEMORY_UNTIL_RENEWABLE_SAFE_STOP_LEASE',
                memory_available_bytes=available, free_bytes=free),stream,indent=2)
        (self.folder/'raw').mkdir()
        (self.folder/'outputs').mkdir()
        self.phase = 'ARMED'

    def tick(self, now=None):
        if self.phase == 'IDLE': return
        now = time.monotonic() if now is None else now
        if self.phase == 'ARMED':
            started = self.signals.started_at.value
            if started:
                if not self.armed_at <= started <= now or started > self.deadline:
                    self._reject('INVALID_START_TIME')
                else:
                    self.started_monotonic = started
                    self.deadline = started+self.request['duration_seconds']
                    self.phase = 'RECORDING'
            elif now >= self.deadline:
                self.stop('ARM_TIMEOUT')
        if self.phase in ('ARMED','RECORDING') and self.signals.stop_code.value:
            self.stop('RUNTIME_STOP_'+str(self.signals.stop_code.value))
        if self.recording and now >= self.deadline:
            self.stop('TIME_LIMIT')
        if self.phase == 'WAIT_SAFE_FLUSH' and self.signals.flush_until.value > now:
            self.permit_flush()

    def _reject(self, reason):
        self.error = reason
        self.stop(reason)

    def capture(self, frame_id, image, freshness):
        self.tick()
        if not self.recording: return
        started = time.perf_counter()
        try:
            if frame_id in self.rows:
                self.duplicate_frame_ids += 1
                self._reject('DUPLICATE_FRAME_ID'); return
            if len(self.rows) >= self.max_frames:
                self.stop('FRAME_LIMIT'); return
            if freshness.get('camera_epoch') != self.context.get('camera_epoch'):
                self._reject('CAMERA_EPOCH_CHANGED'); return
            pts = freshness.get('source_pts_ns')
            source = freshness.get('estimated_source_monotonic')
            if type(pts) is not int or (self._last_pts is not None and pts <= self._last_pts):
                self._reject('SOURCE_PTS_NOT_INCREASING'); return
            if not isinstance(source,(int,float)) or not math.isfinite(source):
                self._reject('SOURCE_TIME_INVALID'); return
            if source < self.started_monotonic:
                self.pre_start_frames += 1; return
            if source >= self.deadline:
                self.stop('TIME_LIMIT'); return
            if image.dtype.name != 'uint8' or image.ndim != 3 or image.shape[2] != 3:
                self._reject('RAW_FORMAT_INVALID'); return
            if tuple(image.shape)!=tuple(self.context['raw_shape']):
                self._reject('RAW_SHAPE_CHANGED'); return
            if image.nbytes > MAX_IMAGE_BYTES:
                self.stop('IMAGE_BYTES_LIMIT'); return
            metadata = json.dumps(freshness,allow_nan=False)
            if len(metadata) > 16384:
                self._reject('FRESHNESS_METADATA_LIMIT'); return
            projected = self.preallocated_raw_bytes+self._metadata_bytes+len(metadata)+SCRATCH_BYTES+BOOKKEEPING_BYTES
            if projected > self.max_bytes or len(self.rows)>=len(self._pool):
                self.stop('BYTE_LIMIT'); return
            pixels = self._pool[len(self.rows)]
            np.copyto(pixels,image)
            pixels.flags.writeable = False
            row = dict(frame_id=frame_id, shape=list(image.shape), dtype='uint8', color='BGR',
                raw_path=f'raw/{len(self.rows):06d}.png', raw_status='BUFFERED',
                observation_status='NOT_PROCESSED', tensor_status='NOT_REQUESTED',
                captured_monotonic=time.monotonic(), _freshness_json=metadata, _observation_json=None)
            self._images[frame_id] = pixels
            self.rows[frame_id] = row
            self.buffered_bytes += image.nbytes
            self._metadata_bytes += len(metadata)
            self.buffered_frames += 1
            self._last_pts = pts
        except Exception as error:
            self._reject('RAW_CAPTURE:'+type(error).__name__+':'+str(error))
        finally:
            elapsed = (time.perf_counter()-started)*1000
            self.hook_ms.append(elapsed)
            self.hook_ms = self.hook_ms[-(self.max_frames+1):]
            if elapsed > 5 and self.recording:
                self.stop('CAPTURE_HOOK_OVER_5MS')

    def observe(self, frame_id, observation, tensor=None):
        row = self.rows.get(frame_id)
        if row is None or self.phase not in ('RECORDING','WAIT_SAFE_FLUSH'): return
        started = time.perf_counter()
        try:
            if observation.get('frame_id') != frame_id or observation.get('generation') != self.context['worker_generation']:
                self._reject('OBSERVATION_IDENTITY_CHANGED'); return
            encoded = json.dumps(observation,allow_nan=False)
            if len(encoded) > 65536 or row['_observation_json'] is not None:
                self._reject('OBSERVATION_METADATA_LIMIT_OR_DUPLICATE'); return
            if self.preallocated_raw_bytes+self._metadata_bytes+len(encoded)+SCRATCH_BYTES+BOOKKEEPING_BYTES > self.max_bytes:
                self.stop('BYTE_LIMIT'); return
            row['_observation_json'] = encoded
            row['observation_status'] = 'PROCESSED'
            self._metadata_bytes += len(encoded)
        except Exception as error:
            self._reject('OBSERVATION:'+type(error).__name__+':'+str(error))
        finally:
            if (time.perf_counter()-started)*1000 > 5 and self.recording:
                self.stop('OBSERVATION_HOOK_OVER_5MS')

    def stop(self, reason='OPERATOR_STOP'):
        if self.phase in ('ARMED','RECORDING'):
            self.stop_reason = reason
            self.phase = 'WAIT_SAFE_FLUSH'
            self.closing.set()

    def permit_flush(self):
        if self.phase == 'WAIT_SAFE_FLUSH' and self.thread is None:
            self.phase = 'SAVING'
            self.thread = threading.Thread(target=self._flush, name='stopped-run-capture-writer',daemon=True)
            self.thread.start()

    def _wait_safe(self):
        while self.signals.flush_until.value <= time.monotonic():
            time.sleep(.02)

    def _write_safe(self, path, data):
        self._wait_safe()
        with path.open('xb') as stream:
            self._write_chunks(stream,data)

    def _write_chunks(self, stream, data):
        for start in range(0,len(data),65536):
            self._wait_safe()
            stream.write(data[start:start+65536])

    def _save_frame(self, frame_id, row):
        self._wait_safe()
        image = self._images[frame_id]
        row['pixel_sha256'] = hashlib.sha256(image.tobytes()).hexdigest()
        before = time.perf_counter()
        ok, encoded = self.encoder(image)
        if not ok: raise OSError('PNG_ENCODE_FAILED')
        data = encoded.tobytes()
        row['raw_sha256'] = hashlib.sha256(data).hexdigest()
        row['raw_timing_ms'] = {'encode':(time.perf_counter()-before)*1000}
        self._wait_safe()
        if shutil.disk_usage(self.folder).free < RESERVE_BYTES+len(data):
            raise OSError('CAPTURE_DISK_RESERVE_REACHED')
        self._write_safe(self.folder/row['raw_path'],data)
        row['raw_status'] = 'SAVED'
        self.bytes_written += len(data)
        self.saved_frames += 1
        self.buffered_bytes -= image.nbytes
        self.buffered_frames -= 1
        del self._images[frame_id]

    def _flush(self):
        try:
            self._wait_safe()
            with (self.folder/'frames.jsonl').open('xb') as stream:
                for frame_id, row in self.rows.items():
                    self._save_frame(frame_id,row)
                    # Keep only one serialized record in scratch space. Expanding
                    # every observation into Python objects exceeds its byte budget.
                    freshness = row['_freshness_json']
                    observation = row['_observation_json']
                    summary = {key:value for key,value in row.items() if not key.startswith('_')}
                    record = (json.dumps(summary,allow_nan=False)[:-1]
                        + ',"freshness":'+freshness+',"observation":'+(observation or 'null')+'}\n')
                    self._write_chunks(stream,record.encode('utf-8'))
                    self._metadata_bytes -= len(freshness)+len(observation or '')
                    del row['_freshness_json'],row['_observation_json']
            final_phase = 'ERROR' if self.error else 'SAVED'
            self._write_safe(self.folder/'receipt.json',json.dumps(dict(self.status(), state=final_phase,
                context=self.context, request=self.request, capture_hook_ms=self.hook_ms,
                started_monotonic=self.started_monotonic, finished_monotonic=time.monotonic(),
                payload_write_policy='RENEWABLE_SAFE_STOP_LEASE',
                acquired_source='EXISTING_SINGLE_CAMERA_WORKER',
                sensor_frames_not_delivered='UNMEASURED; inspect source PTS gaps'),indent=2).encode())
            self._pool=None
            self.phase = final_phase
        except Exception as error:
            self.error = type(error).__name__+':'+str(error)
            self.phase = 'ERROR'
            # Never claim successful save, delete partial evidence or fail the camera.

    def wait(self, seconds):
        if self.thread: self.thread.join(seconds)
        return self.phase in ('SAVED','ERROR') and (self.thread is None or not self.thread.is_alive())

    def status(self):
        value = super().status()
        value.update(mode='RUN_DIAGNOSTIC', memory_payload_bytes=self.buffered_bytes,
            preallocated_raw_bytes=getattr(self,'preallocated_raw_bytes',0),
            memory_metadata_bytes=getattr(self,'_metadata_bytes',0),
            memory_reserve_bytes=MEMORY_RESERVE, pre_start_frames=getattr(self,'pre_start_frames',0),
            volatile_until_saved=True, tensor_policy='NOT_REQUESTED')
        return value
