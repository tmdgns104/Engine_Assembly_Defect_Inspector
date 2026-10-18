"""Explicit PLC request admission, independent of crop/pose and departure evidence."""
from src import config as parameters
import math

FULL_FRAME = 'PLC_REQUEST_TRACKED_FULL_FRAME'
FIXED_ZONE = 'FIXED_ZONE'


def start_policy(profile, contract):
    policy = (profile or {}).get('inspection_start_policy', FIXED_ZONE)
    if policy not in (FIXED_ZONE, FULL_FRAME):
        raise ValueError('UNKNOWN_INSPECTION_START_POLICY')
    if policy == FULL_FRAME and contract != 'OPENER_CYCLIC':
        raise ValueError('FULL_FRAME_REQUIRES_OPENER_CYCLIC')
    if policy == FULL_FRAME:
        supervised = 'SUPERVISED_REPEAT_TEST'
        if ((profile.get('cycle_admission') == supervised) !=
                (profile.get('initial_authorization') == supervised)):
            raise ValueError('MATCHED_SUPERVISED_AUTHORIZATION_REQUIRED')
        automatic = 'PLC_AUTOMATIC_REPEAT'
        if profile.get('cycle_admission') not in ('FIRST_PRODUCT_ONLY', 'VERIFIED_CLEARANCE', supervised, automatic):
            raise ValueError('EXPLICIT_CYCLE_ADMISSION_REQUIRED')
        qualification = profile.get('request_start_qualification', {})
        if type(qualification.get('verified')) is not bool:
            raise ValueError('EXPLICIT_REQUEST_START_QUALIFICATION_REQUIRED')
    return policy


def tracked_frame_evidence(packet, accepted_at, epoch, generation, now, max_age=parameters.ADMISSION_PREVIEW_MAX_AGE_SECONDS):
    """One current product and a source frame strictly newer than the PLC edge.

    This says nothing about motor feedback, whole-product visibility or AI quality.
    Track continuity is owned by the coordinator, not by this packet-only predicate.
    """
    if not packet or epoch is None or generation is None:
        return False
    try:
        source = packet['monotonic_s']
        processed = packet['processed_monotonic']
        if (not all(type(v) in (int, float) and math.isfinite(v)
                    for v in (source, processed, accepted_at, now))
                or not accepted_at < source <= processed <= now
                or now-source >= max_age or now-processed >= max_age):
            return False
        if packet['camera_epoch'] != epoch or packet['generation'] != generation:
            return False
        provider = packet['provider']
        observations = provider['observations']
        if (packet['integrity']['valid'] is not True or
                provider['status'] != 'PRODUCT_OBSERVED' or len(observations) != 1):
            return False
        box = observations[0]['bbox']
        x1, y1, x2, y2 = (box[k] for k in ('x1', 'y1', 'x2', 'y2'))
        return bool(packet.get('frame_id') and type(packet['sequence']) is int
                    and packet['sequence'] >= 0
                    and all(type(v) in (int, float) and math.isfinite(v)
                            for v in (x1, y1, x2, y2))
                    and 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1)
    except (KeyError, TypeError, ValueError):
        return False
