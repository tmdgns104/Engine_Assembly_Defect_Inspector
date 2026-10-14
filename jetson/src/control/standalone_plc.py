"""Versioned serial line handshake. This module cannot write motor or pusher I/O.

The matching PLC program owns motion, physical buttons, sensor edge counting,
cycle identifiers and result consumption. A CIP acknowledgement alone is not
PLC consumption: matching PLC_AckCycleId and Request OFF are both required.
"""
import struct
import uuid

from src.control.omron_cip import OmronCipGateway, CipError
from src.control.production_plc import IoResult, RequestHandshake
from src.control.plc_v2 import RESULT_CODES

VERSION = 'STANDALONE_V3'
TAGS = {
    'PLC_ContractVersion': ('UINT', 'PLC'),
    **{name: ('BOOL', 'PLC') for name in (
        'Inspection_Request', 'PLC_RunPermit', 'PhotoSensor', 'PLC_ConveyorRun',
        'PLC_NoPusherMode', 'Pusher_Forward', 'Pusher_Back')},
    **{name: ('UDINT', 'PLC') for name in (
        'PLC_CycleId', 'PLC_AckCycleId', 'PLC_SessionEcho', 'PLC_SensorRiseCount')},
    **{name: ('BOOL', 'JETSON') for name in (
        'Jetson_Result', 'Jetson_Done', 'Jetson_Ready', 'Jetson_Busy',
        'Jetson_Heartbeat', 'Jetson_InPosition', 'Jetson_ProductClear')},
    'Jetson_ResultCode': ('UINT', 'JETSON'),
    'Jetson_SessionId': ('UDINT', 'JETSON'),
    'Jetson_ResultCycleId': ('UDINT', 'JETSON'),
}
WIRE = {'BOOL': (0xC1, 'H', 2), 'UINT': (0xC7, 'H', 2), 'UDINT': (0xC8, 'I', 4)}


class LineGateway(OmronCipGateway):
    contract_version = VERSION
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verified = False
        self.write_blocked = False
        self.probe_error = None

    def read_tag(self, name):
        kind = TAGS[name][0]
        code, fmt, size = WIRE[kind]
        if self.socket is None: self._connect()
        raw = self._message(0x4C, name, struct.pack('<H', 1))
        if len(raw) != size + 2 or struct.unpack('<H', raw[:2])[0] != code:
            raise CipError('LINE_TAG_TYPE_MISMATCH:' + name)
        value = struct.unpack('<' + fmt, raw[2:])[0]
        if kind == 'BOOL':
            if value not in (0, 1): raise CipError('LINE_BOOL_INVALID:' + name)
            value = bool(value)
        if name == 'Jetson_ResultCode' and value not in range(5):
            raise CipError('LINE_RESULT_CODE_INVALID')
        self.last[name] = value
        return value

    def read_inputs(self):
        # Detect a cycle boundary in the middle of the multi-tag read.
        first = self.read_tag('PLC_CycleId')
        values = {k: self.read_tag(k) for k, (_, owner) in TAGS.items() if owner == 'PLC'}
        if values['PLC_CycleId'] != first:
            raise CipError('PLC_CYCLE_CHANGED_DURING_READ')
        if values['PLC_ContractVersion'] != 3:
            raise CipError('PLC_PROGRAM_VERSION_CHANGED')
        return values

    def probe_contract(self):
        self.verified = False
        try:
            result = {k: self.read_tag(k) for k in TAGS}
            if result['PLC_ContractVersion'] != 3:
                raise CipError('PLC_V3_PROGRAM_NOT_ACTIVE')
        except Exception as error:
            self.probe_error = str(error)
            self.close()
            raise
        self.verified, self.write_blocked, self.probe_error = True, False, None
        return result

    def write(self, name, value):
        if name not in TAGS or TAGS[name][1] != 'JETSON':
            raise ValueError('WRITE_TAG_NOT_ALLOWED')
        kind = TAGS[name][0]
        maximum = 0xFFFF if kind == 'UINT' else 0xFFFFFFFF
        if ((kind == 'BOOL' and type(value) is not bool) or
                (kind != 'BOOL' and (type(value) is not int or not 0 <= value <= maximum))):
            raise ValueError('LINE_VALUE_TYPE_OR_RANGE_INVALID')
        if name == 'Jetson_ResultCode' and value not in range(5):
            raise ValueError('LINE_RESULT_CODE_INVALID')
        if not self.verified or self.write_blocked or self.socket is None:
            raise ValueError('VERIFIED_STANDALONE_SCHEMA_REQUIRED')
        code, fmt, _ = WIRE[kind]
        try:
            reply = self._message(0x4D, name, struct.pack('<HH', code, 1) + struct.pack('<'+fmt, int(value)))
            if reply or self.read_tag(name) != value: raise CipError('WRITE_READBACK_MISMATCH')
            return IoResult('ACK', value)
        except Exception as error:
            self.write_blocked = True
            self.close()
            return IoResult('UNKNOWN', error=str(error))

    def read_request(self):
        try: return IoResult('ACK', self.read_tag('Inspection_Request'))
        except Exception as error: return IoResult('FAILED', error=str(error))

    def health(self):
        return dict(super().health(), available=bool(self.verified and self.socket),
                    Inspection_Request=self.last.get('Inspection_Request'), contract_version=VERSION,
                    contract_schema_verified=self.verified, write_blocked=self.write_blocked,
                    contract_probe_error=self.probe_error, hardware_status='NO_PUSHER_LINE_TAGS',
                    contract_confirmed=self.verified)

    def close(self):
        self.verified = False
        super().close()


class LineHandshake(RequestHandshake):
    """One PLC writer called by the runtime loop, never by the classifier worker."""
    def __init__(self, gateway, event, *, session_id, clear_timeout=20):
        super().__init__(gateway, event, clear_timeout=clear_timeout)
        if type(session_id) is not int or not 0 < session_id < 2**32:
            raise ValueError('PERSISTENT_NEW_SESSION_ID_REQUIRED')
        self.session_id = session_id
        self.initialized = False
        self.session_sent = False
        self.outputs, self.inputs = {}, {}
        self.next_probe_at = 0
        self.last_heartbeat_at = None
        self.cycle_id = None
        self.last_cycle_id = 0
        self.consumed_cycle_id = None
        self.cancelled = False
        self.last_request_value = None

    def _write(self, name, value):
        self.record('PLC_WRITE_INTENT', tag=name, value=value, contract_version=VERSION,
                    line_cycle_id=self.cycle_id, line_session_id=self.session_id)
        reply = self.gateway.write(name, value)
        self.record('PLC_WRITE_RECEIPT', tag=name, value=value, status=reply.status, error=reply.error)
        if reply.status != 'ACK' or type(reply.value) is not type(value) or reply.value != value:
            self.fault('UNCONFIRMED_WRITE:' + name, 'UNKNOWN')
            return False
        self.outputs[name] = value
        return True

    def _changed(self, name, value):
        return self.outputs.get(name) == value or self._write(name, value)

    def _inputs(self):
        try:
            values = self.gateway.read_inputs()
        except Exception as error:
            self.fault('PLC_INPUT_UNAVAILABLE:' + str(error))
            return False
        old_sensor = self.inputs.get('PLC_SensorRiseCount')
        self.inputs = values
        self.request = values['Inspection_Request']
        if old_sensor is not None and old_sensor != values['PLC_SensorRiseCount']:
            self.record('PLC_SENSOR_COUNTER', count=values['PLC_SensorRiseCount'],
                        sensor=values['PhotoSensor'], line_cycle_id=values['PLC_CycleId'])
        return True

    def service_tick(self, now, *, ready, product_clear=False):
        if self.state == 'RESYNC_REQUIRED': return
        if not self.session_sent:
            if now < self.next_probe_at: return
            self.next_probe_at = now + 2
            try: values = self.gateway.probe_contract()
            except Exception as error:
                self.reason = 'WAIT_PLC_SCHEMA:' + str(error)
                return
            self.outputs = {k: v for k, v in values.items() if TAGS[k][1] == 'JETSON'}
            self.last_cycle_id = values['PLC_CycleId']
            # Publish the new session first. Do not clear an old Done before
            # the PLC has stopped its old cycle and acknowledged that session.
            if not self._write('Jetson_SessionId', self.session_id): return
            self.session_sent = True
        if not self._inputs(): return
        if self.inputs['PLC_SessionEcho'] != self.session_id:
            self.reason = 'WAIT_PLC_SESSION_ACK'
            return
        if not self.initialized:
            if self.inputs['PLC_RunPermit'] or self.request:
                self.reason = 'WAIT_NEW_LOCAL_START_BASELINE'
                return
            for tag, value in [('Jetson_Ready', False), ('Jetson_Done', False),
                               ('Jetson_Busy', False), ('Jetson_InPosition', False),
                               ('Jetson_ProductClear', False), ('Jetson_ResultCycleId', 0),
                               ('Jetson_ResultCode', 0)]:
                if not self._changed(tag, value): return
            self.initialized, self.state, self.reason = True, 'ARMED', None
        if (not self.inputs['PLC_NoPusherMode'] or self.inputs['Pusher_Forward'] or self.inputs['Pusher_Back']):
            self._changed('Jetson_Ready', False)
            self.fault('PUSHER_MODE_OR_OUTPUT_NOT_EXCLUDED')
            return
        if self.token and not self.inputs['PLC_RunPermit']:
            self.cancelled = True
            self.record('PLC_STOP_CANCELLED_CYCLE', line_cycle_id=self.cycle_id)
            for tag in ('Jetson_Done', 'Jetson_Busy', 'Jetson_InPosition'):
                if not self._changed(tag, False): return
            self.fault('LOCAL_STOP_CANCELLED_CYCLE', 'BLOCKED')
            return
        if self.token and self.inputs['PLC_CycleId'] != self.cycle_id:
            self.fault('PLC_CHANGED_ACTIVE_CYCLE', 'BLOCKED')
            return
        if self.token and self.last_request_value != self.request:
            self.record('SAME_PRODUCT_REQUEST_EDGE', value=self.request, line_cycle_id=self.cycle_id)
        self.last_request_value = self.request
        if self.state == 'ARMED' and self.request:
            if (not self.outputs.get('Jetson_Ready') or not self.inputs['PLC_RunPermit']
                    or self.inputs['PLC_CycleId'] != self.last_cycle_id + 1):
                self.fault('STALE_OR_UNREADY_REQUEST', 'BLOCKED')
                return
            self.cycle_id = self.inputs['PLC_CycleId']
            self.last_cycle_id = self.cycle_id
            self.token, self.accepted_at = uuid.uuid4().hex, now
            self.inspection_id, self.publication, self.cancelled = None, 'NOT_STARTED', False
            self.state = 'REQUEST_LATCHED'
            self.record('PLC_REQUEST_LATCHED', line_cycle_id=self.cycle_id, line_session_id=self.session_id)
            for tag, value in [('Jetson_Ready', False), ('Jetson_ResultCode', 0), ('Jetson_Busy', True)]:
                if not self._changed(tag, value): return
        elif self.state == 'WAIT_REQUEST_OFF':
            if not self.request and self.inputs['PLC_AckCycleId'] == self.cycle_id:
                for tag in ('Jetson_Done', 'Jetson_Busy', 'Jetson_InPosition'):
                    if not self._changed(tag, False): return
                self.consumed_cycle_id = self.cycle_id
                self.record('PLC_CYCLE_CONSUMED', line_cycle_id=self.cycle_id, result_retained=True)
                self.token = self.inspection_id = None
                self.state = 'ARMED'
            elif now - self.published_at > self.clear_timeout:
                self.fault('PLC_CONSUMPTION_TIMEOUT')
                return
        if not self._changed('Jetson_ProductClear', bool(product_clear)): return
        can_accept = bool(ready and product_clear and self.state == 'ARMED' and self.token is None)
        if not self._changed('Jetson_Ready', can_accept): return
        if self.last_heartbeat_at is None or now - self.last_heartbeat_at >= 1:
            if self._write('Jetson_Heartbeat', not self.outputs.get('Jetson_Heartbeat', False)):
                self.last_heartbeat_at = now

    def poll(self, now):
        # Request edge ownership stays in service_tick; no second writer thread.
        return

    def in_position(self):
        if self.token and self.state in ('REQUEST_LATCHED', 'INSPECTING'):
            return self._changed('Jetson_InPosition', True)
        return False

    def publish(self, inspection_id, decision, durable, now):
        if self.state != 'INSPECTING' or self.cancelled: return
        if not durable or inspection_id != self.inspection_id:
            raise ValueError('DURABLE_SAME_CYCLE_RESULT_REQUIRED')
        code = RESULT_CODES[decision]
        for tag, value in [('Jetson_ResultCycleId', self.cycle_id), ('Jetson_ResultCode', code),
                           ('Jetson_Result', decision != 'PASS'), ('Jetson_Done', True)]:
            if not self._inputs(): return
            if (not self.inputs['PLC_RunPermit'] or not self.request
                    or self.inputs['PLC_CycleId'] != self.cycle_id
                    or self.inputs['PLC_SessionEcho'] != self.session_id
                    or not self.inputs['PLC_NoPusherMode']
                    or self.inputs['Pusher_Forward'] or self.inputs['Pusher_Back']):
                self.cancelled = True
                self.fault('PUBLICATION_CONTEXT_CANCELLED', 'BLOCKED')
                return
            if not self._write(tag, value): return
        self.state, self.publication, self.published_at = 'WAIT_REQUEST_OFF', 'ACKNOWLEDGED', now
        self.record('PLC_DONE_ACK', vision_decision=decision, line_cycle_id=self.cycle_id)

    def shutdown(self):
        if self.session_sent and self.state != 'RESYNC_REQUIRED':
            self._changed('Jetson_Ready', False)

    def status(self):
        return dict(super().status(), contract_version=VERSION, inputs=dict(self.inputs),
                    output_readbacks=dict(self.outputs), line_session_id=self.session_id,
                    line_cycle_id=self.cycle_id, plc_consumed_cycle_id=self.consumed_cycle_id,
                    motor_feedback='NOT_AVAILABLE_COMMAND_ONLY', cancelled=self.cancelled)
