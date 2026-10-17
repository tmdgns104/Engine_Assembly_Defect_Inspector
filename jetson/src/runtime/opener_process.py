"""The existing systemd service supervises its one cyclic Adapter child.

Transport recovery starts with fresh IPC/PLC sessions; it does not restore an
inspection permission. No sudo, network reconfiguration or PLC commands here.
"""
import hashlib
import errno
import logging
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import threading
import time
import uuid


def opener_owners(proc=Path('/proc')):
    """Read only same-user process command names; never expose their environment."""
    owners = []
    for path in proc.iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            args = (path/'cmdline').read_bytes().split(b'\0')
            if any(arg == b'OpENer' or arg.endswith(b'/OpENer') for arg in args):
                owners.append(int(path.name))
        except FileNotFoundError:
            continue  # Process exited during the read. Other failures are fatal.
    return sorted(owners)


def preserve_stale_ipc(ipc, owner_lock):
    """Preserve a proved dead local socket before automatic service startup.

    The existing supervisor lock, private directory, absence of competing C
    processes and ECONNREFUSED are all required. No journal/request is reset.
    """
    if owner_lock is None or owner_lock.closed:
        raise ValueError('OWNER_LOCK_REQUIRED')
    import fcntl
    expected_lock = ipc.parent.parent/'standalone-owner.lock'
    if Path(owner_lock.name).resolve() != expected_lock.resolve():
        raise ValueError('OWNER_LOCK_REQUIRED')
    lock_stat = expected_lock.lstat()
    if (not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != os.getuid()
            or (lock_stat.st_dev, lock_stat.st_ino) !=
               (os.fstat(owner_lock.fileno()).st_dev, os.fstat(owner_lock.fileno()).st_ino)):
        raise ValueError('OWNER_LOCK_REQUIRED')
    fcntl.flock(owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    parent = ipc.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('PRIVATE_IPC_DIRECTORY_REQUIRED')
    before = ipc.lstat()
    if not stat.S_ISSOCK(before.st_mode) or before.st_uid != os.getuid():
        raise ValueError('OWNED_SOCKET_REQUIRED')
    if opener_owners():
        raise ValueError('COMPETING_OPENER_PROCESS')
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as probe:
        probe.settimeout(.5)
        try:
            probe.connect(str(ipc))
        except OSError as error:
            if error.errno != errno.ECONNREFUSED:
                raise ValueError('IPC_OWNERSHIP_UNPROVEN') from error
        else:
            raise ValueError('LIVE_IPC_LISTENER')
    after = ipc.lstat()
    if (before.st_dev, before.st_ino, before.st_mode, before.st_uid) != (
            after.st_dev, after.st_ino, after.st_mode, after.st_uid):
        raise ValueError('IPC_CHANGED_DURING_STARTUP')
    preserved = ipc.with_name(ipc.name+'.stale-'+uuid.uuid4().hex)
    ipc.rename(preserved)
    logging.getLogger(__name__).warning('Preserved verified unowned IPC socket: %s', preserved)
    return str(preserved)

class OpenerProcess:
    def __init__(self, binary, expected_sha, ipc_path, *, approved=False, interface='enP8p1s0',
                 admission='FIRST_PRODUCT_ONLY', owner_lock=None):
        if approved is not True: raise ValueError('FIELD_TRANSPORT_ACTIVATION_NOT_APPROVED')
        if admission not in ('FIRST_PRODUCT_ONLY', 'SUPERVISED_REPEAT_TEST', 'PLC_AUTOMATIC_REPEAT'):
            raise ValueError('UNKNOWN_OPENER_ADMISSION_POLICY')
        self.admission=admission
        self.binary=Path(binary).resolve(); self.ipc=Path(ipc_path)
        if hashlib.sha256(self.binary.read_bytes()).hexdigest()!=expected_sha:
            raise ValueError('OPENER_BINARY_HASH_MISMATCH')
        if interface!='enP8p1s0': raise ValueError('FIELD_INTERFACE_MISMATCH')
        # An existing listener is a competing owner, regardless of its name.
        for kind,port in ((socket.SOCK_STREAM,44818),(socket.SOCK_DGRAM,44818),(socket.SOCK_DGRAM,2222)):
            with socket.socket(socket.AF_INET,kind) as probe: probe.bind(('0.0.0.0',port))
        self.ipc.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        info=self.ipc.parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
            raise ValueError('PRIVATE_IPC_DIRECTORY_REQUIRED')
        # The entrypoint's exclusive standalone-owner.lock is already held.
        # A hard crash may leave a filesystem socket with no live owner. Keep
        # it as evidence; competing/unknown ownership still blocks startup.
        if self.ipc.exists() or self.ipc.is_symlink():
            preserve_stale_ipc(self.ipc, owner_lock)
        self.stop=threading.Event(); self.child=None; self.error=None; self.restarts=0
        self.interface=interface; self.thread=threading.Thread(target=self._run,name='opener-supervisor',daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop.is_set():
            folder=self.ipc.parent/('session-'+str(time.monotonic_ns()))
            folder.mkdir(mode=0o700)
            env=dict(os.environ,ENGINE_OPENER_MODE='COMM_AI_RUNTIME',
                ENGINE_OPENER_ADMISSION=self.admission,
                ENGINE_OPENER_ENCODING='BOOL16_LE_0_1_VERIFIED',ENGINE_OPENER_IPC=str(self.ipc),
                ENGINE_OPENER_EVENTS=str(folder/'events.jsonl'),ENGINE_OPENER_STATUS=str(folder/'status.json'))
            try:
                # C events are bounded; stderr remains visible in the existing
                # systemd journal, rather than a new unlimited log file.
                self.child=subprocess.Popen([str(self.binary),self.interface],cwd=folder,env=env)
                while self.child.poll() is None and not self.stop.wait(.1): pass
                if self.child.poll() is None:
                    self.child.send_signal(signal.SIGINT)
                    try:self.child.wait(timeout=3)
                    except subprocess.TimeoutExpired:self.child.kill();self.child.wait(timeout=2)
                self.error='OPENER_EXIT:'+str(self.child.returncode)
            except OSError as error:
                self.error=type(error).__name__+':'+str(error)
            finally:
                # Only after OUR child exited may its socket be removed.
                if self.child and self.child.poll() is not None and self.ipc.exists():
                    info=self.ipc.lstat()
                    if stat.S_ISSOCK(info.st_mode) and info.st_uid==os.getuid(): self.ipc.unlink()
            if self.stop.is_set(): return
            self.restarts+=1
            # Bounded recovery avoids filling storage after repeated failures.
            if self.restarts>=3:
                self.error='OPENER_RECOVERY_LIMIT'; return
            self.stop.wait(3)

    def close(self):
        self.stop.set(); self.thread.join(timeout=6)
        if self.thread.is_alive(): raise RuntimeError('OPENER_CHILD_STOP_NOT_CONFIRMED')
