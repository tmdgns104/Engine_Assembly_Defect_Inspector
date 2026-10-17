"""No PLC ownership: mocked startup guards plus Linux-only real UNIX sockets."""
import errno
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.runtime import opener_process


class StaleSocketGuards(unittest.TestCase):
    def test_existing_socket_without_owner_lock_remains_blocked(self):
        with self.assertRaisesRegex(ValueError, 'OWNER_LOCK_REQUIRED'):
            opener_process.preserve_stale_ipc(Path('/unused/ipc'), None)

    def test_process_inventory_rejects_live_competing_opener(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            process=root/'123'
            process.mkdir()
            (process/'cmdline').write_bytes(b'/project/current/opener/OpENer\0enP8p1s0\0')
            uid=process.stat().st_uid
            with patch.object(opener_process.os,'getuid',return_value=uid,create=True):
                self.assertEqual(opener_process.opener_owners(root), [123])


@unittest.skipUnless(sys.platform == 'linux', 'Linux UNIX seqpacket ownership test')
class NativeStaleSocket(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'opener').mkdir(mode=0o700)
        self.ipc=self.root/'opener/ipc'
        self.lock=(self.root/'standalone-owner.lock').open('a+b')
        self.addCleanup(self.lock.close)
        import fcntl
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_stale_socket_is_preserved_then_new_listener_can_bind(self):
        with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as old:
            old.bind(str(self.ipc))
        before=self.ipc.lstat()
        with patch.object(opener_process,'opener_owners',return_value=[]):
            saved=opener_process.preserve_stale_ipc(self.ipc,self.lock)
        self.assertFalse(self.ipc.exists())
        self.assertEqual(Path(saved).lstat().st_ino,before.st_ino)
        self.assertTrue(stat.S_ISSOCK(Path(saved).lstat().st_mode))
        with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as current:
            current.bind(str(self.ipc))

    def test_live_listener_is_never_renamed(self):
        with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as live:
            live.bind(str(self.ipc)); live.listen(1)
            with patch.object(opener_process,'opener_owners',return_value=[]):
                with self.assertRaisesRegex(ValueError,'LIVE_IPC_LISTENER'):
                    opener_process.preserve_stale_ipc(self.ipc,self.lock)
        self.assertTrue(self.ipc.exists())

    def test_regular_file_and_symlink_are_never_moved(self):
        self.ipc.write_text('preserve',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'OWNED_SOCKET_REQUIRED'):
            opener_process.preserve_stale_ipc(self.ipc,self.lock)
        self.assertEqual(self.ipc.read_text(),'preserve')
        link=self.ipc.with_name('link')
        link.symlink_to(self.ipc)
        with self.assertRaisesRegex(ValueError,'OWNED_SOCKET_REQUIRED'):
            opener_process.preserve_stale_ipc(link,self.lock)
        self.assertTrue(link.is_symlink())

    def test_competing_process_blocks_even_without_listener(self):
        with socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) as old:
            old.bind(str(self.ipc))
        with patch.object(opener_process,'opener_owners',return_value=[456]):
            with self.assertRaisesRegex(ValueError,'COMPETING_OPENER_PROCESS'):
                opener_process.preserve_stale_ipc(self.ipc,self.lock)
        self.assertTrue(self.ipc.exists())


if __name__=='__main__':
    unittest.main()
