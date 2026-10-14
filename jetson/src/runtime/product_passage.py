"""Product-specific passage evidence from existing detector observations.

This is a qualified geometry policy, not an empty-scene detector or a new AI
model. A single product must move continuously towards the configured exit,
cross it without box growth, and leave a shrinking tail. Subsequent continuous
observations must exclude that exit strip; a separated upstream product is
allowed. Camera visibility, direction and spacing need field qualification.
"""
import math


class ProductPassage:
    def __init__(self, identity, packet, edge):
        self.identity = dict(identity)
        self.edge = edge
        self.last = packet
        boxes = packet['provider']['observations']
        self.box = boxes[0]['bbox'] if len(boxes) == 1 else None
        self.origin = self.box
        self.crossed = False
        self.tail = False
        self.samples = []
        self.reason = 'WAIT_OUTBOUND_PRODUCT_TRAJECTORY'
        self.invalid = False
        self.proof = None

    def _axis(self, box):
        # Express both supported horizontal directions as progress towards 1.
        return ((box['x1'], box['x2']) if self.edge == 'right'
                else (1-box['x2'], 1-box['x1']))

    def _fail(self, reason):
        self.invalid = True
        self.reason = reason
        self.proof = None
        return None

    def observe(self, p, now):
        if self.invalid:
            return None
        old = self.last
        if (self.edge not in ('left', 'right') or not self.origin
                or not p.get('frame_id') or p['frame_id'] == old.get('frame_id')
                or p.get('integrity', {}).get('valid') is not True
                or any(p.get(k) != old.get(k) for k in ('camera_epoch', 'generation', 'package_sha256'))
                or p['sequence'] != old['sequence']+1
                or not 0 < p['monotonic_s']-old['monotonic_s'] <= .5
                or not 0 <= now-p['monotonic_s'] <= 1):
            return self._fail('PRODUCT_PASSAGE_FRAME_CONTINUITY_INVALID')
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
        if not self.tail:
            if not current:
                return self._fail('PRODUCT_LOST_BEFORE_OBSERVED_EXIT_TAIL')
            a, b = self._axis(self.box)
            x, y = self._axis(current)
            origin_a, origin_b = self._axis(self.origin)
            # IoU identity is not inferred across a jump, reversal or enlargement.
            if (x < a-1e-9 or x >= b or y < b-1e-9 or
                    y-x > b-a+1e-9 or
                    min(current['y2'], self.box['y2']) <= max(current['y1'], self.box['y1']) or
                    current['y2']-current['y1'] > self.box['y2']-self.box['y1']+1e-9):
                return self._fail('PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY')
            if b < 1 and y == 1 and x > a:
                self.crossed = True
            self.box = current
            # A box initially clipped at the edge never supplies the crossing.
            self.tail = self.crossed and y == 1 and y-x <= .2*(origin_b-origin_a)+1e-9
            self.reason = 'WAIT_EXIT_STRIP_OBSERVATIONS' if self.tail else self.reason
            return None
        # No need for a globally empty image. A single disjoint upstream engine
        # can occupy the image while the old product's exit strip is observed.
        exit_start, _ = self._axis(self.box)
        if current:
            x, y = self._axis(current)
            if y >= exit_start:
                # A tail that grows or reverses is still the previous product,
                # never a disjoint successor after several occupied frames.
                a, b = self._axis(self.box)
                if (x < a-1e-9 or x >= b or y < b-1e-9 or
                        y-x > b-a+1e-9 or
                        min(current['y2'], self.box['y2']) <= max(current['y1'], self.box['y1']) or
                        current['y2']-current['y1'] > self.box['y2']-self.box['y1']+1e-9):
                    return self._fail('PRODUCT_EXIT_TAIL_REVERSED_OR_CHANGED')
                self.box = current
                self.samples = []
                self.reason = 'PREVIOUS_EXIT_STRIP_STILL_OCCUPIED'
                return None
        self.samples.append((p['sequence'], p['monotonic_s']))
        self.samples = self.samples[-128:]
        if len(self.samples) < 6 or self.samples[-1][1]-self.samples[0][1] < 1.2-1e-9:
            return None
        self.proof = dict(self.identity, reason='PRODUCT_TRAJECTORY_AND_EXIT_STRIP',
            edge=self.edge, frame_id=p['frame_id'], sequence=p['sequence'],
            source_monotonic=p['monotonic_s'], camera_epoch=p['camera_epoch'],
            generation=p['generation'], sequences=[s for s, _ in self.samples],
            duration_s=self.samples[-1][1]-self.samples[0][1],
            whole_scene_empty_required=False, area_clearance_used=False,
            next_product_visible=bool(current), sensor_cycle_observed=False)
        self.reason = 'PRODUCT_SEPARATION_OBSERVED'
        return self.proof

    def status(self):
        return dict(reason=self.reason, invalid=self.invalid, proof=self.proof,
                    previous=self.identity, whole_scene_empty_required=False)
