"""Opt-in five-second maintenance capture, reusing the existing bounded writer.

This module has no camera or PLC access. The camera Worker alone supplies frames.
Capacity failures invalidate evidence instead of slowing acquisition to hide drops.
"""
from src import config as parameters
import hashlib
import json
from pathlib import Path
import threading
import time

import numpy as np

from src.vision.diagnostic_capture import DiagnosticCapture, validate_request

MAX_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_METADATA_BYTES = 16 * 1024 * 1024
MAX_TENSOR_BYTES = 4 * 1024 * 1024
MAX_TENSORS = 12


def validate_field_request(body):
    request = validate_request(body)
    if request['duration_seconds'] > 5 or request['max_frames'] > 160 or request['max_bytes'] > MAX_PAYLOAD_BYTES:
        raise ValueError('FIELD_CAPTURE_LIMIT_5S_160FRAMES_128MIB')
    if not request['condition'] or request['condition']=='UNCONFIRMED_BENCH_SCENE':
        raise ValueError('OPERATOR_SCENE_DECLARATION_REQUIRED')
    return request


class FieldRawCapture(DiagnosticCapture):
    """Serialize hook/stop state; a clock watcher also stops an idle/stalled camera."""
    def __init__(self):
        super().__init__()
        self.lifecycle = threading.RLock()
        self.selected_tensors = 0
        self.metadata_bytes = 0
        self.last_representative = None
        self.finalized = False
        self.epoch = None
        self.closed_at = None
        self.observation_hook_ms = []
        self.last_sequence = None

    def start(self, folder, request, context, **options):
        request = validate_field_request(request)
        if context.get('field_raw_approval') is not True or context.get('publication_disabled') is not True:
            raise ValueError('MAINTENANCE_APPROVAL_AND_NO_PUBLICATION_REQUIRED')
        if not context.get('worker_generation') or not context.get('camera_owner_pid'):
            raise ValueError('WORKER_IDENTITY_REQUIRED')
        if len(json.dumps(context,allow_nan=False).encode('utf-8'))>128*1024:
            raise ValueError('CAPTURE_CONTEXT_LIMIT')
        if options.get('queue_size',parameters.FIELD_RAW_QUEUE_SIZE) != parameters.FIELD_RAW_QUEUE_SIZE or options.get('encoder_workers',parameters.FIELD_RAW_ENCODER_WORKERS) != parameters.FIELD_RAW_ENCODER_WORKERS:
            raise ValueError('FIXED_FIELD_CAPTURE_QUEUE_REQUIRED')
        with self.lifecycle:
            super().start(folder,request,context,queue_size=parameters.FIELD_RAW_QUEUE_SIZE,encoder_workers=parameters.FIELD_RAW_ENCODER_WORKERS,
                          **{k:v for k,v in options.items() if k not in ('queue_size','encoder_workers')})
            self.watcher=threading.Thread(target=self._watch,name='field-capture-deadline',daemon=True)
            self.watcher.start()

    def _watch(self):
        while not self.closing.wait(min(.02,max(.001,self.deadline-time.monotonic()))):
            with self.lifecycle:
                self.tick()

    def fail(self, reason):
        self.error=reason
        self.stop('DIAGNOSTIC_FAILURE')

    def capture(self, frame_id, image, freshness):
        with self.lifecycle:
            if not self.recording:return
            if (freshness.get('frame_id')!=frame_id or type(freshness.get('sequence')) is not int
                    or not freshness.get('camera_epoch')):
                self.fail('RAW_FRAME_IDENTITY_INVALID');return
            epoch=freshness['camera_epoch']
            if self.epoch is not None and self.epoch!=epoch:
                self.fail('CAMERA_EPOCH_CHANGED');return
            if self.last_sequence is not None and freshness['sequence']<=self.last_sequence:
                self.fail('NONMONOTONIC_SEQUENCE');return
            if (getattr(image,'shape',None)!=(720,1280,3) or image.dtype!=np.uint8):
                self.fail('RAW_NATIVE_BGR8_1280X720_REQUIRED');return
            self.epoch=epoch
            self.last_sequence=freshness['sequence']
            super().capture(frame_id,image,freshness)
            if frame_id in self.rows:
                self.rows[frame_id]['worker_generation']=self.context['worker_generation']

    def observe(self, frame_id, observation, tensor=None):
        started=time.perf_counter()
        with self.lifecycle:
            row=self.rows.get(frame_id)
            if row is None or self.closing.is_set():return
            if observation.get('frame_id')!=frame_id or observation.get('detector_frame_id')!=frame_id:
                self.fail('TENSOR_FRAME_ID_MISMATCH');return
            if observation.get('generation')!=self.context['worker_generation']:
                self.fail('WORKER_GENERATION_MISMATCH');return
            try:
                size=len(json.dumps(observation,allow_nan=False).encode('utf-8'))
            except (ValueError,TypeError):
                self.fail('NONFINITE_OR_INVALID_DIAGNOSTIC_METADATA');return
            if size>1024*1024 or self.metadata_bytes+size>MAX_METADATA_BYTES:
                self.fail('METADATA_LIMIT');return
            self.metadata_bytes+=size
            stages=observation.get('engine',{}).get('detector_stages') or {}
            traces=stages.get('bbox_coordinate_trace',[])
            boundary=any(any(v<=0 for v in t['restored_after_clip'][:2]) or
                         t['restored_after_clip'][2]>=1280 or t['restored_after_clip'][3]>=720 for t in traces)
            now=time.monotonic()
            representative=self.last_representative is None or now-self.last_representative>=1
            selected=tensor is not None and (boundary or representative) and self.selected_tensors<MAX_TENSORS
            if selected:
                if (not isinstance(tensor,np.ndarray) or tensor.dtype.hasobject
                        or tensor.nbytes>MAX_TENSOR_BYTES):
                    self.fail('TENSOR_SIZE_OR_TYPE_INVALID');return
                self.selected_tensors+=1
                if representative:self.last_representative=now
                row['tensor_selection_reason']='BOUNDARY' if boundary else 'REPRESENTATIVE'
            else:
                row['tensor_status']=('UNAVAILABLE' if tensor is None else
                    'SELECTION_LIMIT' if self.selected_tensors>=MAX_TENSORS else 'NOT_SELECTED')
            super().observe(frame_id,observation,tensor if selected else None)
        self.observation_hook_ms.append((time.perf_counter()-started)*1000)

    def stop(self, reason='OPERATOR_STOP'):
        with self.lifecycle:
            if self.thread and not self.closing.is_set():self.closed_at=time.monotonic()
            super().stop(reason)

    def status(self):
        value=super().status()
        if value['state'].startswith('SAVED') and not self.finalized:value['state']='SAVING'
        return dict(value,mode='FIELD_RAW_CAPTURE_ONLY',selected_tensors=self.selected_tensors,
                    metadata_bytes=self.metadata_bytes,plc_writes=0)

    def _write(self):
        super()._write()
        try:
            # Writer is joined before this receipt is consumed; no live row edits remain.
            rows=list(self.rows.values())
            if not rows and not self.error:
                self.error='NO_RAW_FRAMES';self.phase='ERROR'
            elif self.phase=='SAVED' and any(r['observation_status']!='PROCESSED' for r in rows):
                self.phase='SAVED_WITH_DROPS'
            sequences=[r['freshness']['sequence'] for r in rows]
            gaps=[dict(after=a,before=b,missing=b-a-1) for a,b in zip(sequences,sequences[1:]) if b!=a+1]
            pts=[r['freshness'].get('source_pts_ns') for r in rows]
            pts_deltas=[(b-a)/1e6 for a,b in zip(pts,pts[1:]) if a is not None and b is not None]
            files=[]
            for path in sorted(self.folder.rglob('*')):
                if path.is_file():
                    data=path.read_bytes()
                    files.append(dict(path=path.relative_to(self.folder).as_posix(),bytes=len(data),
                                      sha256=hashlib.sha256(data).hexdigest()))
            metadata_total=sum(v['bytes'] for v in files if not v['path'].startswith(('raw/','outputs/')))
            # Includes two metadata indexes + receipt: each observation is bounded before enqueue.
            if metadata_total>2*MAX_METADATA_BYTES+2*1024*1024:
                self.error='METADATA_FILE_LIMIT';self.phase='ERROR'
            times=[r['freshness']['estimated_source_monotonic'] for r in rows]
            summary=dict(state=self.phase,error=self.error,stop_reason=self.stop_reason,
                started_monotonic=self.started_monotonic,deadline_monotonic=self.deadline,
                closed_monotonic=self.closed_at,files=files,plc_writes=0,
                publication='NOT_CONSTRUCTED',camera_owner_pid=self.context['camera_owner_pid'],
                raw_frames=len(rows),saved_frames=self.saved_frames,worker_sequence_gaps=gaps,
                source_pts_deltas_ms=pts_deltas,sensor_frames_not_delivered='UNMEASURED',
                continuous_clear_evidence_eligible=False,
                continuity_note='Worker sequence is not a sensor counter; assess actual source PTS/freshness and human scene separately.',
                source_span_seconds=times[-1]-times[0] if len(times)>1 else 0,
                diagnostic_overhead_ms={'capture':self.hook_ms,'observe':self.observation_hook_ms},
                inference_ms=[r['observation'].get('inference_ms') for r in rows if r.get('observation')],
                not_processed_frames=[r['frame_id'] for r in rows if r['observation_status']!='PROCESSED'],
                bounds=dict(payload_bytes=self.max_bytes,metadata_index_bytes=2*MAX_METADATA_BYTES+2*1024*1024,
                    queue_items=8,encoder_workers=2,max_tensor_bytes=MAX_TENSOR_BYTES,max_tensors=MAX_TENSORS),
                field_qualification='NOT_GRANTED_BY_CAPTURE_SUCCESS')
            with (self.folder/'field_summary.json').open('x',encoding='utf-8') as stream:
                json.dump(summary,stream,ensure_ascii=False,indent=2,allow_nan=False)
            digest=hashlib.sha256((self.folder/'field_summary.json').read_bytes()).hexdigest()
            (self.folder/'field_summary.sha256').write_text(digest+'\n',encoding='ascii')
        except Exception as error:
            self.error=type(error).__name__+': '+str(error);self.phase='ERROR'
        finally:
            self.closing.set()
            self.finalized=True
