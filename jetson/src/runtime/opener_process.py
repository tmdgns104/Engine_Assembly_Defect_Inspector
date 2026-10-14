"""The existing systemd service supervises its one cyclic Adapter child.

Transport recovery starts with fresh IPC/PLC sessions; it does not restore an
inspection permission. No sudo, network reconfiguration or PLC commands here.
"""
import hashlib
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import threading
import time

class OpenerProcess:
    def __init__(self, binary, expected_sha, ipc_path, *, approved=False, interface='enP8p1s0'):
        if approved is not True: raise ValueError('FIELD_TRANSPORT_ACTIVATION_NOT_APPROVED')
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
        # Still refuse unknown socket remnants on the first start: explicit
        # stopped maintenance can verify and remove these after a hard crash.
        if self.ipc.exists(): raise ValueError('STALE_OR_COMPETING_IPC_SOCKET_REQUIRES_REVIEW')
        self.stop=threading.Event(); self.child=None; self.error=None; self.restarts=0
        self.interface=interface; self.thread=threading.Thread(target=self._run,name='opener-supervisor',daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop.is_set():
            folder=self.ipc.parent/('session-'+str(time.monotonic_ns()))
            folder.mkdir(mode=0o700)
            env=dict(os.environ,ENGINE_OPENER_MODE='COMM_AI_RUNTIME',
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
