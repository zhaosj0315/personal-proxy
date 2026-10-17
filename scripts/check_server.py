#!/usr/bin/env python3
"""Check the VPS shape over ssh banwa. Prints no passwords and no public address."""

from __future__ import annotations

import json
import subprocess
import sys

EXPECTED_SHA256 = "768d31fa7f68debc067bb4626539498a1e8751d36a7b99e1a54bee6a23815f93"

REMOTE = r"""
import hashlib, json, subprocess
from pathlib import Path

def run(args):
    proc = subprocess.run(args, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

problems = []
binary = Path("/usr/local/bin/sing-box")
if not binary.is_file():
    problems.append("sing-box binary missing")
else:
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if digest != "EXPECTED_SHA256":
        problems.append("sing-box binary hash differs")
code, text = run(["sing-box", "version"])
if "1.14.3" not in text:
    problems.append("sing-box version is not 1.14.3")
code, cap = run(["getcap", "/usr/local/bin/sing-box"])
if "cap_net_bind_service=ep" not in cap:
    problems.append("sing-box is missing cap_net_bind_service")
code, active = run(["systemctl", "is-active", "sing-box"])
if active.strip() != "active":
    problems.append("sing-box service is not active")
cfg_path = Path("/etc/sing-box/config.json")
if not cfg_path.is_file():
    problems.append("config missing")
else:
    cfg = json.loads(cfg_path.read_text())
    inbound = {item.get("type"): item for item in cfg.get("inbounds") or []}
    st = inbound.get("shadowtls") or {}
    ss = inbound.get("shadowsocks") or {}
    handshake = st.get("handshake") or {}
    if st.get("listen") != "::" or st.get("listen_port") != 443 or st.get("version") != 3 or st.get("strict_mode") is not True:
        problems.append("shadowtls is not v3 strict on 443")
    if handshake.get("server") != "www.microsoft.com" or handshake.get("server_port") != 443:
        problems.append("handshake server is not www.microsoft.com")
    if st.get("detour") != "ss-in":
        problems.append("shadowtls does not detour to ss-in")
    if ss.get("listen") != "127.0.0.1" or ss.get("listen_port") != 8388 or ss.get("network") != "tcp":
        problems.append("shadowsocks is not tcp on localhost")
    if ss.get("method") != "2022-blake3-aes-128-gcm":
        problems.append("unexpected shadowsocks method")
code, fw = run(["firewall-cmd", "--list-all"])
if "target: DROP" not in fw or "443/tcp" not in fw or " ssh" not in fw and "services: ssh" not in fw:
    problems.append("firewalld is not DROP with ssh and 443/tcp")
for name in ("nginx", "hysteria"):
    code, state = run(["systemctl", "is-active", name])
    if state.strip() == "active":
        problems.append(name + " is active")
key_only = Path("/etc/ssh/sshd_config.d/99-key-only.conf")
text = key_only.read_text() if key_only.is_file() else ""
if "PasswordAuthentication no" not in text or "PermitRootLogin prohibit-password" not in text:
    problems.append("sshd key-only drop-in missing")
print(json.dumps({"ok": not problems, "problems": problems}))
""".replace("EXPECTED_SHA256", EXPECTED_SHA256)


def main() -> None:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "banwa", "python3", "-"],
        input=REMOTE,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write("ssh banwa failed\n")
        raise SystemExit(proc.returncode or 1)
    try:
        report = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        sys.stderr.write("server check returned no report\n")
        raise SystemExit(1) from exc
    if report.get("ok"):
        print("CHECK server 0")
        return
    for item in report.get("problems") or []:
        print("PROBLEM", item)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
