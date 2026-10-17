"""Autostart is insufficient while historical product identity blocks requests."""
import copy
import unittest
from notebook.deployment.check_reboot_ready import validate_ready


class RebootReadinessTests(unittest.TestCase):
    def setUp(self):
        self.status = dict(runtime_loop_alive=True, error=None, runtime_issue=None,
            aborted_inspection=None, final_commit_pending=False,
            inspection_service=dict(state='IDLE', worker_alive=True, camera_ready=True,
                error=None, active_inspection_id=None, storage_pending=False),
            assembly_component=dict(ready=True, error=None, outstanding=0, active_identifier=None),
            ipc_health=dict(latest=dict(IPC_HEALTH_SENT=dict(ready=True))),
            plc_cycle=dict(reason='WAIT_NEW_PHYSICAL_START', product_identity_reason=None,
                request_identity_block=None),
            plc=dict(snapshot=dict(connected=True, fresh=True, bool_valid=True, run_idle=True,
                raw100='00000000', phase='SYNC_LOW', controls=dict(Inspection_Request=False,
                    Mc_Run=False, EStop_OK=True, Stop_PB=True))))
        self.view = dict(phase='WAIT_START', camera=dict(fresh=True))

    def test_stopped_ready_accepts_without_result_or_inspection(self):
        original = copy.deepcopy(self.status)
        validate_ready(self.status, self.view)
        self.assertEqual(self.status, original)

    def test_previous_product_blocks_despite_all_hardware_ready(self):
        self.status['plc_cycle']['product_identity_reason'] = 'PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN'
        with self.assertRaisesRegex(ValueError, 'PRODUCT_CONTEXT'):
            validate_ready(self.status, self.view)

    def test_request_or_motion_or_outputs_prevent_reboot(self):
        for key in ('Inspection_Request', 'Mc_Run'):
            s = copy.deepcopy(self.status)
            s['plc']['snapshot']['controls'][key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_ready(s, self.view)
        self.status['plc']['snapshot']['raw100'] = '01000100'
        with self.assertRaises(ValueError): validate_ready(self.status, self.view)

    def test_unfinished_storage_health_and_missing_fields_rejected(self):
        for group, key, value in [('inspection_service', 'storage_pending', True),
                ('assembly_component', 'outstanding', 1), ('inspection_service', 'worker_alive', False)]:
            s = copy.deepcopy(self.status); s[group][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_ready(s, self.view)
        del self.status['plc_cycle']['product_identity_reason']
        with self.assertRaises(ValueError): validate_ready(self.status, self.view)

    def test_ui_hold_and_stale_preview_are_not_ready(self):
        for view in [dict(phase='HOLD', camera=dict(fresh=True)),
                     dict(phase='WAIT_START', camera=dict(fresh=False))]:
            with self.subTest(view=view), self.assertRaises(ValueError):
                validate_ready(self.status, view)
