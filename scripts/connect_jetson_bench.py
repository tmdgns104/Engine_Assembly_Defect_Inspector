"""Run interactively on Windows to authorize a dedicated SSH key on your Jetson.

OpenSSH owns password/host-key prompts; this program never reads a password.
Existing remote authorized keys and host verification remain intact.
"""

import argparse
import shlex
import subprocess
from pathlib import Path


def authorize_command(public_key):
    key = shlex.quote(public_key.strip())
    return ("umask 077; mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && "
            f"(grep -qxF -- {key} ~/.ssh/authorized_keys || "
            f"printf '%s\\n' {key} >> ~/.ssh/authorized_keys)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Current, user-confirmed username@host")
    args = parser.parse_args()
    if args.target.startswith("-") or "@" not in args.target or any(c.isspace() for c in args.target):
        parser.error("Expected username@host without whitespace")
    key = Path.home() / ".ssh/oned_device_jetson_bench_ed25519"
    if not key.exists():
        if key.with_suffix(".pub").exists():
            raise RuntimeError("Public key exists without private key; preserve and resolve manually")
        key.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-N", "",
                        "-C", "OneDevice Jetson BENCH"], check=True)
    public_key = key.with_suffix(".pub").read_text(encoding="ascii")
    print("OpenSSH may request your Jetson password in this terminal. Do not send it in chat.")
    subprocess.run(["ssh", "-o", "ConnectTimeout=10", args.target,
                    authorize_command(public_key)], check=True)
    subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
                    "-o", "ConnectTimeout=10", "-i", str(key), args.target,
                    "hostname; uname -m"], check=True)
    print("Dedicated key authentication verified. Tell Codex this command completed.")


if __name__ == "__main__":
    main()
