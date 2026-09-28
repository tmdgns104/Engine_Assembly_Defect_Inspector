"""Bounded lossless diagnostics from the existing camera owner, never an inspector.

Only the Worker calls capture/observe/stop. One bounded writer thread owns files.
Missing raw/tensor payloads remain explicit records, never fabricated samples.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import threading
import time

import cv2
import numpy as np

RESERVE_BYTES = 512 * 1024 * 1024
# Default requests remain 512 MiB. An explicit 60-second HCAM clip may use
# up to 1 GiB only after the same Worker-memory and disk reserves pass.
MAX_ENCODED_BUFFER_BYTES = 1024 ** 3
# B03 measured a 1.38 s writer stall at 14 frames/s, with two payloads/frame.
# 64 pending items absorb that burst; at 1280x720 BGR this bounds pending raw
# payloads to 177 MB even if every item is an image (plus two in-flight items).
DEFAULT_QUEUE_ITEMS = 64


def validate_request(body):
    clip_id = body.get('clip_id', '')
    if not isinstance(clip_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', clip_id):
        raise ValueError('CLIP_ID_MUST_BE_1_TO_64_ASCII_LETTERS_DIGITS_DASH_UNDERSCORE')
    defaults = {'duration_seconds': 10, 'max_frames': 600, 'max_bytes': 512 * 1024 * 1024}
    limits = {'duration_seconds': (1, 60), 'max_frames': (1, 1200), 'max_bytes': (1, 1024 ** 3)}
    result = {'clip_id': clip_id}
    for key, default in defaults.items():
        value = body.get(key, default)
        low, high = limits[key]
        if type(value) not in (int, float) or not low <= value <= high:
            raise ValueError('INVALID_CAPTURE_LIMIT: ' + key)
        if key != 'duration_seconds' and type(value) is not int:
            raise ValueError('INTEGER_CAPTURE_LIMIT_REQUIRED: ' + key)
        result[key] = value
    condition = body.get('condition', 'UNCONFIRMED_BENCH_SCENE')
    if not isinstance(condition, str) or len(condition) > 500:
        raise ValueError('INVALID_CAPTURE_CONDITION')
    result['condition'] = condition
    return result


class DiagnosticCapture:
    def __init__(self):
        self.thread = None
        self.rows = {}
        self.phase = 'IDLE'
        self.error = None
        self.stop_reason = None
        self.saved_frames = self.dropped_raw_frames = self.bytes_written = 0
        self.bytes_reserved = 0
        self.buffered_payloads = []
        self.buffered_frames = 0
        self.buffered_bytes = 0
        self.duplicate_frame_ids = self.dropped_tensors = 0
        self.hook_ms = []
        self.encoder_ms = []
        self.queue_high_water = 0
        self.closing = threading.Event()
        self.lock = threading.RLock()

    @property
    def recording(self):
        return self.phase == 'RECORDING' and not self.closing.is_set()

    def start(self, folder, request, context, *, encoder=None, queue_size=DEFAULT_QUEUE_ITEMS, free_bytes=None, encoder_workers=2):
        if self.thread is not None:
            raise ValueError('CAPTURE_OBJECT_ALREADY_USED')
        request = validate_request(request)
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(self.folder).free if free_bytes is None else free_bytes
        if free < RESERVE_BYTES + request['max_bytes']:
            raise OSError('CAPTURE_DISK_RESERVE_REQUIRED')
        buffer_limit = min(request['max_bytes'], MAX_ENCODED_BUFFER_BYTES)
        # Target Jetson publishes MemAvailable. Keep an additional 512 MiB plus
        # the worst-case bounded raw queue free for the already-running Worker.
        memory_info = Path('/proc/meminfo')
        available = None
        if memory_info.exists():
            available = next(int(line.split()[1]) * 1024 for line in memory_info.read_text().splitlines()
                             if line.startswith('MemAvailable:'))
            if available < buffer_limit + RESERVE_BYTES + (queue_size + encoder_workers) * 1280 * 720 * 3:
                raise OSError('CAPTURE_MEMORY_RESERVE_REQUIRED')
        # Reservation prevents overwriting any past clip, including interrupted clips.
        with (self.folder / 'request.json').open('x', encoding='utf-8') as stream:
            json.dump({'request': request, 'context': context, 'free_bytes_at_start': free,
                       'encoded_buffer_limit_bytes': buffer_limit,
                       'memory_available_bytes_at_start': available}, stream, indent=2)
        (self.folder / 'raw').mkdir()
        (self.folder / 'outputs').mkdir()
        self.request = request
        self.context = context
        self.max_frames = request['max_frames']
        self.max_bytes = buffer_limit
        self.started_monotonic = time.monotonic()
        self.deadline = self.started_monotonic + request['duration_seconds']
        self.queue = queue.Queue(maxsize=queue_size)
        # Uncompressed PNG sustained ~38 MB/s and stalled the SD card in a longer
        # clip. Two bounded encoders keep lossless compression off the camera path
        # and reduce disk demand; this still requires the live overhead gate.
        self.encoder_workers=encoder_workers
        self.encoder = encoder or (lambda image: cv2.imencode('.png', image, [cv2.IMWRITE_PNG_COMPRESSION, 1,
            cv2.IMWRITE_PNG_STRATEGY,cv2.IMWRITE_PNG_STRATEGY_RLE]))
        self.phase = 'RECORDING'
        self.thread = threading.Thread(target=self._write, name='bounded-diagnostic-writer', daemon=True)
        self.thread.start()

    def tick(self, now=None):
        if self.recording and (time.monotonic() if now is None else now) >= self.deadline:
            self.stop('TIME_LIMIT')
        if self.error and self.recording:
            self.stop('WRITE_ERROR')

    def capture(self, frame_id, image, freshness):
        self.tick()
        if not self.recording:
            return
        started = time.perf_counter()
        if frame_id in self.rows:
            self.duplicate_frame_ids += 1
            return
        if len(self.rows) >= self.max_frames:
            self.stop('FRAME_LIMIT')
            return
        index = len(self.rows)
        row = {'frame_id': frame_id, 'freshness': copy.deepcopy(freshness),
               'captured_monotonic': time.monotonic(), 'shape': list(image.shape),
               'dtype': str(image.dtype), 'color': 'BGR', 'pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest(),
               'raw_path': f'raw/{index:06d}.png', 'raw_status': 'QUEUED', 'observation': None,
               'observation_status': 'NOT_PROCESSED', 'tensor_status': 'NOT_PROCESSED'}
        self.rows[frame_id] = row
        try:
            self.queue.put_nowait(('raw', row, image.copy()))
            self.queue_high_water = max(self.queue_high_water, self.queue.qsize())
        except queue.Full:
            row['raw_status'] = 'QUEUE_FULL'
            self.dropped_raw_frames += 1
        self.hook_ms.append((time.perf_counter() - started) * 1000)

    def observe(self, frame_id, observation, tensor=None):
        if observation.get('frame_id') != frame_id:
            raise ValueError('CAPTURE_OBSERVATION_FRAME_ID_MISMATCH')
        row = self.rows.get(frame_id)
        if row is None or self.closing.is_set():
            return
        row['observation'] = copy.deepcopy(observation)
        row['observation_status'] = 'PROCESSED'
        if tensor is not None:
            row['tensor_path'] = row['raw_path'].replace('raw/', 'outputs/').replace('.png', '.npy')
            row['tensor_status'] = 'QUEUED'
            try:
                self.queue.put_nowait(('tensor', row, np.array(tensor, copy=True)))
                self.queue_high_water = max(self.queue_high_water, self.queue.qsize())
            except queue.Full:
                row['tensor_status'] = 'QUEUE_FULL'
                self.dropped_tensors += 1

    def stop(self, reason='OPERATOR_STOP'):
        if self.thread and not self.closing.is_set():
            self.stop_reason = reason
            self.phase = 'SAVING'
            self.closing.set()

    def wait(self, seconds):
        if self.thread:
            self.thread.join(seconds)
        return self.thread is None or not self.thread.is_alive()

    def status(self):
        return {'state': self.phase, 'clip_id': getattr(self, 'request', {}).get('clip_id'),
                'path': str(getattr(self, 'folder', '')), 'captured_frames': len(self.rows),
                'saved_frames': self.saved_frames, 'dropped_raw_frames': self.dropped_raw_frames,
                'dropped_tensors': self.dropped_tensors, 'duplicate_frame_ids': self.duplicate_frame_ids,
                'buffered_frames': self.buffered_frames, 'buffered_bytes': self.buffered_bytes,
                'encoded_buffer_limit_bytes': getattr(self, 'max_bytes', None),
                'bytes_written': self.bytes_written, 'stop_reason': self.stop_reason, 'error': self.error,
                'remaining_seconds': max(0, getattr(self, 'deadline', 0) - time.monotonic()) if self.recording else 0}

    def _payload(self, kind, row, value):
        started = time.perf_counter()
        if kind == 'raw':
            ok, encoded = self.encoder(value)
            if not ok:
                raise OSError('PNG_ENCODE_FAILED')
            data = encoded.tobytes()
        else:
            from io import BytesIO
            buffer = BytesIO()
            np.save(buffer, value, allow_pickle=False)
            data = buffer.getvalue()
        encoded_at = time.perf_counter()
        with self.lock:
            if self.bytes_reserved + len(data) > self.max_bytes:
                row[kind + '_status'] = 'BYTE_LIMIT'
                if kind == 'raw': self.dropped_raw_frames += 1
                else: self.dropped_tensors += 1
                self.stop('BYTE_LIMIT')
                return
            self.bytes_reserved += len(data)  # Includes in-flight writes for a hard bound.
            # Do not stream large writes to the same SD card as FULL/WAL Track
            # events. Encode during recording; persist after acquisition stops.
            self.buffered_payloads.append((kind, row, data))
            self.buffered_bytes += len(data)
            # Expected file bytes are known before disk writes. Keep these in
            # the pre-flush index so a killed Worker cannot erase identities.
            row[kind + '_sha256'] = hashlib.sha256(data).hexdigest()
            row[kind + '_status'] = 'BUFFERED'
            row[kind + '_timing_ms'] = {'encode': (encoded_at - started) * 1000}
            if kind == 'raw':
                self.buffered_frames += 1
                self.encoder_ms.append((encoded_at - started) * 1000)

    def _persist_payload(self, kind, row, data):
        started = time.perf_counter()
        if shutil.disk_usage(self.folder).free - len(data) < RESERVE_BYTES:
            raise OSError('CAPTURE_DISK_RESERVE_REACHED')
        with (self.folder / row[kind + '_path']).open('xb') as stream:
            stream.write(data)
        row[kind + '_sha256'] = hashlib.sha256(data).hexdigest()
        row[kind + '_status'] = 'SAVED'
        row[kind + '_timing_ms']['disk_check_write_hash'] = (time.perf_counter() - started) * 1000
        with self.lock:
            self.bytes_written += len(data)
        if kind == 'raw':
            self.saved_frames += 1

    def _write(self):
        from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
        def save(item):
            kind,row,value=item
            try:
                self._payload(kind,row,value)
            except Exception as error:
                row[kind+'_status']='WRITE_ERROR'
                self.error=type(error).__name__+': '+str(error)
                if kind=='raw':self.dropped_raw_frames+=1
                else:self.dropped_tensors+=1
            finally:self.queue.task_done()
        try:
            with ThreadPoolExecutor(max_workers=self.encoder_workers,thread_name_prefix='diagnostic-png') as pool:
                pending=set()
                while not self.closing.is_set() or not self.queue.empty() or pending:
                    while len(pending)<self.encoder_workers:
                        try:item=self.queue.get(timeout=.01)
                        except queue.Empty:break
                        pending.add(pool.submit(save,item))
                    if pending:
                        _,pending=wait(pending,timeout=.02,return_when=FIRST_COMPLETED)
            # SAVING is explicit; a buffered clip is never reported as SAVED.
            # Persist the small, immutable identity/hash index before any large
            # payload. It is recovery evidence, never a completed-save receipt.
            with (self.folder / 'capture_index.jsonl').open('x', encoding='utf-8') as stream:
                for row in self.rows.values():
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            for index, payload in enumerate(self.buffered_payloads):
                kind, row, data = payload
                try:
                    self._persist_payload(kind, row, data)
                except Exception as error:
                    row[kind + '_status'] = 'WRITE_ERROR'
                    self.error = type(error).__name__ + ': ' + str(error)
                    if kind == 'raw': self.dropped_raw_frames += 1
                    else: self.dropped_tensors += 1
                finally:
                    self.buffered_bytes -= len(data)
                    if kind == 'raw': self.buffered_frames -= 1
                    self.buffered_payloads[index] = None
            self.buffered_payloads.clear()
            with (self.folder / 'frames.jsonl').open('x', encoding='utf-8') as stream:
                for row in self.rows.values():
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            self.phase = 'ERROR' if self.error else 'SAVED_WITH_DROPS' if self.dropped_raw_frames or self.dropped_tensors else 'SAVED'
            receipt = dict(self.status(), context=self.context, request=self.request,
                           started_monotonic=self.started_monotonic, finished_monotonic=time.monotonic(),
                           capture_hook_ms=self.hook_ms, encode_ms=self.encoder_ms,
                           payload_write_policy='AFTER_RECORDING', encoded_buffer_limit_bytes=self.max_bytes,
                           encoder_workers=self.encoder_workers,png_compression=1,png_strategy='RLE',
                           queue_capacity_items=self.queue.maxsize,queue_high_water_items=self.queue_high_water,
                           sensor_frames_not_delivered='UNMEASURED; source PTS gaps are recorded, not invented frame counts')
            with (self.folder / 'receipt.json').open('x', encoding='utf-8') as stream:
                json.dump(receipt, stream, ensure_ascii=False, indent=2)
        except Exception as error:
            self.error = type(error).__name__ + ': ' + str(error)
            self.phase = 'ERROR'
