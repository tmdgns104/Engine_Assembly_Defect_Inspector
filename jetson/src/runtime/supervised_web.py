"""Narrow operator preparation capability; no motor, reset, or result endpoint.

A private per-service secret pairs the operator browser once. It is never
returned by a GET or logged. An exact host and same-origin check protects the
field interface; all other POST routes remain forbidden by standalone_web.
"""
import hmac
import secrets
from urllib.parse import urlsplit

from src.runtime.initial_approval import atomic_json

PREPARE_PATH = '/api/v1/line/supervised/prepare'


class PreparationAccess:
    def __init__(self, approval_root, hosts, *, purpose='SUPERVISED_PREPARE_ONLY'):
        if (not isinstance(hosts, list) or not hosts or len(hosts) > 8
                or any(not isinstance(host, str) or not host or '/' in host
                       or '@' in host or '*' in host or urlsplit('//'+host).netloc != host
                       for host in hosts)):
            raise ValueError('EXPLICIT_SUPERVISED_WEB_HOSTS_REQUIRED')
        self.hosts = frozenset(hosts)
        self.token = secrets.token_urlsafe(32)
        atomic_json(approval_root/'web_pairing.json', dict(token=self.token,
            purpose=purpose, restored=False))

    def permits(self, request):
        host = request.headers.get('host', '')
        origin = request.headers.get('origin', '')
        auth = request.headers.get('authorization', '')
        expected = 'Bearer '+self.token
        return bool(auth.isascii() and host in self.hosts and origin == request.url.scheme+'://'+host
                    and hmac.compare_digest(auth, expected))
