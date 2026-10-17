#!/usr/bin/env python3
"""Install the sing-box shape on the VPS behind ssh banwa.

Without --apply this only runs the read-only check. With --apply, a server
that already matches is left untouched. A missing binary is downloaded and
checked against the pinned hash. A missing config is created on the server.
An existing config or a different binary is never replaced. Passwords and the
public address are not printed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "check_server.py"
UNIT = (HERE / "sing-box.service").read_text()
SSHD = (HERE / "sshd-key-only.conf").read_text()

REMOTE = r"""
import base64, hashlib, json, os, secrets, shutil, subprocess, tarfile, tempfile, urllib.request
from pathlib import Path

UNIT = __UNIT__
SSHD = __SSHD__
SHA = "768d31fa7f68debc067bb4626539498a1e8751d36a7b99e1a54bee6a23815f93"
URL = "https://github.com/SagerNet/sing-box/releases/download/v1.14.3/sing-box-1.14.3-linux-amd64.tar.gz"
BINARY = Path("/usr/local/bin/sing-box")
CONFIG = Path("/etc/sing-box/config.json")
UNIT_PATH = Path("/etc/systemd/system/sing-box.service")
SSHD_PATH = Path("/etc/ssh/sshd_config.d/99-key-only.conf")

def run(args, allow_already=False):
    proc = subprocess.run(args, capture_output=True, text=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return
    if allow_already and "ALREADY_ENABLED" in text:
        return
    raise SystemExit("command failed: " + " ".join(args[:3]))

def binary_ok():
    return BINARY.is_file() and hashlib.sha256(BINARY.read_bytes()).hexdigest() == SHA

if not binary_ok():
    if BINARY.is_file():
        raise SystemExit("refusing to replace a sing-box binary with a different hash")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "sing-box.tar.gz"
        urllib.request.urlretrieve(URL, archive)
        with tarfile.open(archive) as packed:
            member = next(
                item for item in packed.getmembers()
                if item.isfile() and item.name.endswith("/sing-box")
            )
            source = packed.extractfile(member)
            if source is None:
                raise SystemExit("archive member is empty")
            BINARY.write_bytes(source.read())
        BINARY.chmod(0o755)
    if not binary_ok():
        BINARY.unlink(missing_ok=True)
        raise SystemExit("downloaded sing-box hash does not match")

if subprocess.run(["id", "sing-box"], capture_output=True).returncode != 0:
    run(["useradd", "--system", "--no-create-home", "--shell", "/sbin/nologin", "sing-box"])
run(["setcap", "cap_net_bind_service=ep", str(BINARY)])
Path("/etc/sing-box").mkdir(mode=0o755, exist_ok=True)
if not CONFIG.is_file():
    config = {
        "log": {"level": "warn", "timestamp": True},
        "inbounds": [
            {
                "type": "shadowtls",
                "tag": "st-in",
                "listen": "::",
                "listen_port": 443,
                "version": 3,
                "users": [{"name": "ny", "password": secrets.token_hex(24)}],
                "handshake": {"server": "www.microsoft.com", "server_port": 443},
                "strict_mode": True,
                "detour": "ss-in",
            },
            {
                "type": "shadowsocks",
                "tag": "ss-in",
                "listen": "127.0.0.1",
                "listen_port": 8388,
                "network": "tcp",
                "method": "2022-blake3-aes-128-gcm",
                "password": base64.b64encode(secrets.token_bytes(16)).decode(),
            },
        ],
    }
    CONFIG.write_text(json.dumps(config, indent=2) + "\n")
    os.chmod(CONFIG, 0o640)
    shutil.chown(CONFIG, "sing-box", "sing-box")
if not UNIT_PATH.is_file():
    UNIT_PATH.write_text(UNIT)
    run(["systemctl", "daemon-reload"])
elif UNIT_PATH.read_text() != UNIT:
    raise SystemExit("refusing to replace a different sing-box unit")
run(["systemctl", "enable", "--now", "sing-box"])
run(["firewall-cmd", "--permanent", "--add-service=ssh"], allow_already=True)
run(["firewall-cmd", "--permanent", "--add-port=443/tcp"], allow_already=True)
run(["firewall-cmd", "--permanent", "--set-target=DROP"], allow_already=True)
run(["firewall-cmd", "--reload"])
if not SSHD_PATH.is_file():
    SSHD_PATH.parent.mkdir(mode=0o755, exist_ok=True)
    SSHD_PATH.write_text(SSHD)
    run(["systemctl", "reload", "sshd"])
elif SSHD_PATH.read_text() != SSHD:
    raise SystemExit("refusing to replace a different sshd drop-in")
print("APPLY done")
"""


def remote_script() -> str:
    return (
        REMOTE
        .replace("__UNIT__", json.dumps(UNIT))
        .replace("__SSHD__", json.dumps(SSHD))
    )


def main() -> None:
    apply = "--apply" in sys.argv
    check = subprocess.run([sys.executable, str(CHECK)])
    if not apply:
        raise SystemExit(check.returncode)
    if check.returncode == 0:
        print("APPLY skipped; server shape already matches")
        return
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "banwa", "python3", "-"],
        input=remote_script(),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write("apply failed\n")
        raise SystemExit(proc.returncode or 1)
    if "APPLY done" not in proc.stdout:
        sys.stderr.write("apply finished without confirmation\n")
        raise SystemExit(1)
    print("APPLY done")


if __name__ == "__main__":
    main()
