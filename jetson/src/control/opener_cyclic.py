"""Local IPC client for the sole cyclic publisher. Never opens a PLC socket.

The IO thread only exchanges atomic snapshots. Inference and SQLite stay on
their existing owners. A live IO thread cannot conceal a stalled runtime:
ready/clear permission expires unless the runtime renews its health lease.
"""
from src import config as parameters
import os
from pathlib import Path
import socket
import struct
import threading
import time
import uuid
from src.runtime.health_diagnostics import HealthDiagnostics

CONTRACT = 'OPENER_CYCLIC'
PHASES = ('WAIT_CONNECTION','SYNC_LOW','IDLE','REQUEST_RECEIVED','TEST_RESULT_READY',
          'RESULT_SENT','DONE_SENT','WAIT_REQUEST_OFF','CLEARING_DONE','READY_NEXT','DISARMED')
DECISIONS = {'PASS':1, 'FAIL':2, 'REVIEW':3, 'ERROR':4}
PLC_RESULT_POLICY = 'PASS_OK_OTHER_NG_V1'

def decode_snapshot(data, now):
    if len(data)!=160 or data[:8]!=b'EAI1\x03\x00\x01\x00':
        raise ValueError('IPC_SCHEMA_INVALID')
    boot, connection, request, generated, received, accepted = struct.unpack_from('<QIIddd', data,8)
    flags, phase, results, done, complete, ack, rejected = struct.unpack_from('<7I',data,48)
    if not boot or phase>=len(PHASES) or not 0<=now-generated<=parameters.IPC_SNAPSHOT_MAX_AGE_SECONDS:
        raise ValueError('IPC_STALE_OR_INVALID_SNAPSHOT')
    return dict(boot=boot, connection=connection, request_id=request, generated=generated,
        received=received, accepted_at=accepted, connected=bool(flags&1), run_idle=bool(flags&2),
        bool_valid=bool(flags&4), fresh=bool(flags&8),
        controls={k:bool(flags&(1<<(8+i))) for i,k in enumerate(
            ('Inspection_Request','EStop_OK','Mc_Run','Stop_PB'))},
        transaction_settled=bool(flags&(1<<16)),
        phase=PHASES[phase], result_count=results, done_count=done, completed_count=complete,
        result_ack=ack, rejected=rejected, raw100=data[76:80].hex(),
        approval_id=data[128:160].rstrip(b'\0').decode('ascii'),
        reason=data[80:128].split(b'\0')[0].decode('ascii',errors='replace'))

def command(snapshot, session, op, *, flags=0, identifier='', decision=0, now=None, approval_id=''):
    if len(session)!=32 or (identifier and len(identifier)!=32):
        raise ValueError('IPC_IDENTITY_LENGTH')
    b=bytearray(160); b[:8]=b'EAI1\x03\x00\x02\x00'
    struct.pack_into('<QIId',b,8,snapshot['boot'],snapshot['connection'],snapshot['request_id'],
                     time.monotonic() if now is None else now)
    b[32:64]=session.encode('ascii'); b[64:96]=identifier.encode('ascii').ljust(32,b'\0')
    struct.pack_into('<III',b,96,decision,flags,op)
    if approval_id and (len(approval_id)!=32 or any(c not in '0123456789abcdef' for c in approval_id)):
        raise ValueError('IPC_APPROVAL_ID_INVALID')
    b[128:160]=approval_id.encode('ascii').ljust(32,b'\0')
    return bytes(b)

class OpenerGateway:
    backend = contract_version = CONTRACT
    def __init__(self, path, *, writes_enabled=False):
        self.path=str(path); self.writes_enabled=writes_enabled is True
        self.runtime_session=uuid.uuid4().hex
        self.lock=threading.Lock(); self.stop=threading.Event()
        self.snapshot=None; self.error='WAIT_OPENER_IPC'; self.pending=None
        self.health=(False,False,0); self.sent=set(); self.initial_pending=None
        self.initial_error=None
        self.diagnostics = HealthDiagnostics()
        self.ready_reason = 'NOT_RENEWED'
        self.thread=threading.Thread(target=self._run,name='opener-ipc',daemon=True)
        self.thread.start()

    def initial_arm(self, snapshot, approval_id):
        with self.lock:
            if not self.writes_enabled or self.initial_pending:
                raise ValueError('INITIAL_PERMISSION_NOT_ENABLED_OR_PENDING')
            self.initial_pending=(snapshot['boot'],snapshot['connection'],approval_id,time.monotonic())

    def health_update(self, ready, clear, now):
        with self.lock:
            previous = self.health[2]
            changed = self.health[0] != bool(ready)
            self.health=(bool(ready),bool(clear),now)
            if hasattr(self, 'diagnostics'):
                self.diagnostics.record('HEALTH_UPDATE', retain=changed or now-previous>.2,
                    ready=bool(ready), reason=self.ready_reason,
                    interval_ms=(now-previous)*1000 if previous else None, last_valid_update=now)

    def supervised_arm(self, snapshot, approval_id):
        with self.lock:
            if not self.writes_enabled or self.initial_pending or self.pending:
                raise ValueError('SUPERVISED_PERMISSION_NOT_ENABLED_OR_PENDING')
            self.initial_pending=(snapshot['boot'],snapshot['connection'],approval_id,time.monotonic(),5)

    def read_snapshot(self, now):
        with self.lock:
            # The IO thread can publish after the caller sampled its loop time.
            # Measure age against the clock at the atomic read, never that older
            # loop timestamp. Future/stale wire timestamps remain invalid.
            observed = time.monotonic()
            if self.snapshot and 0<=observed-self.snapshot['generated']<=.5:
                return dict(self.snapshot, observed_at=observed)
        return None

    def result(self, snapshot, identifier, decision):
        if decision not in DECISIONS: raise ValueError('UNKNOWN_AI_RESULT')
        key=(snapshot['boot'],snapshot['connection'],snapshot['request_id'])
        with self.lock:
            if key in self.sent or self.pending is not None:
                raise ValueError('DUPLICATE_RESULT_PUBLICATION')
            if not self.writes_enabled: raise ValueError('CYCLIC_PUBLICATION_NOT_APPROVED')
            self.pending=(key,identifier,decision,time.monotonic())

    def cancel(self):
        with self.lock:
            self.pending=None
            self.initial_pending=None
            self.health=(False,False,time.monotonic())

    def _diagnose(self, name, **values):
        # Older software-only fixtures construct the owner without its thread.
        if hasattr(self, 'diagnostics'):
            self.diagnostics.record(name, **values)

    def _run(self):
        while not self.stop.is_set():
            try:
                self._connected_loop()
            except (OSError,ValueError) as error:
                # Preserve the first local cause even after the next connection
                # clears self.error. Never record message payloads or grant IDs.
                known = {'IPC_SCHEMA_INVALID','IPC_STALE_OR_INVALID_SNAPSHOT',
                         'IPC_SNAPSHOT_TIMEOUT','IPC_PEER_UID_MISMATCH',
                         'PRIVATE_IPC_DIRECTORY_REQUIRED'}
                reason = str(error) if str(error) in known else type(error).__name__.upper()
                self._diagnose('IPC_CONNECTION_LOST', reason=reason,
                    errno=getattr(error,'errno',None),
                    last_valid_snapshot=getattr(self,'last_valid_snapshot_at',None),
                    last_receive_at=getattr(self,'last_snapshot_receive_at',None))
                with self.lock:
                    self.error=type(error).__name__+':'+str(error)
                    self.snapshot=None; self.pending=None; self.initial_pending=None; self.health=(False,False,0)
                self.stop.wait(parameters.IPC_RECONNECT_SECONDS)

    def _connected_loop(self):
        if not hasattr(socket,'SOCK_SEQPACKET'): raise OSError('LINUX_SEQPACKET_REQUIRED')
        parent=Path(self.path).parent.stat()
        if parent.st_uid!=os.geteuid() or parent.st_mode&0o077:
            raise ValueError('PRIVATE_IPC_DIRECTORY_REQUIRED')
        with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as client:
            client.settimeout(parameters.IPC_SOCKET_POLL_SECONDS); client.connect(self.path)
            pid,uid,gid=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=os.geteuid(): raise ValueError('IPC_PEER_UID_MISMATCH')
            last_valid_snapshot=time.monotonic()
            while not self.stop.is_set():
                try:
                    data=client.recv(161)
                except socket.timeout:
                    # The 100 ms socket timeout is a stop-responsive poll, not
                    # the 500 ms snapshot lease. Do not renew health or send a
                    # result without a new snapshot. Send failures still escape.
                    if not 0<=time.monotonic()-last_valid_snapshot<=parameters.IPC_SNAPSHOT_MAX_AGE_SECONDS:
                        raise ValueError('IPC_SNAPSHOT_TIMEOUT')
                    continue
                snapshot=decode_snapshot(data,time.monotonic())
                last_valid_snapshot=snapshot['generated']
                received_at=time.monotonic()
                previous_receive=getattr(self,'last_snapshot_receive_at',received_at)
                self.last_valid_snapshot_at=last_valid_snapshot
                self.last_snapshot_receive_at=received_at
                self._diagnose('IPC_SNAPSHOT_RECEIVED', retain=False,
                    interval_ms=(received_at-previous_receive)*1000,
                    snapshot_age_s=received_at-last_valid_snapshot,
                    connection=snapshot['connection'])
                with self.lock:
                    self.snapshot=snapshot; self.error=None
                    ready,clear,renewed=self.health; pending=self.pending; initial=self.initial_pending
                now=time.monotonic()
                healthy=ready and 0<=now-renewed<=parameters.PLC_HEALTH_LEASE_SECONDS and self.writes_enabled
                if hasattr(self, 'diagnostics'):
                    reason = ('PUBLICATION_DISABLED' if not self.writes_enabled else
                              'READY_FALSE:'+self.ready_reason if not ready else
                              'HEALTH_LEASE_EXPIRED' if not 0<=now-renewed<=parameters.PLC_HEALTH_LEASE_SECONDS else 'READY')
                    changed = reason != getattr(self, '_last_health_reason', None)
                    self._last_health_reason = reason
                    self.diagnostics.record('IPC_HEALTH_SENT', retain=changed, ready=bool(healthy), reason=reason,
                        last_valid_update=renewed, health_age_s=now-renewed,
                        snapshot_age_s=now-snapshot['generated'], adapter_reason=snapshot['reason'])
                client.sendall(command(snapshot,self.runtime_session,1,flags=int(healthy)|(int(healthy and clear)<<1)))
                if initial:
                    boot,connection,approval_id,queued=initial[:4]
                    operation=initial[4] if len(initial)==5 else 4
                    # Reservation is queued before the owner renews health.
                    # Wait for that renewal; remove only before the first send
                    # or at expiration. Never retry an attempted/ambiguous send.
                    if (boot,connection)!=(snapshot['boot'],snapshot['connection']) or not 0<=now-queued<=parameters.IPC_GRANT_LEASE_SECONDS:
                        with self.lock:
                            self.initial_pending=None
                            self.initial_error='INITIAL_GRANT_CONTEXT_OR_LEASE_EXPIRED'
                        self._diagnose('IPC_GRANT_NOT_SENT',
                            reason=self.initial_error, queue_age_s=now-queued,
                            connection_changed=(boot,connection)!=(snapshot['boot'],snapshot['connection']))
                    elif healthy:
                        with self.lock: self.initial_pending=None
                        self._diagnose('IPC_GRANT_SEND_ATTEMPT', queue_age_s=now-queued)
                        client.sendall(command(snapshot,self.runtime_session,operation,approval_id=approval_id))
                        self._diagnose('IPC_GRANT_SENT_AWAIT_C_ACK', queue_age_s=now-queued)
                if pending:
                    key,identifier,decision,queued=pending
                    current=(snapshot['boot'],snapshot['connection'],snapshot['request_id'])
                    if key==current and healthy and now-queued<=parameters.IPC_RESULT_LEASE_SECONDS and snapshot['phase']=='REQUEST_RECEIVED':
                        client.sendall(command(snapshot,self.runtime_session,2,flags=7,
                            identifier=identifier,decision=DECISIONS[decision],approval_id=snapshot['approval_id']))
                        with self.lock:
                            self.sent.add(key)
                            if len(self.sent)>parameters.IPC_SENT_CACHE_LIMIT: self.sent={key}
                    # An ambiguous socket send is never replayed after reconnect.
                    with self.lock: self.pending=None

    def close(self):
        self.cancel(); self.stop.set(); self.thread.join(timeout=parameters.IPC_CLOSE_SECONDS)

class CyclicHandshake:
    """Runtime adapter: journaled AI outcome -> C; never fabricates PLC ACK."""
    def __init__(self,gateway,event):
        self.gateway=gateway; self.event=event; self.state='SYNC_LOW'; self.reason='WAIT_OPENER_IPC'
        self.token=self.inspection_id=self.accepted_at=None
        self.session_id=gateway.runtime_session; self.cycle_id=None
        self.inputs={}; self.outputs={}; self.snapshot=None
        self.cancelled=False; self.publication='NOT_STARTED'; self.request=False
        self.early_off=False; self.clearance_required_after=None
        self.seen_token=None; self.closed=False

    def poll(self,now):
        s=self.gateway.read_snapshot(now); self.snapshot=s
        if s: now=s.get('observed_at',now)
        if not s or not s['connected'] or not s['fresh'] or not s['run_idle'] or not s['bool_valid']:
            self.fault('WAIT_FRESH_OPENER_CONNECTION')
            return
        self.inputs=s['controls']; self.request=self.inputs['Inspection_Request']
        self.outputs=dict(Jetson_Result=s['raw100'][:4]=='0100', Jetson_Done=s['raw100'][4:]=='0100')
        key=f"{s['boot']:016x}:{s['connection']}:{s['request_id']}"
        if s['phase']=='REQUEST_RECEIVED' and key!=self.seen_token and not self.closed:
            self.token=self.seen_token=key; self.cycle_id=s['request_id']; self.accepted_at=s['accepted_at']
            self.inspection_id=None; self.cancelled=False; self.reason=None
            self.state='REQUEST_LATCHED'; self.publication='NOT_STARTED'
            self.event(dict(event='OPENER_AI_REQUEST_ACCEPTED',request_token=key,
                            connection_session=s['connection'],adapter_boot=s['boot']))
        elif s['phase']=='DISARMED':
            self.state='HOLD'; self.reason=s['reason']
            if self.token: self.cancelled=True; self.publication='BLOCKED'
        elif s['phase']=='READY_NEXT' and self.token:
            self.state='WAIT_PRODUCT_CLEAR'; self.reason='CYCLIC_COMPLETED_WAIT_PRODUCT_CLEAR'
            self.publication='CYCLIC_DONE_RESET_SENT'
            if self.clearance_required_after is None: self.clearance_required_after=now
        elif s['phase']=='IDLE':
            self.state='ARMED'; self.reason=None; self.cancelled=False
            self.token=self.inspection_id=self.accepted_at=None
            self.clearance_required_after=None
        elif s['phase'] in ('TEST_RESULT_READY','RESULT_SENT','DONE_SENT','WAIT_REQUEST_OFF','CLEARING_DONE'):
            self.state='WAIT_REQUEST_OFF'; self.publication='CYCLIC_'+s['phase']

    def bind(self,identifier):
        if self.state!='REQUEST_LATCHED' or self.inspection_id:
            raise ValueError('NO_UNBOUND_CYCLIC_REQUEST')
        self.inspection_id=identifier; self.state='INSPECTING'

    def publish(self,identifier,decision,durable,now):
        self.poll(now)
        if durable is not True or identifier!=self.inspection_id or not self.token:
            raise ValueError('PUBLICATION_IDENTITY_OR_DURABILITY_MISMATCH')
        if self.cancelled or self.state!='INSPECTING':
            self.publication='BLOCKED'; return
        self.gateway.result(self.snapshot,identifier,decision)
        self.publication='IPC_QUEUED'
        # Keep the actual four-way decision in IPC. C maps non-PASS to NG.

    def fault(self,reason,status='BLOCKED'):
        if self.token: self.cancelled=True
        self.state='HOLD'; self.reason=reason
        if self.token: self.publication=status
        self.gateway.cancel()

    def shutdown(self):
        self.closed=True; self.fault('LOCAL_SERVICE_STOP')

    def retire_supervised(self):
        # Runtime checked durable completion and operator evidence before this.
        # No resync command/health cancellation: C still owns admission and IDs.
        self.token=self.inspection_id=self.accepted_at=None
        self.clearance_required_after=None
        self.cancelled=False; self.closed=False
        self.state='SYNC_LOW'; self.reason='WAIT_NEW_SUPERVISED_START'
        self.publication='NOT_STARTED'

    def retire_automatic(self):
        # Transaction settlement only; Runtime retains physical product identity
        # independently. seen_token is deliberately never cleared.
        self.retire_supervised()
        self.reason='WAIT_NEXT_PLC_REQUEST'

    def resync(self):
        # Existing maintenance recovery API: only an observed stopped PLC may
        # reopen software acquisition. C still requires a fresh physical START.
        s=self.gateway.read_snapshot(time.monotonic())
        if (not s or not s['connected'] or not s['fresh'] or not s['bool_valid']
                or not s['run_idle'] or s['controls']['Inspection_Request']
                or s['controls']['Mc_Run'] or not s['controls']['EStop_OK']
                or not s['controls']['Stop_PB']):
            raise ValueError('CYCLIC_RECOVERY_REQUIRES_CURRENT_STOPPED_REQUEST_LOW')
        self.gateway.cancel()
        self.closed=False; self.cancelled=False
        self.token=self.inspection_id=self.accepted_at=None
        self.state='SYNC_LOW'; self.reason='WAIT_NEW_PHYSICAL_START'

    def status(self):
        return dict(state=self.state,reason=self.reason,request=self.request,request_token=self.token,
            inspection_id=self.inspection_id,accepted_at=self.accepted_at,publication=self.publication,
            contract_version=CONTRACT,inputs=self.inputs,outputs=self.outputs,cancelled=self.cancelled,
            contract_schema_verified=bool(self.snapshot),snapshot=self.snapshot,
            available=bool(self.snapshot and self.snapshot['connected'] and self.snapshot['fresh']),
            Inspection_Request=self.request, last_values=dict(self.inputs,**self.outputs),
            publication_status=self.publication,
            ack_scope='CYCLIC_SEND_AND_REQUEST_RESET_ONLY',plc_consumption_confirmed=False,
            physical_output_enabled=False,network_plc_writes_enabled=self.gateway.writes_enabled,
            motor_feedback='NOT_AVAILABLE',transport='OPENER_CYCLIC_NO_EXPLICIT_WRITER',
            plc_result_policy=PLC_RESULT_POLICY)
