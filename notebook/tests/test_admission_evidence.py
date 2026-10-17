"""Stored three-frame evidence must retain the Service's durable admission floor."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.runtime.completed_evidence import validate_completed_evidence


def stored_result(*, with_floor=True):
    binding = dict(package_manifest_sha='package', worker_generation='worker',
        camera_epoch='camera', sequence=5, monotonic_s=10.1)
    request = dict(runtime_binding=binding, package_sha256='package')
    observations, checks, assets = [], [], []
    for index in range(3):
        identity = f'frame-{index}'
        fresh = dict(frame_id=identity, estimated_source_monotonic=10.6 + index * .1,
            sequence=6 + index, camera_epoch='camera', integrity={'valid': True})
        observations.append(dict(frame_id=identity, freshness=fresh,
            input_pixel_sha256=f'pixels-{index}'))
        checks.append(dict(frame_id=identity, failed_conditions=[]))
        assets.append(dict(frame_id=identity, kind='raw', inspection_id='inspection',
            sha256=f'encoded-{index}'))
    result = dict(inspection_id='inspection', storage_success=True, request=request,
        production_identity=dict(binding, inspection_id='inspection'),
        execution={'worker_generation': 'worker'}, observations=observations,
        production_frame_checks=checks, assets=assets)
    if with_floor:
        result.update(durable_admission_monotonic=10.55,
            fresh_frame=dict(trigger={'trigger_received_monotonic': 10.2},
                source_not_before_monotonic=10.55,
                effective_source_not_before_monotonic=10.55,
                selected_frames=[copy.deepcopy(item['freshness']) for item in observations]))
    row = dict(inspection_id='inspection', state='COMPLETE', request=request, result=result)
    return row, binding


class AdmissionEvidenceTests(unittest.TestCase):
    def validate(self, row, binding):
        return validate_completed_evidence(row, binding, 'inspection', 10., 11., 'package')

    def test_valid_post_durable_three_originals_pass(self):
        self.assertIsNone(self.validate(*stored_result()))

    def test_pre_durable_frame_is_rejected_even_if_freshness_record_agrees(self):
        row, binding = stored_result()
        row['result']['observations'][0]['freshness']['estimated_source_monotonic'] = 10.4
        row['result']['fresh_frame']['selected_frames'][0]['estimated_source_monotonic'] = 10.4
        with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE_'):
            self.validate(row, binding)

    def test_durable_boundary_is_exclusive(self):
        row, binding = stored_result()
        row['result']['observations'][0]['freshness']['estimated_source_monotonic'] = 10.55
        row['result']['fresh_frame']['selected_frames'][0]['estimated_source_monotonic'] = 10.55
        with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE_'):
            self.validate(row, binding)

    def test_tampered_or_missing_admission_metadata_is_rejected(self):
        changes = {
            'missing fresh block': lambda r: r.pop('fresh_frame'),
            'missing worker floor': lambda r: r['fresh_frame'].pop('source_not_before_monotonic'),
            'missing effective floor': lambda r: r['fresh_frame'].pop('effective_source_not_before_monotonic'),
            'missing server floor': lambda r: r.pop('durable_admission_monotonic'),
            'lower worker floor': lambda r: r['fresh_frame'].update(source_not_before_monotonic=10.3),
            'lower server floor': lambda r: r.update(durable_admission_monotonic=10.3),
            'lower effective floor': lambda r: r['fresh_frame'].update(effective_source_not_before_monotonic=10.3),
            'future floor': lambda r: r.update(durable_admission_monotonic=12.),
            'floor before trigger': lambda r: r['fresh_frame']['trigger'].update(trigger_received_monotonic=10.56),
            'trigger before request': lambda r: r['fresh_frame']['trigger'].update(trigger_received_monotonic=9.),
            'missing trigger': lambda r: r['fresh_frame'].pop('trigger'),
            'none': lambda r: r.update(durable_admission_monotonic=None),
            'nan': lambda r: r.update(durable_admission_monotonic=float('nan')),
            'infinity': lambda r: r.update(durable_admission_monotonic=float('inf')),
            'boolean': lambda r: r.update(durable_admission_monotonic=True),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                row, binding = stored_result()
                change(row['result'])
                with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE_'):
                    self.validate(row, binding)

    def test_missing_or_mismatched_selected_originals_are_rejected(self):
        changes = {
            'missing': lambda f: f.pop('selected_frames'),
            'too few': lambda f: f['selected_frames'].pop(),
            'reordered': lambda f: f['selected_frames'].reverse(),
            'time mismatch': lambda f: f['selected_frames'][0].update(estimated_source_monotonic=10.7),
            'sequence mismatch': lambda f: f['selected_frames'][0].update(sequence=9),
            'epoch mismatch': lambda f: f['selected_frames'][0].update(camera_epoch='other'),
            'id mismatch': lambda f: f['selected_frames'][0].update(frame_id='other'),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                row, binding = stored_result()
                change(row['result']['fresh_frame'])
                with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE_'):
                    self.validate(row, binding)

    def test_old_rows_without_admission_floor_preserve_existing_validation(self):
        row, binding = stored_result(with_floor=False)
        self.assertIsNone(self.validate(row, binding))
        row['result']['observations'][0]['freshness']['estimated_source_monotonic'] = 10.
        with self.assertRaisesRegex(ValueError, 'COMPLETED_EVIDENCE_FRAME_ORDER'):
            self.validate(row, binding)


if __name__ == '__main__':
    unittest.main()
