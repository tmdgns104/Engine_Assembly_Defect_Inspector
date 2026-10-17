"""Validate the already stored inspection, without reclassifying a preview.

Journal owns atomic image/result storage. This bounded metadata check ties its
three originals to the accepted request; it does not re-read PNGs under the
Runtime lock or introduce another inference/threshold decision.
"""
import math


def validate_completed_evidence(row, binding, identifier, accepted_at, now, package_sha):
    def require(condition, reason):
        if not condition:
            raise ValueError('COMPLETED_EVIDENCE_' + reason)

    try:
        result = row['result']
        require(row['inspection_id'] == identifier and row['state'] == 'COMPLETE'
                and result['storage_success'] is True, 'NOT_DURABLE')
        require(result['inspection_id'] == identifier and result['request'] == row['request']
                and row['request']['runtime_binding'] == binding
                and result['production_identity'] == dict(binding, inspection_id=identifier), 'IDENTITY')
        require(binding['package_manifest_sha'] == package_sha
                and row['request']['package_sha256'] == package_sha
                and result['execution']['worker_generation'] == binding['worker_generation'], 'PACKAGE_OR_WORKER')
        observations = result['observations']
        checks = result['production_frame_checks']
        assets = [a for a in result['assets'] if a['kind'] == 'raw']
        require(len(observations) == len(checks) == len(assets) == 3, 'THREE_ORIGINALS_REQUIRED')
        ids = [o['frame_id'] for o in observations]
        require(len(set(ids)) == 3 and {a['frame_id'] for a in assets} == set(ids)
                and [c['frame_id'] for c in checks] == ids
                and all(not c['failed_conditions'] for c in checks), 'FRAME_BINDING')
        require(all(a['inspection_id'] == identifier for a in assets)
                and len({a['sha256'] for a in assets}) == 3
                and len({o['input_pixel_sha256'] for o in observations}) == 3, 'ASSET_IDENTITY')
        previous_time = max(accepted_at, binding['monotonic_s'])
        freshness = result.get('fresh_frame') or {}
        floor_keys = ('source_not_before_monotonic', 'effective_source_not_before_monotonic')
        # The Service stamps its own admission receipt before raw result storage.
        # A Worker-only floor cannot substitute for that trusted boundary. Old
        # records without either field keep their original publication contract.
        has_floor = ('durable_admission_monotonic' in result
                     or any(key in freshness for key in floor_keys))
        if has_floor:
            floor = result['durable_admission_monotonic']
            trigger_time = freshness['trigger']['trigger_received_monotonic']
            effective = freshness['effective_source_not_before_monotonic']
            reported_floor = freshness['source_not_before_monotonic']
            require(all(type(value) in (int, float) and math.isfinite(value)
                        for value in (floor, trigger_time, effective, reported_floor))
                    and accepted_at <= trigger_time <= floor <= now
                    and reported_floor == floor
                    and effective == max(trigger_time, floor), 'ADMISSION_FLOOR')
            selected = freshness['selected_frames']
            require(isinstance(selected, list) and len(selected) == len(observations)
                    and all(all(item[key] == observation['freshness'][key]
                                for key in ('frame_id', 'estimated_source_monotonic',
                                            'sequence', 'camera_epoch'))
                            and type(item['sequence']) is int
                            for item, observation in zip(selected, observations)),
                    'ADMISSION_FRAME_BINDING')
            previous_time = max(previous_time, effective)
        previous_sequence = binding['sequence']
        for observation in observations:
            fresh = observation['freshness']
            source = fresh['estimated_source_monotonic']
            require(type(source) in (int, float) and math.isfinite(source)
                    and previous_time < source <= now
                    and type(fresh['sequence']) is int and fresh['sequence'] > previous_sequence,
                    'FRAME_ORDER')
            require(fresh['camera_epoch'] == binding['camera_epoch']
                    and fresh['frame_id'] == observation['frame_id']
                    and fresh['integrity']['valid'] is True, 'FRAME_SOURCE')
            previous_time, previous_sequence = source, fresh['sequence']
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('COMPLETED_EVIDENCE_INCOMPLETE') from error
