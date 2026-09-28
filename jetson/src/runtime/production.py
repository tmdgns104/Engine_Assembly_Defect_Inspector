"""Single camera, existing coordinator and inspection bridge; separate request latch.

The runtime thread owns all tracking/handshake mutations under runtime->Service locks.
This candidate uses an in-memory gateway only. It cannot connect to a physical PLC.
"""
from collections import deque
from dataclasses import asdict
import hashlib
import json
import math
import queue
from pathlib import Path
import time
import uuid

from src.control.production_plc import MockPlcGateway,RequestHandshake
from src.integration.clearance import VisionAbsenceEvidence, AreaClearEvidence
from src.observation.area_occupancy import ClearWindow
from src.integration.cycle_track_binding import BoundClearanceEvidence
from src.observation.contracts import ProviderStatus
from src.runtime.contracts import CycleStart
from src.runtime.inspection_bridge import InspectionBridge
from src.runtime.integrated import IntegratedRuntime
from src.runtime.production_profile import proposed_zone,validate_zone,tracker_config,calibration_sha
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.tracking.contracts import TrackState,WindowRelation,TrackingReason


class ProductionRuntime(IntegratedRuntime):
    def __init__(self,*args,zone=None,area_config_version=None,
                 area_reference_required=True,gateway=None,**kwargs):
        self.connection_plan=json.loads((Path(__file__).resolve().parents[2]/'config/plc_reference.json').read_text(encoding='utf-8'))
        self.zone=zone or proposed_zone()
        self.operating=False; self.phase='STOPPED'; self.latest_packet=None
        self.auto_stop_requested=False
        self.last_sequence=-1; self.last_time=0; self.epoch=None; self.worker_generation=None
        self.absent=[]; self.observation_times=deque(maxlen=40); self.history=deque(maxlen=30)
        self.gateway=gateway if gateway is not None else MockPlcGateway()
        self.handshake=RequestHandshake(self.gateway,self._event)
        self.pending_started=None; self.published_ids=set(); self.inspected_tracks=set()
        self.window_event=None; self.eligible=False; self.last_transition=None
        self.request_wait_seconds=8.; self.observation_stale_seconds=2.
        self.observation_started_at=None
        self._reset_departure_candidate()
        self._diagnostic_events=None
        self.area_config_version = area_config_version
        self.area_reference_required=area_reference_required
        self.area_approval = None
        self.area_window = ClearWindow()
        self.area_observation = None
        self.area_wait_reason = None
        self.area_wait_started = None
        self.last_retirement = None
        self.new_product_after = None
        super().__init__(*args,**kwargs)
        self.service.production_owner=self

    def _event(self,value):
        if self._diagnostic_events is not None:
            self._diagnostic_events.append(dict(value))
        journal=self.service.journal
        payload=dict(runtime_session_id=self.session_id,monotonic_s=time.monotonic(),
            worker_generation=self.service.generation,physical_output_enabled=False,**value)
        with journal.lock,journal.db:
            journal._event(payload['event'],payload)
            if payload.get('inspection_id'):
                journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    ('production_publication:'+payload['inspection_id'],json.dumps(payload)))

    def start_auto(self):
        with self.lock,self.service.lock:
            if self.operating: return self.status()
            if self.error or self.coordinator.active_cycle or self.service.active: raise ValueError('RECOVERY_OR_CLEARANCE_REQUIRED')
            if self.service.lab.mode!='MANUAL': raise ValueError('STOP_LAB_MODE_FIRST')
            if not self.service.status()['ready']: raise ValueError('CAMERA_MODELS_REFERENCE_JOURNAL_REQUIRED')
            if not self.zone.get('confirmed') or self.zone.get('calibration_sha')!=calibration_sha(self.service.calibration):
                raise ValueError('INSPECTION_ZONE_CONFIRMATION_REQUIRED')
            if self.handshake.state=='RESYNC_REQUIRED': raise ValueError('PLC_RESYNC_REQUIRED')
            if self.gateway.backend != 'MOCK':
                if self.handshake.state not in ('SYNC_LOW', 'ARMED'):
                    raise ValueError('PLC_HANDSHAKE_NOT_IDLE')
                request = self.gateway.read_request()
                if request.status != 'ACK' or request.value is not False:
                    raise ValueError('VALID_PLC_REQUEST_LOW_REQUIRED_AT_AUTO_START')
                self.handshake.request = False
                self.handshake.state = 'ARMED'
            if self.area_config_version and not self._area_approval_current(self._preview_area()):
                raise ValueError('CURRENT_VALID_AREA_OBSERVATION_REQUIRED' if not self.area_reference_required
                                 else 'MAINTENANCE_AREA_REFERENCE_APPROVAL_REQUIRED')
            self.auto_stop_requested=False
            self.operating=True; self.phase='IDLE'; self.last_sequence=-1; self.last_time=0
            # A new acquisition window must not inherit a stopped preview's age,
            # eligibility or FPS. Queue entries captured before START are not current.
            self.observation_started_at=time.monotonic()
            self.latest_packet=None; self.eligible=False; self.observation_times.clear()
            self.epoch=None; self.worker_generation=self.service.generation; self.absent=[]
            self._reset_departure_candidate()
            self.area_window.reset()
            self.service.production_tracking.set()
            self._event({'event':'PRODUCTION_AUTO_STARTED','zone':self.zone,'human_acceptance':'PENDING'})
            return self.status()

    def stop_auto(self):
        with self.lock,self.service.lock:
            self.auto_stop_requested=True
            self.operating=False
            # An admitted request finishes under its original identity; STOP admits no next edge.
            if self.handshake.state=='REQUEST_LATCHED': self.handshake.fault('STOP_BEFORE_INSPECTION')
            if not self.coordinator.active_cycle and not self.service.active:
                self.service.production_tracking.clear()
            self.phase='STOPPED_DRAINING' if self.coordinator.active_cycle or self.service.active else 'STOPPED'
            self._event({'event':'PRODUCTION_AUTO_STOPPED','drain_current':bool(self.service.active)})
            return self.status()

    def configure_zone(self,body):
        with self.lock,self.service.lock:
            if self.operating or self.coordinator.active_cycle or self.service.active: raise ValueError('STOP_AND_IDLE_REQUIRED')
            zone=dict(body)
            validate_zone(zone)
            if type(zone.get('confirmed')) is not bool: raise ValueError('EXPLICIT_ZONE_CONFIRMATION_STATE_REQUIRED')
            if not self.service.calibration: raise ValueError('REFERENCE_CONFIRMATION_REQUIRED')
            zone.update(version='zone-'+uuid.uuid4().hex[:12],calibration_sha=calibration_sha(self.service.calibration))
            self.zone=zone; self.tracker_config=tracker_config(zone,wait_area_clear=bool(self.area_config_version))
            self._replace_tracking_session(uuid.uuid4().hex)
            self.inspected_tracks.clear()
            self._reset_departure_candidate()
            self.service.production_owner=self
            with self.service.journal.lock,self.service.journal.db:
                self.service.journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    ('production_zone',json.dumps(zone)))
            self._event({'event':'INSPECTION_ZONE_CONFIRMED' if zone['confirmed'] else 'INSPECTION_ZONE_DRAFT_SAVED','zone':zone})
            return self.status()

    def mock_action(self,action,body):
        with self.lock,self.service.lock:
            if self.gateway.backend != 'MOCK':
                raise ValueError('MOCK_ACTION_UNAVAILABLE_WITH_REAL_PLC')
            if action=='request':
                if type(body.get('value')) is not bool: raise ValueError('BOOL_REQUIRED')
                self.gateway.request=body['value']
            elif action=='resync':
                if self.service.active: raise ValueError('INSPECTION_RUNNING')
                self.handshake.resync()
            elif action=='fault':
                kind=body.get('kind')
                if kind in ('disconnect','reconnect'): self.gateway.connected=kind=='reconnect'
                elif kind in ('result_fail','done_fail','done_unknown'):
                    setattr(self.gateway,'unknown_next' if kind=='done_unknown' else 'fail_next',
                        'Jetson_Result' if kind=='result_fail' else 'Jetson_Done')
                else: raise ValueError('UNKNOWN_MOCK_FAULT')
            else: raise ValueError('UNKNOWN_MOCK_ACTION')
            self._event({'event':'PRODUCTION_MOCK_OPERATOR_ACTION','action':action,'value':body})
            return self.status()

    def recover_empty_area(self,empty_confirmed=False,**unused):
        with self.lock,self.service.lock:
            if self.operating or self.service.active: raise ValueError('STOP_AND_IDLE_REQUIRED')
            # Operator assertion alone is insufficient: require the current healthy absence sequence.
            if empty_confirmed is not True or not self._absence_ready(): raise ValueError('CURRENT_HEALTHY_EMPTY_AREA_REQUIRED')
            self._event({'event':'PRODUCTION_EXPLICIT_RECOVERY','old_track_id':self.coordinator._tracker._track_id})
            self._replace_tracking_session(uuid.uuid4().hex)
            self.inspected_tracks.clear()
            self.bridge=InspectionBridge(self.service,self.coordinator)
            self.error=None; self.eligible=False; self.window_event=None; self.phase='STOPPED'
            self._reset_departure_candidate()
            self.handshake.resync(); self.service.production_tracking.clear()
            return self.status()

    def start_cycle(self,*args,**kwargs): raise ValueError('PRODUCTION_OWNS_TRACK_CYCLES')
    def observe(self,*args,**kwargs): raise ValueError('WORKER_OWNS_PRODUCT_OBSERVATIONS')
    def clearance(self,*args,**kwargs): raise ValueError('VISION_OWNS_CLEARANCE_EVIDENCE')

    def _absence_ready(self):
        return bool(len(self.absent)>=6 and self.absent[-1][1]-self.absent[0][1]>=1.2
            and self.latest_packet and time.monotonic()-self.latest_packet['processed_monotonic']<2)

    def _fault(self,reason):
        if self.error==reason: return
        self.error=reason; self.phase='FAULT'; self.eligible=False; self.operating=False
        self.area_window.reset()
        self._event({'event':'PRODUCTION_FAULT','reason':reason,'track_id':self.coordinator._tracker._track_id})
        if self.handshake.token: self.handshake.fault(reason,'BLOCKED')

    def _preview_area(self):
        preview = getattr(self.service, 'preview', None) or {}
        area = preview.get('area_occupancy')
        if not area or time.monotonic()-area['monotonic_s'] > 1:
            return None
        return area

    def _area_approval_current(self, area):
        if not area or not area.get('reference_valid') or area.get('config_version')!=self.area_config_version:
            return False
        if not self.area_reference_required:
            return True
        return bool(self.area_approval and all(area.get(k)==self.area_approval[k]
            for k in ('generation','camera_epoch','config_version')))

    def approve_area_reference(self, empty_confirmed=False, setup_unchanged=False):
        """One maintenance approval per Worker/epoch; never called by the lifecycle."""
        with self.lock, self.service.lock:
            if not self.area_reference_required:
                raise ValueError('NO_STATIC_REFERENCE_IN_DARK_SURFACE_MODE')
            if self.operating or self.coordinator.active_cycle or self.service.active:
                raise ValueError('STOP_AND_IDLE_REQUIRED')
            area = self._preview_area()
            if (empty_confirmed is not True or setup_unchanged is not True or not area or
                    area['state'] != 'CLEAR' or area['config_version'] != self.area_config_version):
                raise ValueError('CURRENT_MATCHING_EMPTY_AREA_AND_SETUP_CONFIRMATION_REQUIRED')
            self.area_approval = {k:area[k] for k in ('generation','camera_epoch','config_version')}
            self.area_window.reset()
            self._event(dict(event='AREA_REFERENCE_MAINTENANCE_APPROVED',approval=self.area_approval,
                             reference_version=area['reference_version'],frame_id=area['frame_id']))
            return self.status()

    def _observe_area(self, packet, provider):
        measurement = packet.get('area_occupancy')
        if (not measurement or not self._area_approval_current(measurement) or
                any(measurement.get(k) != packet.get(k) for k in
                    ('frame_id','sequence','camera_epoch','generation','monotonic_s'))):
            self.area_window.reset()
            self.area_observation = dict(state='UNKNOWN',reference_valid=False,clear_duration_s=0,
                reason='AREA_REFERENCE_OR_FRAME_MISMATCH',frame_id=packet['frame_id'])
            return
        measurement = dict(measurement)
        if provider.status != ProviderStatus.NO_FOREGROUND and measurement['classification']=='MATCH':
            measurement.update(classification='UNKNOWN',reason='PRODUCT_OBSERVATION_CONTRADICTS_CLEAR')
        self.area_observation = self.area_window.update(measurement,packet,time.monotonic())

    def _area_transaction_block(self):
        if not self.operating: return 'USER_STOP_OR_SYSTEM_FAULT'
        if getattr(self.service,'error',None) or getattr(self.service,'state','IDLE') in ('RECOVERY','STOPPED','CANCELLING'):
            return 'INSPECTION_SERVICE_OR_CAMERA_FAULT'
        if self.service.active: return 'INSPECTION_IN_FLIGHT'
        if self.handshake.state not in ('ARMED','SYNC_LOW'):
            return 'REQUEST_OR_PUBLICATION_UNSETTLED:'+self.handshake.state
        if self.handshake.token: return 'REQUEST_TOKEN_NOT_SETTLED'
        if self.bridge.inspection_id:
            if (self.bridge.phase != 'INSPECTION_DURABLE' or
                    self.bridge.inspection_id not in self.published_ids or
                    self.handshake.publication != 'ACKNOWLEDGED'):
                return 'DURABILITY_OR_PUBLICATION_NOT_ACKNOWLEDGED'
        return None

    def _area_clearance(self, packet, provider):
        tracker = self.coordinator._tracker
        if not self.coordinator.active_cycle or tracker._track_id is None: return None
        area = self.area_observation or {}
        self.area_wait_reason = self._area_transaction_block()
        if self.area_wait_reason: return None
        if area.get('state') != 'CLEAR' or provider.status != ProviderStatus.NO_FOREGROUND:
            self.area_wait_reason = area.get('reason','AREA_OBSERVATION_REQUIRED')
            return None
        reason = ('EXIT_CONFIRMED' if self.departure_edge and self.departure_clearance_eligible
                  else 'AREA_CLEAR_CONFIRMED')
        authority = AreaClearEvidence(self.epoch,tuple(area['clear_sequences']),
            area['first_clear_monotonic'],packet['monotonic_s'],area['reference_version'],
            area['config_version'],reason)
        tracker.prepare_visual_clearance(tracker._track_id)
        evidence = BoundClearanceEvidence(self.session_id,self.coordinator.active_cycle.cycle_id,
            tracker._track_id,uuid.uuid4().hex,self.epoch,packet['sequence'],authority)
        self.last_clearance = asdict(evidence)
        return evidence

    def _reset_departure_candidate(self):
        self.departure_edge = None
        self.departure_clearance_eligible = False
        self._departure_reference_box = None

    def _observe_departure_edge(self, previous, current):
        """Arm an exit candidate only after observed outward motion to an image edge.

        Zone departure and an initially clipped box are not camera departure.
        One native pixel of boundary jitter retains an existing candidate only.
        Creation still requires the original observed crossing. Box growth makes
        that candidate ineligible for clearance until it is cancelled and rearmed.
        """
        # Occluding hands can enlarge the detector box into an image boundary.
        # Require its trailing edge to move outward too, without growth along
        # that axis. These are geometry checks, not relaxed detector thresholds.
        # Equivalent decimal box widths can differ by floating-point roundoff.
        width_not_growing = previous and (current.width <= previous.width
                                          or math.isclose(current.width, previous.width))
        height_not_growing = previous and (current.height <= previous.height
                                           or math.isclose(current.height, previous.height))
        edges = {
            'left': (current.x1 == 0, previous and previous.x1 > 0
                     and current.x2 < previous.x2 and width_not_growing),
            'right': (current.x2 == 1, previous and previous.x2 < 1
                      and current.x1 > previous.x1 and width_not_growing),
            'top': (current.y1 == 0, previous and previous.y1 > 0
                    and current.y2 < previous.y2 and height_not_growing),
            'bottom': (current.y2 == 1, previous and previous.y2 < 1
                       and current.y1 > previous.y1 and height_not_growing),
        }
        self._diagnostic_departure=dict(previous_box=asdict(previous) if previous else None,
            current_box=asdict(current),edge_checks={edge:dict(touches=bool(values[0]),crossed_with_non_growing_box=bool(values[1])) for edge,values in edges.items()})
        # This is coordinate quantization tolerance, not a confidence/zone change.
        # Missing image dimensions grant no tolerance (e.g. legacy test packets).
        width = self.latest_packet.get('width', 0)
        height = self.latest_packet.get('height', 0)
        dx, dy = (1 / width if width else 0), (1 / height if height else 0)
        gaps = {'left':current.x1, 'right':1-current.x2,
                'top':current.y1, 'bottom':1-current.y2}
        tolerances = {'left':dx, 'right':dx, 'top':dy, 'bottom':dy}
        reference = self._departure_reference_box or previous
        non_growing = bool(previous and reference and all(
            current.width <= box.width + dx + 1e-12 and
            current.height <= box.height + dy + 1e-12
            for box in (previous, reference)))
        self._diagnostic_departure.update(boundary_tolerance_pixels=1,
            geometry_non_growing=non_growing)
        if self.departure_edge and gaps[self.departure_edge] <= tolerances[self.departure_edge]:
            if self.departure_clearance_eligible and not non_growing:
                self.departure_clearance_eligible = False
                self._event({'event':'PRODUCTION_DEPARTURE_CANDIDATE_UNTRUSTED',
                    'reason':'BBOX_GROWTH_AFTER_CROSSING','departure_edge':self.departure_edge,
                    'previous_box':asdict(previous) if previous else None,
                    'current_box':asdict(current),'frame_id':self.latest_packet['frame_id']})
            self._diagnostic_departure['reason']=('RETAIN_SAME_BOUNDARY_CONTACT'
                if edges[self.departure_edge][0] else 'RETAIN_SUBPIXEL_BOUNDARY_CANDIDATE')
            self._diagnostic_departure['clearance_eligible']=self.departure_clearance_eligible
            return
        previous_departure_edge = self.departure_edge
        self.departure_edge = next((edge for edge, (touches, crossed) in edges.items()
                                    if touches and crossed), None)
        # A new crossing uses its own pre-crossing box. Unknown/growing geometry
        # is a candidate, never sufficient authority for absence-based retirement.
        self._departure_reference_box = previous if self.departure_edge else None
        self.departure_clearance_eligible = bool(self.departure_edge and previous and
            current.width <= previous.width + dx + 1e-12 and
            current.height <= previous.height + dy + 1e-12)
        self._diagnostic_departure['clearance_eligible']=self.departure_clearance_eligible
        self._diagnostic_departure['reason']=('ARMED_OBSERVED_NON_GROWING_OUTWARD_CROSSING' if self.departure_edge
            else 'CLEARED_NO_QUALIFYING_BOUNDARY_CONTACT' if previous_departure_edge
            else 'NO_QUALIFYING_BOUNDARY_CROSSING')
        entered_boundary = previous is not None and (
            (current.x1 == 0 and previous.x1 > 0) or (current.x2 == 1 and previous.x2 < 1)
            or (current.y1 == 0 and previous.y1 > 0) or (current.y2 == 1 and previous.y2 < 1))
        if entered_boundary:
            self._event({'event':'PRODUCTION_DEPARTURE_EDGE_ASSESSED',
                'departure_edge':self.departure_edge,
                'previous_box':asdict(previous) if previous else None,'current_box':asdict(current),
                'frame_id':self.latest_packet['frame_id']})
        if previous_departure_edge and self.departure_edge is None:
            self._event({'event':'PRODUCTION_DEPARTURE_EDGE_CLEARED',
                'previous_departure_edge':previous_departure_edge,
                'previous_box':asdict(previous) if previous else None,'current_box':asdict(current),
                'frame_id':self.latest_packet['frame_id']})

    def _packet(self,packet):
        recorder=getattr(self.service,'diagnostic_capture',None)
        clip_id=packet.get('diagnostic_clip_id')
        if recorder is None or not clip_id:
            return self._apply_packet(packet)
        before=self._diagnostic_state()
        self._diagnostic_events=[]
        self._diagnostic_reason='UNKNOWN'
        self._diagnostic_departure={'reason':'NO_ACCEPTED_ASSOCIATED_BOX_UPDATE'}
        started=time.perf_counter()
        try:
            return self._apply_packet(packet)
        finally:
            recorder.record(dict(clip_id=clip_id,frame_id=packet['frame_id'],
                consumed_monotonic=time.monotonic(),packet=packet,before=before,
                after=self._diagnostic_state(),events=self._diagnostic_events,
                outcome=self._diagnostic_reason,departure=self._diagnostic_departure,
                handler_ms=(time.perf_counter()-started)*1000))
            self._diagnostic_events=None

    def _diagnostic_state(self):
        tracker=self.coordinator._tracker
        box=tracker._last_box
        return dict(runtime_session_id=self.session_id,operating=self.operating,phase=self.phase,
            error=self.error,track_id=tracker._track_id,state=tracker._state.value,
            last_sequence=self.last_sequence,last_time=self.last_time,
            last_observed_s=tracker._last_observed_s,last_box=asdict(box) if box else None,
            departure_edge=self.departure_edge,eligible=self.eligible,
            departure_clearance_eligible=self.departure_clearance_eligible,
            area_occupancy=self.area_observation,area_wait_reason=self.area_wait_reason,
            last_retirement=self.last_retirement,
            inspection_id=self.service.active['inspection_id'] if self.service.active else None,
            inspection_zone=self.zone,plc=self.handshake.status())

    def _apply_packet(self,packet):
        if not self.service.production_tracking.is_set():
            self._diagnostic_reason='TRACKING_DISABLED'; return
        if self.observation_started_at is not None and packet['monotonic_s']<self.observation_started_at:
            self._diagnostic_reason='BEFORE_ACQUISITION_WINDOW'
            return
        if packet['generation']!=self.service.generation:
            self._fault('WORKER_GENERATION_CHANGED'); return
        if self.worker_generation and packet['generation']!=self.worker_generation:
            self._fault('WORKER_GENERATION_CHANGED'); return
        if self.epoch is not None and packet['camera_epoch']!=self.epoch:
            self.absent=[]; self._fault('CAMERA_EPOCH_CHANGED')
            self.epoch=packet['camera_epoch']; self.last_sequence=-1; self.last_time=0; self.latest_packet=None
        if packet['sequence']<=self.last_sequence or packet['monotonic_s']<=self.last_time:
            self._fault('PRODUCT_FRAME_ORDER_INVALID'); return
        if self.latest_packet and packet['monotonic_s']-self.last_time>self.observation_stale_seconds:
            self.absent=[]
            if self.coordinator.active_cycle: self._fault('PRODUCT_OBSERVATION_GAP')
        if time.monotonic()-packet['processed_monotonic']>2 or not packet['integrity']['valid']:
            self.absent=[]; self._fault('INVALID_OR_STALE_PRODUCT_OBSERVATION'); return
        if packet['package_sha256']!=self.service.package.manifest_hash:
            self._fault('PACKAGE_CHANGED'); return
        if self.area_config_version and not 0 <= time.monotonic()-packet['monotonic_s'] <= 2:
            self.area_window.reset(); self._fault('INVALID_OR_STALE_PRODUCT_OBSERVATION'); return
        self.last_sequence=packet['sequence']; self.last_time=packet['monotonic_s']; self.epoch=packet['camera_epoch']
        self.latest_packet=packet; self.observation_times.append(packet['processed_monotonic'])
        provider=self.observation.observe(packet)
        if self.area_config_version:
            self._observe_area(packet,provider)
        self._diagnostic_reason='PROVIDER_'+provider.status.value
        if provider.status==ProviderStatus.NO_FOREGROUND:
            self.absent.append((packet['sequence'],packet['monotonic_s']))
            if len(self.absent)>128: self.absent.pop(0)
        else: self.absent=[]
        if self.error:
            self._diagnostic_reason='HALTED_'+self.error; return
        tracker=self.coordinator._tracker
        if (provider.status==ProviderStatus.PRODUCT_OBSERVED and
                tracker._state==TrackState.WAIT_AREA_CLEAR and
                self.handshake.token is None and
                self.area_observation and
                self.area_observation.get('frame_id')==packet['frame_id'] and
                self.area_observation.get('state')=='OCCUPIED' and
                tracker.resume_short_ambiguity(provider.observations[0].bbox,packet['monotonic_s'])):
            self._event({'event':'PRODUCTION_TRACK_RESUMED','track_id':tracker._track_id,
                'reason':'SHORT_AMBIGUITY_SAME_PRODUCT','frame_id':packet['frame_id']})
        if provider.status==ProviderStatus.AMBIGUOUS_FOREGROUND:
            self.eligible=False; self.phase='AMBIGUOUS_HOLD'
            if tracker._track_id is not None:
                if self.area_config_version:
                    tracker.wait_for_area_clear(TrackingReason.AMBIGUOUS_ACTIVE_OBSERVATIONS)
                    self.snapshot=self.coordinator.route(packet['frame_id'],packet['sequence'],packet['monotonic_s'],provider)
                    self.phase='WAIT_AREA_CLEAR'
                    self.area_wait_reason='AMBIGUOUS_PRODUCT_OBSERVATION'
                    if self.area_wait_started is None: self.area_wait_started=time.monotonic()
                else: self._fault('MULTIPLE_PRODUCT_AMBIGUITY')
            return
        if self.coordinator.active_cycle is None and provider.observations:
            if not self.operating: return
            if self.new_product_after is not None and packet['monotonic_s'] <= self.new_product_after:
                self._diagnostic_reason='QUEUED_BEFORE_PREVIOUS_RETIREMENT'; return
            self.snapshot=self.coordinator.start_cycle(CycleStart(self.session_id,uuid.uuid4().hex))
            self.window_event=None
            self._reset_departure_candidate()
            self._event({'event':'VISION_PASSAGE_STARTED','cycle_id':self.coordinator.active_cycle.cycle_id})
        evidence=None
        # Clearance cannot retire an identity sooner than the tracker's existing
        # missed-observation grace. Hand occlusion during part removal may recover
        # within that window; it is not a new product passage.
        gap_limit=self.tracker_config.max_unobserved_seconds
        gap_elapsed=(packet['monotonic_s']-tracker._last_observed_s
            if tracker._last_observed_s is not None else 0)
        clearance_gap_elapsed=gap_limit is None or gap_elapsed>=gap_limit
        # Losing an envelope while it was inside the zone is not observed exit.
        # Outside the inspection zone can still be inside the camera image.
        # Require an observed outward edge crossing before absence can retire it.
        last_box=tracker._last_box
        window=self.tracker_config.inspection_window
        margin=self.tracker_config.zone_hysteresis
        observed_outside_zone=bool(last_box and not (
            window.x1-margin<=last_box.center_x<=window.x2+margin and
            window.y1-margin<=last_box.center_y<=window.y2+margin))
        if (not self.area_config_version and self.coordinator.active_cycle and self._absence_ready() and clearance_gap_elapsed
                and observed_outside_zone and self.departure_edge and self.departure_clearance_eligible
                and not self.service.active and
                (not self.bridge.inspection_id or self.bridge.inspection_id in self.published_ids)):
            if tracker._state!=TrackState.LOST:
                authority=VisionAbsenceEvidence(self.epoch,tuple(n for n,t in self.absent),self.absent[0][1],packet['monotonic_s'])
                tracker.prepare_visual_clearance(tracker._track_id)
                evidence=BoundClearanceEvidence(self.session_id,self.coordinator.active_cycle.cycle_id,
                    tracker._track_id,uuid.uuid4().hex,self.epoch,packet['sequence'],authority)
                self.last_clearance=asdict(evidence)
        if self.area_config_version:
            evidence=self._area_clearance(packet,provider)
            if (evidence is None and tracker._state==TrackState.CLEARING and
                    gap_limit is not None and gap_elapsed>gap_limit):
                tracker.wait_for_area_clear(TrackingReason.MISSED_OBSERVATION_LIMIT)
        self.snapshot=self.coordinator.route(packet['frame_id'],packet['sequence'],packet['monotonic_s'],provider,evidence)
        if self.snapshot.inspection_event: self.window_event=self.snapshot.inspection_event
        if tracker._state==TrackState.LOST:
            self._fault('TRACK_ASSOCIATION_OR_GAP_LOST'); return
        if provider.observations and tracker._state != TrackState.WAIT_AREA_CLEAR:
            self._observe_departure_edge(last_box, provider.observations[0].bbox)
        elif (not self.area_config_version and tracker._state==TrackState.CLEARING and gap_limit is not None
              and gap_elapsed>gap_limit and evidence is None):
            # The bridge intentionally holds CLEARING without exit authority;
            # stop on unresolved absence instead of silently retiring or hanging.
            self._fault('PRODUCT_DEPARTURE_NOT_OBSERVED'); return
        self.eligible=bool(provider.observations and tracker._state==TrackState.INSPECTION_READY
            and tracker._relation==WindowRelation.INSIDE and tracker._track_id not in self.inspected_tracks)
        if self.snapshot.cycle_retired:
            self.last_retirement=dict(track_id=self.snapshot.track_id,
                reason=evidence.clearance_evidence.termination_reason if self.area_config_version else 'VISION_BOUNDED_ABSENCE',
                inspection_id=self.snapshot.inspection_id,
                inspection_status='INSPECTED' if self.snapshot.inspection_id else 'UNINSPECTED',
                frame_id=packet['frame_id'],source_monotonic=packet['monotonic_s'],
                retired_monotonic=time.monotonic())
            self._event({'event':'PRODUCTION_TRACK_RETIRED','track_id':self.snapshot.track_id,
                'inspection_id':self.snapshot.inspection_id,'clearance':self.last_clearance,
                'termination':self.last_retirement,
                'departure_edge':self.departure_edge,'request_off_is_clearance':False})
            self._reset_departure_candidate()
            self.window_event=None; self.absent=[]
            if self.area_config_version:
                self.new_product_after=time.monotonic()
                self.bridge=InspectionBridge(self.service,self.coordinator)
                self.area_wait_reason=None; self.area_wait_started=None
        self.phase=('INSPECTING' if self.service.active else 'WAIT_PLC_REQUEST' if self.eligible else tracker._state.value)
        if self.area_config_version:
            if tracker._state==TrackState.WAIT_AREA_CLEAR:
                if self.area_wait_started is None: self.area_wait_started=time.monotonic()
                self.phase='WAIT_AREA_CLEAR'
            elif tracker._state==TrackState.IDLE: self.phase='WAIT_NEW_PRODUCT'
            if not self.operating:
                self.phase='STOPPED_DRAINING' if self.coordinator.active_cycle or self.service.active else 'STOPPED'
        transition=(tracker._track_id,tracker._state.value,self.eligible)
        if transition!=self.last_transition:
            self.last_transition=transition
            self._event({'event':'PRODUCTION_TRACK_STATE','track_id':tracker._track_id,'state':tracker._state.value,
                'eligible':self.eligible,'frame_id':packet['frame_id'],'sequence':packet['sequence']})
        self.logger.info(json.dumps({'event':'PRODUCTION_OBSERVATION','runtime_session_id':self.session_id,
            'track_id':tracker._track_id,'phase':self.phase,'packet':packet},ensure_ascii=False))
        if not self.operating and not self.coordinator.active_cycle and not self.service.active:
            self.service.production_tracking.clear(); self.phase='STOPPED'

    def _trigger(self,now):
        if not self.operating or self.error or self.handshake.state!='REQUEST_LATCHED' or self.service.active: return
        if self.area_config_version and self.coordinator._tracker._state==TrackState.WAIT_AREA_CLEAR: return
        expired=now-self.handshake.accepted_at>=self.request_wait_seconds
        if not expired and not (self.eligible and self.latest_packet.get('stable')): return
        tracker=self.coordinator._tracker
        if tracker._track_id in self.inspected_tracks:
            self.handshake.fault('REQUEST_FOR_ALREADY_INSPECTED_TRACK','BLOCKED'); return
        packet=self.latest_packet or {}
        binding=dict(runtime_session_id=self.session_id,
            cycle_id=self.coordinator.active_cycle.cycle_id if self.coordinator.active_cycle else None,
            track_id=tracker._track_id if self.eligible else None,plc_request_token=self.handshake.token,
            camera_epoch=self.epoch,worker_generation=self.service.generation,
            package_manifest_sha=self.service.package.manifest_hash,inspection_zone=self.zone,
            sequence=packet.get('sequence',-1),monotonic_s=packet.get('monotonic_s',0),
            product_box=None,authority='WHOLE_PRODUCT_TRACK_AND_LATCHED_PLC_REQUEST',
            trigger_reason='REQUEST_TRACK_TIMEOUT_DIAGNOSTIC' if not self.eligible else 'TRACK_IN_ZONE_AND_PLC_EDGE')
        if self.eligible:
            box=packet['provider']['observations'][0]['bbox']
            binding['product_box']=[box[k] for k in ('x1','y1','x2','y2')]
        self.bridge=InspectionBridge(self.service,self.coordinator)
        self.bridge.submit_production(binding)
        self.handshake.bind(self.bridge.inspection_id)
        if binding['track_id'] is not None: self.inspected_tracks.add(binding['track_id'])
        self.phase='INSPECTING'; self.pending_started=now
        self._event({'event':'PRODUCTION_INSPECTION_BOUND','inspection_id':self.bridge.inspection_id,'identity':binding})

    def _poll_result(self,now):
        if not self.bridge.inspection_id or self.bridge.inspection_id in self.published_ids: return
        updated=self.bridge.poll()
        if updated: self.snapshot=updated
        if self.bridge.error:
            self._fault('INSPECTION_DURABLE_BOUNDARY: '+self.bridge.error); return
        if self.bridge.phase!='INSPECTION_DURABLE': return
        identifier=self.bridge.inspection_id
        row=self.service.journal.detail(identifier)
        self.published_ids.add(identifier)  # Never auto-retry uncertain publication.
        if not self.error: self.handshake.publish(identifier,row['decision'],True,now)
        else: self.handshake.fault(self.error,'BLOCKED')
        entry=dict(inspection_id=identifier,track_id=self.bridge.request['runtime_binding']['track_id'],
            plc_request_token=self.bridge.request['runtime_binding']['plc_request_token'],
            vision_decision=row['decision'],reason=row['result'].get('reason_code',row['result'].get('reason')),
            completed_at=row.get('completed_at'),publication_status=self.handshake.publication,
            request_to_publication_ms=(now-self.handshake.accepted_at)*1000,
            timing=self.service.latest_timing)
        self.history.appendleft(entry)
        self.phase='WAIT_AREA_CLEAR' if self.coordinator._tracker._state==TrackState.WAIT_AREA_CLEAR else 'INSPECTED'
        self._event(dict(event='PRODUCTION_INSPECTION_COMPLETED',**entry))

    def _run(self):
        while not self.stop.wait(.02):
            with self.lock,self.service.lock:
                if self.closing: continue
                try:
                    while True:
                        try: packet=self.service.products.get_nowait()
                        except queue.Empty: break
                        self._packet(packet)
                    now=time.monotonic()
                    if self.operating or self.handshake.token: self.handshake.poll(now)
                    self._poll_result(now)
                    self._trigger(now)
                    observation_since=(self.latest_packet['processed_monotonic'] if self.latest_packet
                        else self.observation_started_at)
                    if self.operating and observation_since is not None and now-observation_since>self.observation_stale_seconds:
                        # A latched request still obtains an explicit durable system ERROR, never a missing-product FAIL.
                        if self.handshake.state=='REQUEST_LATCHED':
                            self._trigger(now+self.request_wait_seconds)
                            self._poll_result(now)
                        # Keep acknowledged ERROR publication/Request OFF separate from camera health.
                        self.error='CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE'
                        self.area_window.reset()
                        self.operating=False; self.eligible=False; self.phase='FAULT'
                        self._event({'event':'PRODUCTION_CAMERA_FAULT','reason':self.error})
                except Exception as error:
                    self.logger.exception('Production AUTO boundary failed')
                    try: self._fault(type(error).__name__+': '+str(error))
                    except Exception: self.error='JOURNAL_UNAVAILABLE'; self.operating=False

    def status(self):
        value=super().status()
        with self.lock:
            plc_status=self.handshake.status()
        packet=self.latest_packet
        fresh=bool(packet and time.monotonic()-packet['processed_monotonic']<2 and self.service.status()['camera_ready'])
        area=self.area_observation if fresh else self._preview_area()
        area_approved=self._area_approval_current(area)
        if area and not area_approved:
            area=dict(area,state='UNKNOWN',reference_valid=False,clear_duration_s=0,
                      reason=('CURRENT_VALID_AREA_OBSERVATION_REQUIRED' if not self.area_reference_required
                              else 'MAINTENANCE_AREA_REFERENCE_APPROVAL_REQUIRED'))
        value.update(mode='production',operating=self.operating,phase=self.phase,
            auto_stop_requested=self.auto_stop_requested,inspection_zone=self.zone,
            area_clearance_enabled=bool(self.area_config_version),
            area_clearance_mode='DARK_SURFACE_SELF_OBSERVED' if not self.area_reference_required else 'STATIC_REFERENCE',
            area_occupancy=area,
            area_reference_approved=area_approved if self.area_reference_required else False,
            area_observation_valid=area_approved,
            area_wait_reason=self.area_wait_reason,last_retirement=self.last_retirement,
            area_wait_limit_exceeded=bool(self.area_wait_started is not None and time.monotonic()-self.area_wait_started>60),
            departure_edge=self.departure_edge,
            departure_clearance_eligible=self.departure_clearance_eligible,
            eligible=self.eligible and fresh,latest_frame=packet if fresh else None,stale_observation=not fresh,
            history=list(self.history),plc=plc_status,
            observation_fps=((len(self.observation_times)-1)/(self.observation_times[-1]-self.observation_times[0])
                if fresh and len(self.observation_times)>1 else None),
            human_acceptance='PENDING',physical_output_enabled=False,
            real_plc='BENCH_TAG_ACCESS_ONLY' if self.gateway.backend!='MOCK' else 'COMMISSIONING_REQUIRED',
            connection_plan=self.connection_plan,per_product_manual_controls=False)
        return value

    def close(self):
        try:
            super().close()
        finally:
            self.gateway.close()
