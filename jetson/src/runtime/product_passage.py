"""Product-specific passage evidence from existing detector observations.

This uses the existing detector and Track bounds, not an empty-scene model.
A witnessed shrinking tail plus continuous exit-strip observations can prove
exit. If partial detection ends earlier, only positive new entry at the opposite
edge, after the old outbound trajectory, can prove a separate product cycle.
That second route never claims complete physical exit or AI Area CLEAR.
Camera visibility, direction and spacing still need field qualification.
"""
import math


class ProductPassage:
    def __init__(self, identity, packet, edge, *, tracker_config=None):
        self.identity = dict(identity)
        self.edge = edge
        self.last = packet
        boxes = packet['provider']['observations']
        self.box = boxes[0]['bbox'] if len(boxes) == 1 else None
        self.origin = self.box
        self.last_product = packet if self.box else None
        self.crossed = False
        self.tail = False
        self.samples = []
        self.reason = 'WAIT_OUTBOUND_PRODUCT_TRAJECTORY'
        self.invalid = False
        self.proof = None
        self.tracker_config = tracker_config
        # Reuse the production Track's spatial hysteresis, not a new detector
        # threshold. Older packets without dimensions keep exact geometry.
        self.jitter = (tracker_config.zone_hysteresis if tracker_config and
                       packet.get('width', 0) > 0 else 0.)
        self.pixel = 1/packet['width'] if packet.get('width', 0) > 0 else 0.
        self.furthest = sum(self._axis(self.box))/2 if self.box else 0.
        self.outbound_samples = 0
        self.entry = None
        self.geometry_pending = False
        self.settled_transaction = None

    @classmethod
    def from_history(cls, identity, packets, edge, *, tracker_config):
        """Continue the same bound request across an empty publication frame.

        Runtime supplies only its bounded, validated observations for this
        request/Track. Missing detections preserve uncertainty, never exit.
        """
        seed = next((i for i in range(len(packets)-1, -1, -1)
                     if len(packets[i]['provider']['observations']) == 1), None)
        passage = cls(identity, packets[seed if seed is not None else -1],
                      edge, tracker_config=tracker_config)
        if seed is None:
            passage._fail('PRODUCT_PASSAGE_PRODUCT_BASELINE_MISSING')
            return passage
        if (packets[seed].get('integrity', {}).get('valid') is not True or
                packets[seed]['provider']['status'] != 'PRODUCT_OBSERVED'):
            passage._fail('PRODUCT_PASSAGE_FRAME_CONTINUITY_INVALID')
        for p in packets[seed+1:]:
            passage.observe(p, p['processed_monotonic'])
        return passage

    def _axis(self, box):
        # Express both supported horizontal directions as progress towards 1.
        return ((box['x1'], box['x2']) if self.edge == 'right'
                else (1-box['x2'], 1-box['x1']))

    def _fail(self, reason):
        self.invalid = True
        self.reason = reason
        self.proof = None
        return None

    def _outbound_rejection(self, current, elapsed):
        a, b = self._axis(self.box)
        x, y = self._axis(current)
        center = (x+y)/2
        if (x < a-self.jitter-1e-9 or x >= b or y < b-self.jitter-1e-9
                or center < self.furthest-self.jitter-1e-9
                or min(current['y2'],self.box['y2']) <= max(current['y1'],self.box['y1'])):
            return 'MOTION_OR_OVERLAP'
        if self.tracker_config:
            limit = self.tracker_config.max_center_step_norm
            limit += (self.tracker_config.max_center_speed_norm_s or 0)*elapsed
            cross_step = (current['y1']+current['y2']-self.box['y1']-self.box['y2'])/2
            if math.hypot(center-(a+b)/2,cross_step) > limit:
                return 'MOTION_OR_OVERLAP'
        elif current['y2']-current['y1'] > self.box['y2']-self.box['y1']+1e-9:
            return 'SHAPE_CHANGED'
        # A noisy width measurement is not evidence of either departure or a
        # different product. Keep the last trusted box for bounded reassociation.
        if y-x > b-a+2*self.jitter+1e-9:
            return 'SHAPE_CHANGED'
        return None

    def _observe_entry(self, current, p):
        """Positive entry from the opposite edge, separate from the old box.

        This proves a separate inspection cycle, not that every old pixel left
        the image. Neither Request LOW nor missing detections can supply it.
        """
        if not self.tracker_config or not self.crossed or self.outbound_samples < 6:
            return False
        x,y = self._axis(current)
        old_start,_ = self._axis(self.box)
        oa,ob = self._axis(self.origin)
        if self.furthest-(oa+ob)/2 < (ob-oa)/2 or y >= old_start:
            self.entry = None
            return False
        center = (x+y)/2
        if self.entry is None:
            # Detector boxes need not clip to the exact outer pixel. Reuse the
            # same spatial hysteresis for the upstream boundary observation.
            if x > max(self.pixel,self.jitter) or center >= (oa+ob)/2:
                return False
            self.entry = dict(first_sequence=p['sequence'],last_sequence=p['sequence'],
                first_frame_id=p['frame_id'],last_frame_id=p['frame_id'],
                first_time=p['monotonic_s'],last_time=p['monotonic_s'],
                first_center=center,last_center=center,last_box=dict(current),samples=1,
                window_time=p['monotonic_s'],window_center=center)
        else:
            e = self.entry
            step = center-e['last_center']
            gap = p['sequence']-e['last_sequence']-1
            elapsed = p['monotonic_s']-e['last_time']
            limit = self.tracker_config.max_center_step_norm
            if gap:
                limit += (self.tracker_config.max_center_speed_norm_s or 0)*elapsed
            if (gap > self.tracker_config.max_missed_frames
                    or (self.tracker_config.max_unobserved_seconds is not None and
                        elapsed > self.tracker_config.max_unobserved_seconds)
                    or step < -self.jitter or step > limit
                    or min(current['x2'],e['last_box']['x2']) <= max(current['x1'],e['last_box']['x1'])
                    or min(current['y2'],e['last_box']['y2']) <= max(current['y1'],e['last_box']['y1'])):
                self.entry = None
                return False
            # Keep the observed upstream identity across a bounded gap, but
            # restart the consecutive proof window. A gap supplies no evidence.
            if gap or e['samples'] == 0:
                e.update(samples=0,window_time=p['monotonic_s'],window_center=center)
            e.update(last_sequence=p['sequence'],last_frame_id=p['frame_id'],
                last_time=p['monotonic_s'],last_center=center,last_box=dict(current),samples=e['samples']+1)
        e = self.entry
        return (e['samples'] >= 3 and e['last_time']-e['window_time'] >= .2-1e-9
                and e['last_center']-e['window_center'] >= max(self.jitter,self.pixel))

    def observe(self, p, now):
        if self.invalid:
            return None
        old = self.last
        if (self.edge not in ('left', 'right') or not self.origin
                or not p.get('frame_id') or p['frame_id'] == old.get('frame_id')
                or p.get('integrity', {}).get('valid') is not True
                or any(p.get(k) != old.get(k) for k in ('camera_epoch', 'generation', 'package_sha256'))
                or p['sequence'] <= old['sequence']
                or (not self.tracker_config and p['sequence'] != old['sequence']+1)
                or not 0 < p['monotonic_s']-old['monotonic_s'] <= .5
                or not 0 <= now-p['monotonic_s'] <= 1):
            return self._fail('PRODUCT_PASSAGE_FRAME_CONTINUITY_INVALID')
        if p['sequence'] != old['sequence']+1:
            # Tracking may associate two actual observations across a short
            # gap. Missing frames never count towards the exit-strip window.
            self.samples = []
        self.last = p
        provider = p['provider']
        boxes = provider['observations']
        if (len(boxes) > 1 or provider['status'] not in ('PRODUCT_OBSERVED', 'NO_FOREGROUND')):
            return self._fail('PRODUCT_PASSAGE_OCCLUSION_OR_AMBIGUITY')
        current = boxes[0]['bbox'] if boxes else None
        if current and not (all(type(current.get(k)) in (int, float) and math.isfinite(current[k])
                for k in ('x1', 'y1', 'x2', 'y2')) and
                0 <= current['x1'] < current['x2'] <= 1 and 0 <= current['y1'] < current['y2'] <= 1):
            return self._fail('PRODUCT_PASSAGE_INVALID_BOX')
        if self.entry and not current:
            e = self.entry
            if (p['sequence']-e['last_sequence'] > self.tracker_config.max_missed_frames or
                    (self.tracker_config.max_unobserved_seconds is not None and
                     p['monotonic_s']-e['last_time'] > self.tracker_config.max_unobserved_seconds)):
                return self._fail('PRODUCT_PASSAGE_ENTRY_REOBSERVATION_LIMIT')
            e['samples'] = 0
            self.samples = []
            self.reason = 'WAIT_ENTRY_REOBSERVATION'
            return None
        if self.tracker_config and (not self.crossed or self.geometry_pending):
            # Reuse the Track's existing loss bounds. Valid camera frames can
            # intermittently contain no detector box while the belt is stopped.
            # Reappearance must still associate with the last actual product.
            elapsed = p['monotonic_s']-self.last_product['monotonic_s']
            missed = p['sequence']-self.last_product['sequence']-int(current is not None)
            if (missed > self.tracker_config.max_missed_frames or
                    (self.tracker_config.max_unobserved_seconds is not None and
                     elapsed > self.tracker_config.max_unobserved_seconds)):
                return self._fail('PRODUCT_PASSAGE_REOBSERVATION_LIMIT')
            if not current:
                self.samples = []
                self.entry = None
                self.reason = 'WAIT_SAME_PRODUCT_REOBSERVATION'
                return None
        entry_ready = False
        if current and self.crossed and not self.geometry_pending:
            entry_ready = self._observe_entry(current,p)
        if not self.tail and not self.entry:
            if not current and not (self.tracker_config and self.crossed):
                return self._fail('PRODUCT_LOST_BEFORE_OBSERVED_EXIT_TAIL')
        if current and not self.entry:
            a, b = self._axis(self.box)
            x, y = self._axis(current)
            origin_a, origin_b = self._axis(self.origin)
            # A disjoint upstream successor after a witnessed shrinking tail
            # is still the original supported exit-strip path.
            disjoint_after_tail = self.tail and y < a and not self.geometry_pending
            if not disjoint_after_tail:
                rejection = self._outbound_rejection(
                    current, p['monotonic_s']-self.last_product['monotonic_s'])
                if rejection == 'SHAPE_CHANGED' and self.tracker_config:
                    self.geometry_pending = True
                    self.samples = []
                    self.entry = None
                    self.proof = None
                    self.reason = 'WAIT_SAME_PRODUCT_GEOMETRY'
                    return None
                if rejection:
                    return self._fail('PRODUCT_EXIT_TAIL_REVERSED_OR_CHANGED' if self.tail
                                      else 'PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY')
            if (origin_b < 1-self.pixel and b < 1-self.pixel
                    and y >= 1-self.pixel and x > origin_a+self.jitter):
                self.crossed = True
            if not disjoint_after_tail:
                self.geometry_pending = False
                self.furthest = max(self.furthest, (x+y)/2)
                self.box = current
                self.last_product = p
                self.outbound_samples += 1
                # Once witnessed, retain the tail through subpixel boundary jitter.
                self.tail = self.tail or (self.crossed and y >= 1-self.pixel
                                          and y-x <= .2*(origin_b-origin_a)+1e-9)
                self.samples = []
                self.reason = 'PREVIOUS_EXIT_STRIP_STILL_OCCUPIED' if self.tail else 'WAIT_OUTBOUND_PRODUCT_TRAJECTORY'
                return None
        # No need for a globally empty image. A single disjoint upstream engine
        # can occupy the image while the old product's exit strip is observed.
        exit_start, _ = self._axis(self.box)
        if current and not self.entry:
            x, y = self._axis(current)
            if y >= exit_start:
                self.samples = []
                return None
        if not current:
            self.entry = None
        self.samples.append((p['sequence'], p['monotonic_s']))
        self.samples = self.samples[-128:]
        if len(self.samples) < 6 or self.samples[-1][1]-self.samples[0][1] < 1.2-1e-9:
            return None
        if not self.tail and not entry_ready:
            self.reason = 'WAIT_POSITIVE_UPSTREAM_ENTRY_AFTER_OUTBOUND'
            return None
        self.proof = dict(self.identity, reason=('PRODUCT_TRAJECTORY_AND_EXIT_STRIP' if self.tail
            else 'OUTBOUND_PRODUCT_AND_NEW_UPSTREAM_ENTRY'),
            edge=self.edge, frame_id=p['frame_id'], sequence=p['sequence'],
            source_monotonic=p['monotonic_s'], camera_epoch=p['camera_epoch'],
            generation=p['generation'], sequences=[s for s, _ in self.samples],
            duration_s=self.samples[-1][1]-self.samples[0][1],
            whole_scene_empty_required=False, area_clearance_used=False,
            next_product_visible=bool(current), sensor_cycle_observed=False,
            product_exit_claimed=self.tail, upstream_entry=dict(self.entry) if self.entry else None)
        self.reason = 'PRODUCT_SEPARATION_OBSERVED'
        return self.proof

    def status(self):
        return dict(reason=self.reason, invalid=self.invalid, proof=self.proof,
                    previous=self.identity, whole_scene_empty_required=False,
                    crossed=self.crossed, tail=self.tail, outbound_samples=self.outbound_samples,
                    geometry_pending=self.geometry_pending, entry=dict(self.entry) if self.entry else None,
                    last_trusted_box=dict(self.box) if self.box else None,
                    last_trusted_frame={k:self.last_product.get(k) for k in
                        ('frame_id','sequence','monotonic_s','camera_epoch','generation')}
                        if self.last_product else None,
                    last_observed_frame={k:self.last.get(k) for k in ('frame_id','sequence','monotonic_s')},
                    exit_window_samples=len(self.samples),
                    settled_transaction=self.settled_transaction)
