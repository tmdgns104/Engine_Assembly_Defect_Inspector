"""Explicit seven-tag contract; no motion/pusher output is addressable here.

The PLC must implement the matching latched request and watchdog contract before
this version is selected. A successful CIP write/readback is transport evidence,
not proof that the PLC sequence consumed the result or that a motor stopped.
"""
import struct
import time
import uuid

from src.control.omron_cip import CipError, OmronCipGateway
from src.control.production_plc import IoResult, RequestHandshake, decision_bit

CONTRACT_VERSION = 'EXTENDED_V2'
RESULT_CODES = {'PASS': 1, 'FAIL': 2, 'REVIEW': 3, 'ERROR': 4}
BOOL_TAGS = frozenset(('Inspection_Request', 'Jetson_Result', 'Jetson_Done',
                       'Jetson_Ready', 'Jetson_Busy', 'Jetson_Heartbeat'))
UINT_TAG = 'Jetson_ResultCode'


class OmronCipV2Gateway(OmronCipGateway):
    """Bounded typed access, with a read-only schema probe before any write."""
    contract_version = CONTRACT_VERSION
    _ALLOWED_READS = BOOL_TAGS
    _ALLOWED_WRITES = BOOL_TAGS - {'Inspection_Request'}
    _UINT_TYPE = 0x00C7  # OMRON W506, CIP service data types, section 7-4.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract_verified = False
        self.write_blocked = False
        self.probe_error = None

    def _read_code(self):
        if self.socket is None:
            self._connect()
        data = self._message(0x4C, UINT_TAG, struct.pack('<H', 1))
        if len(data) != 4:
            raise CipError('UINT_REPLY_LENGTH_INVALID')
        kind, value = struct.unpack('<HH', data)
        if kind != self._UINT_TYPE or value not in range(5):
            raise CipError('RESULT_CODE_TYPE_OR_VALUE_INVALID')
        self.last[UINT_TAG] = value
        return value

    def probe_contract(self):
        """Read all seven tags. Never creates tags, changes PLC mode, or writes.

        Calling this after an uncertain write is an explicit recovery operation;
        the handshake never automatically probes again after RESYNC_REQUIRED.
        """
        self.contract_verified = False
        try:
            values = {tag: self._read_bool(tag) for tag in sorted(BOOL_TAGS)}
            values[UINT_TAG] = self._read_code()
            if self._read_bool('Inspection_Request') != values['Inspection_Request']:
                raise CipError('REQUEST_CHANGED_DURING_PROBE')
        except Exception as error:
            self.probe_error = f'{type(error).__name__}:{error}'
            self.close()
            raise
        self.contract_verified = True
        self.write_blocked = False
        self.probe_error = None
        return values

    def write(self, tag, value):
        if tag == UINT_TAG:
            if type(value) is not int or value not in range(5):
                raise ValueError('RESULT_CODE_REQUIRED')
            kind = self._UINT_TYPE
        elif tag in self._ALLOWED_WRITES:
            if type(value) is not bool:
                raise ValueError('BOOL_REQUIRED')
            kind = self._BOOL_TYPE
        else:
            raise ValueError('WRITE_TAG_NOT_ALLOWED')
        if not self.contract_verified or self.write_blocked or self.socket is None:
            raise ValueError('VERIFIED_V2_CONTRACT_REQUIRED')
        try:
            reply = self._message(0x4D, tag, struct.pack('<HHH', kind, 1, int(value)))
            if reply:
                raise CipError('WRITE_REPLY_DATA_UNEXPECTED')
            observed = self._read_code() if tag == UINT_TAG else self._read_bool(tag)
            if type(observed) is not type(value) or observed != value:
                raise CipError('WRITE_READBACK_MISMATCH')
            return IoResult('ACK', value)
        except Exception as error:
            # A lost ACK may already have changed the PLC. Block even a different
            # output until explicit recovery; never send Done after partial data.
            self.write_blocked = True
            self.close()
            return IoResult('UNKNOWN', error=f'{type(error).__name__}:{error}')

    def _write_bool(self, tag, value):
        return self.write(tag, value)

    def health(self):
        value = super().health()
        value.update(contract_version=self.contract_version,
                     contract_schema_verified=self.contract_verified,
                     contract_confirmed=False, write_blocked=self.write_blocked,
                     contract_probe_error=self.probe_error,
                     hardware_status='EXTENDED_TAG_ACCESS_NOT_PHYSICAL_FEEDBACK')
        return value

    def close(self):
        self.contract_verified = False
        super().close()


class ExtendedRequestHandshake(RequestHandshake):
    """Single writer, serial four-phase handshake with explicit outcome codes.

    Runtime calls service_tick under its existing lock. No timer thread can race
    result publication. Readiness is an admission condition, not a motor command.
    A fault stops heartbeat writes; the PLC watchdog must HOLD independently.
    """
    def __init__(self, gateway, event, *, clear_timeout=20, heartbeat_period=1.0):
        super().__init__(gateway, event, clear_timeout=clear_timeout)
        if heartbeat_period <= 0:
            raise ValueError('POSITIVE_HEARTBEAT_PERIOD_REQUIRED')
        self.outputs = {}
        self.initialized = False
        self.heartbeat_period = heartbeat_period
        self.last_heartbeat_at = None
        self.next_probe_at = 0

    def _write(self, tag, value):
        # An intent must be durable before an external effect is attempted.
        self.record('PLC_WRITE_INTENT', tag=tag, value=value, contract_version=CONTRACT_VERSION)
        reply = self.gateway.write(tag, value)
        self.record('PLC_WRITE_RECEIPT', tag=tag, value=value, status=reply.status, error=reply.error)
        if reply.status != 'ACK' or type(reply.value) is not type(value) or reply.value != value:
            self.fault(tag.upper() + '_WRITE_UNCONFIRMED',
                       reply.status if reply.status in ('FAILED', 'UNKNOWN') else 'UNKNOWN')
            return False
        self.outputs[tag] = value
        return True

    def _changed(self, tag, value):
        return self.outputs.get(tag) == value or self._write(tag, value)

    def service_tick(self, now, *, ready):
        if self.state == 'RESYNC_REQUIRED':
            return
        if not self.initialized:
            if now < self.next_probe_at:
                return
            self.next_probe_at = now + 1
            try:
                observed = self.gateway.probe_contract()
            except Exception as error:
                self.reason = f'CONTRACT_PROBE_FAILED:{type(error).__name__}:{error}'
                return
            self.outputs = {k: v for k, v in observed.items() if k != 'Inspection_Request'}
            if any(observed[tag] for tag in ('Inspection_Request', 'Jetson_Done', 'Jetson_Busy')):
                self.fault('RESTART_WITH_UNSETTLED_PLC_STATE')
                return
            self.initialized = True
            self.state = 'ARMED'
            self.request = False
            self.reason = None
            if not self._changed('Jetson_Ready', False):
                return
            self.record('PLC_V2_SCHEMA_VERIFIED', contract_version=CONTRACT_VERSION)
        # Poll before changing Ready, so a request issued while the previous
        # Ready was high is not rejected just because its product entered view.
        self.poll(now)
        if self.state == 'RESYNC_REQUIRED':
            return
        can_accept = bool(ready and self.state == 'ARMED' and self.token is None)
        if not self._changed('Jetson_Ready', can_accept):
            return
        if self.last_heartbeat_at is None or now - self.last_heartbeat_at >= self.heartbeat_period:
            if self._write('Jetson_Heartbeat', not self.outputs['Jetson_Heartbeat']):
                self.last_heartbeat_at = now

    def poll(self, now):
        if not self.initialized or self.state == 'RESYNC_REQUIRED':
            return
        read = self.gateway.read_request()
        if read.status != 'ACK' or type(read.value) is not bool:
            self.fault('REQUEST_READ_FAILED')
            return
        previous, self.request = self.request, read.value
        if self.state == 'ARMED' and read.value:
            if previous is not False or self.outputs.get('Jetson_Ready') is not True:
                self.fault('REQUEST_WHILE_NOT_READY')
                return
            self.token = uuid.uuid4().hex
            self.accepted_at = now
            self.early_off = False
            self.inspection_id = None
            self.publication = 'NOT_STARTED'
            self.reason = None
            self.state = 'REQUEST_LATCHED'
            self.record('PLC_REQUEST_LATCHED')
            if not self._write('Jetson_Ready', False):
                return
            if not self._write('Jetson_Busy', True):
                return
            self._write(UINT_TAG, 0)
        elif self.state in ('REQUEST_LATCHED', 'INSPECTING') and not read.value:
            self.early_off = True
            self.fault('PLC_HANDSHAKE_CONTRACT_REQUIRED', 'BLOCKED')
        elif self.state == 'WAIT_REQUEST_OFF':
            if not read.value:
                if not self._write('Jetson_Done', False):
                    return
                if not self._write('Jetson_Busy', False):
                    return
                self.record('PLC_REQUEST_RELEASE_ACK', product_clearance=False, result_retained=True)
                self.state = 'ARMED'
                self.token = None
                self.inspection_id = None
            elif now - self.published_at > self.clear_timeout:
                self.fault('REQUEST_CLEAR_TIMEOUT')

    def publish(self, inspection_id, decision, durable, now):
        if durable is not True:
            raise ValueError('DURABLE_RESULT_REQUIRED')
        if inspection_id != self.inspection_id or not self.token:
            raise ValueError('PUBLICATION_IDENTITY_MISMATCH')
        code = RESULT_CODES[decision]  # Unknown decisions fail before any output.
        if self.state != 'INSPECTING':
            return
        self.poll(now)
        if self.state != 'INSPECTING':
            return
        self.record('PLC_DURABLE_RESULT_VERIFIED', vision_decision=decision, result_code=code)
        for tag, value in ((UINT_TAG, code), ('Jetson_Result', decision_bit(decision)),
                           ('Jetson_Done', True)):
            # The PLC must hold Request through every data write. A mid-sequence
            # release blocks Done and preserves the partial-write evidence.
            self.poll(now)
            if self.state != 'INSPECTING' or not self._write(tag, value):
                return
        self.publication = 'ACKNOWLEDGED'
        self.state = 'WAIT_REQUEST_OFF'
        self.published_at = now
        self.record('PLC_DONE_ACK', value=True, vision_decision=decision, result_code=code)

    def resync(self):
        if self.state == 'INSPECTING':
            raise ValueError('INSPECTION_RUNNING')
        observed = self.gateway.probe_contract()
        if observed['Inspection_Request'] is not False:
            raise ValueError('VALID_REQUEST_LOW_REQUIRED')
        self.outputs = {k: v for k, v in observed.items() if k != 'Inspection_Request'}
        for tag, value in (('Jetson_Ready', False), ('Jetson_Done', False),
                           ('Jetson_Busy', False), (UINT_TAG, 0)):
            if not self._write(tag, value):
                raise ValueError('V2_RESET_UNCONFIRMED')
        self.token = self.inspection_id = None
        self.early_off = False
        self.state = 'ARMED'
        self.request = False
        self.reason = None
        self.publication = 'NOT_STARTED'
        self.initialized = True
        self.record('PLC_EXPLICIT_RESYNC', result_retained=True, product_clearance=False)

    def shutdown(self):
        # This is a normal admission stop, not equipment safety or a cycle reset.
        if self.initialized and self.state != 'RESYNC_REQUIRED':
            self._changed('Jetson_Ready', False)

    def status(self):
        return dict(super().status(), contract_version=CONTRACT_VERSION,
                    output_readbacks=dict(self.outputs),
                    plc_consumption='REQUEST_RELEASE_OBSERVED' if self.publication == 'ACKNOWLEDGED'
                    and self.state == 'ARMED' else 'NOT_CONFIRMED',
                    heartbeat_period_s=self.heartbeat_period)
