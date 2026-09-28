"""Bounded EtherNet/IP explicit-message access to the three bench PLC BOOL tags.

The gateway never retries a write whose outcome is uncertain. The runtime's
RequestHandshake owns the cycle and requires an explicit low-state resync.
"""
import socket
import struct

from src.control.production_plc import IoResult


class CipError(Exception):
    pass


class OmronCipGateway:
    backend = 'OMRON_CIP_BENCH'
    _BOOL_TYPE = 0x00C1
    _ALLOWED_READS = frozenset(('Inspection_Request', 'Jetson_Result', 'Jetson_Done'))
    _ALLOWED_WRITES = frozenset(('Jetson_Result', 'Jetson_Done'))

    def __init__(self, host, source_ip, *, timeout=1.5):
        self.host = host
        self.source_ip = source_ip
        self.timeout = timeout
        self.socket = None
        self.session = 0
        self.counter = 0
        self.last = {}
        self._connect()

    def _connect(self):
        connection = socket.create_connection((self.host, 44818), self.timeout,
                                              source_address=(self.source_ip, 0))
        connection.settimeout(self.timeout)
        self.socket = connection
        try:
            session, reply = self._exchange(0x65, struct.pack('<HH', 1, 0), session=0)
            if not session or len(reply) != 4 or reply != struct.pack('<HH', 1, 0):
                raise CipError('REGISTER_SESSION_INVALID')
            self.session = session
        except Exception:
            self.close()
            raise

    def _receive(self, count):
        data = bytearray()
        while len(data) < count:
            block = self.socket.recv(count - len(data))
            if not block:
                raise CipError('CONNECTION_CLOSED')
            data.extend(block)
        return bytes(data)

    def _exchange(self, command, payload, *, session=None):
        if self.socket is None:
            raise CipError('NOT_CONNECTED')
        self.counter += 1
        context = struct.pack('<Q', self.counter)
        active_session = self.session if session is None else session
        header = struct.pack('<HHII8sI', command, len(payload), active_session, 0, context, 0)
        self.socket.sendall(header + payload)
        response = self._receive(24)
        actual_command, size, actual_session, status, actual_context, options = struct.unpack(
            '<HHII8sI', response)
        if size > 4096:
            raise CipError('RESPONSE_TOO_LARGE')
        body = self._receive(size)
        if (actual_command != command or actual_context != context or status != 0 or options != 0
                or (command != 0x65 and actual_session != active_session)):
            raise CipError(f'ENCAPSULATION_RESPONSE_INVALID:{status:#x}')
        return actual_session, body

    @staticmethod
    def _path(tag):
        encoded = tag.encode('ascii')
        return bytes((0x91, len(encoded))) + encoded + (b'\x00' if len(encoded) & 1 else b'')

    def _message(self, service, tag, data=b''):
        path = self._path(tag)
        request = bytes((service, len(path) // 2)) + path + data
        rr_data = struct.pack('<IHHHHHH', 0, 0, 2, 0, 0, 0x00B2, len(request)) + request
        _, response = self._exchange(0x6F, rr_data)
        if len(response) < 16:
            raise CipError('SHORT_RR_RESPONSE')
        interface, timeout, count = struct.unpack_from('<IHH', response)
        if interface != 0 or count != 2:
            raise CipError('RR_RESPONSE_ITEMS_INVALID')
        offset = 8
        items = []
        for _ in range(count):
            if len(response) < offset + 4:
                raise CipError('TRUNCATED_ITEM_HEADER')
            item_type, length = struct.unpack_from('<HH', response, offset)
            offset += 4
            if len(response) < offset + length:
                raise CipError('TRUNCATED_ITEM')
            items.append((item_type, response[offset:offset + length]))
            offset += length
        if offset != len(response) or items[0] != (0, b'') or items[1][0] != 0x00B2:
            raise CipError('RR_ITEM_TYPE_INVALID')
        cip = items[1][1]
        if len(cip) < 4 or cip[0] != service | 0x80:
            raise CipError('CIP_REPLY_INVALID')
        extra_words = cip[3]
        if len(cip) < 4 + 2 * extra_words:
            raise CipError('CIP_EXTENDED_STATUS_TRUNCATED')
        if cip[2] != 0:
            raise CipError(f'CIP_STATUS:{cip[2]:#x}')
        return cip[4 + 2 * extra_words:]

    def _read_bool(self, tag):
        if tag not in self._ALLOWED_READS:
            raise ValueError('READ_TAG_NOT_ALLOWED')
        data = self._message(0x4C, tag, struct.pack('<H', 1))
        if len(data) != 4:
            raise CipError('BOOL_REPLY_LENGTH_INVALID')
        data_type, raw = struct.unpack('<HH', data)
        if data_type != self._BOOL_TYPE or raw not in (0, 1):
            raise CipError('BOOL_REPLY_VALUE_INVALID')
        value = bool(raw)
        self.last[tag] = value
        return value

    def read_request(self):
        try:
            return IoResult('ACK', self._read_bool('Inspection_Request'))
        except Exception as error:
            return IoResult('FAILED', error=type(error).__name__ + ':' + str(error))

    def _write_bool(self, tag, value):
        if tag not in self._ALLOWED_WRITES:
            raise ValueError('WRITE_TAG_NOT_ALLOWED')
        if type(value) is not bool:
            raise ValueError('BOOL_REQUIRED')
        try:
            data = struct.pack('<HHH', self._BOOL_TYPE, 1, int(value))
            response = self._message(0x4D, tag, data)
            if response:
                raise CipError('WRITE_REPLY_DATA_UNEXPECTED')
            observed = self._read_bool(tag)
            if observed is not value:
                raise CipError('WRITE_READBACK_MISMATCH')
            return IoResult('ACK', value)
        except Exception as error:
            # A partial send, missing acknowledgement, or readback mismatch may
            # have changed the PLC. Never retry it as if the write did not occur.
            return IoResult('UNKNOWN', error=type(error).__name__ + ':' + str(error))

    def write_result(self, value):
        return self._write_bool('Jetson_Result', value)

    def write_done(self, value):
        return self._write_bool('Jetson_Done', value)

    def health(self):
        request = self.read_request()
        return dict(backend=self.backend, available=request.status == 'ACK',
                    network_plc_writes_enabled=True, physical_output_enabled=False,
                    host=self.host, Inspection_Request=request.value if request.status == 'ACK' else None,
                    last_values=dict(self.last), result_true_means='NG',
                    contract_confirmed=False, hardware_status='BENCH_TAG_ACCESS_ONLY')

    def close(self):
        connection, self.socket = self.socket, None
        if connection is not None:
            try:
                connection.close()
            finally:
                self.session = 0
