#!/usr/bin/env python3
"""Render local Surge and Clash clients from the live sing-box config.

The server is read through `ssh banwa`. Passwords and the public address are
written only under ~/Library/Application Support. This script refuses to write
inside the git repository.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SURGE_PATH = Path.home() / "Library/Application Support/Surge/Profiles/NY.conf"
CLASH_DIR = Path.home() / "Library/Application Support/Clash"
MAC_CLASH = CLASH_DIR / "NY.yaml"
ANDROID_CLASH = CLASH_DIR / "NY-android.yaml"
MIHOMO = (
    Path.home()
    / "Library/Application Support/com.aegisclient.cloud/bin/mihomo-darwin-arm64"
)
SURGE_CLI = Path("/Applications/Surge.app/Contents/Applications/surge-cli")

REMOTE = r"""
import json
c = json.load(open("/etc/sing-box/config.json"))
st = next(i for i in c["inbounds"] if i.get("type") == "shadowtls")
ss = next(i for i in c["inbounds"] if i.get("type") == "shadowsocks")
print(json.dumps({
    "sni": (st.get("handshake") or {}).get("server"),
    "port": st.get("listen_port"),
    "version": st.get("version"),
    "strict": st.get("strict_mode"),
    "st_password": (st.get("users") or [{}])[0].get("password"),
    "method": ss.get("method"),
    "ss_password": ss.get("password"),
    "ss_network": ss.get("network"),
    "ss_listen": ss.get("listen"),
}))
"""


def ssh_read() -> dict:
    host = subprocess.run(
        ["ssh", "-G", "banwa"],
        check=True,
        capture_output=True,
        text=True,
    )
    hostname = ""
    for line in host.stdout.splitlines():
        if line.startswith("hostname "):
            hostname = line.split(None, 1)[1].strip()
            break
    if not hostname:
        raise SystemExit("banwa has no hostname")
    remote = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "banwa", "python3", "-"],
        input=REMOTE,
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(remote.stdout)
    data["host"] = hostname
    return data


def check_source(data: dict) -> None:
    if data.get("sni") != "www.microsoft.com":
        raise SystemExit("handshake server is not www.microsoft.com")
    if data.get("port") != 443 or data.get("version") != 3 or data.get("strict") is not True:
        raise SystemExit("shadowtls is not v3 strict on 443")
    if data.get("method") != "2022-blake3-aes-128-gcm":
        raise SystemExit("unexpected shadowsocks method")
    if data.get("ss_network") != "tcp" or data.get("ss_listen") != "127.0.0.1":
        raise SystemExit("shadowsocks is not tcp on localhost")
    if not re.fullmatch(r"[A-Za-z0-9+/]{22}==", data["ss_password"] or ""):
        raise SystemExit("shadowsocks password has an unexpected shape")
    if not re.fullmatch(r"[0-9a-f]{48}", data["st_password"] or ""):
        raise SystemExit("shadowtls password has an unexpected shape")
    if not re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", data["host"]):
        raise SystemExit("banwa hostname is not an ipv4 address")


def outside_repo(path: Path) -> None:
    resolved = path.resolve()
    if REPO_ROOT in resolved.parents or resolved == REPO_ROOT:
        raise SystemExit(f"refusing to write inside the repo: {resolved}")


def quote_yaml(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_private(path: Path, text: str) -> None:
    outside_repo(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chmod(path, 0o600)


def render_surge(data: dict) -> bool:
    text = SURGE_PATH.read_text()
    line = (
        f"NY = ss, {data['host']}, 443, encrypt-method={data['method']}, "
        f"password={data['ss_password']}, udp-relay=false, "
        f"shadow-tls-password={data['st_password']}, "
        f"shadow-tls-sni={data['sni']}, shadow-tls-version=3, block-quic=on"
    )
    new, count = re.subn(r"(?m)^NY = ss,.*$", line, text, count=1)
    if count != 1:
        raise SystemExit("NY proxy line was not found")
    direct = f"IP-CIDR,{data['host']}/32,DIRECT,no-resolve"
    new2, count = re.subn(
        r"(?m)^IP-CIDR,\d{1,3}(?:\.\d{1,3}){3}/32,DIRECT,no-resolve$",
        direct,
        new,
        count=1,
    )
    if count != 1:
        raise SystemExit("VPS direct rule was not found")
    if "ChinaMax_Domain.list" not in new2 or "FINAL,Proxy" not in new2:
        raise SystemExit("refusing to rewrite a Surge profile without the China rules")
    new2 = ensure_surge_rules(new2)
    changed = new2 != text
    if changed:
        write_private(SURGE_PATH, new2)
    return changed


def clash_proxy(data: dict, indent: str) -> str:
    return "\n".join(
        [
            f"{indent}- name: NY",
            f"{indent}  type: ss",
            f"{indent}  server: {data['host']}",
            f"{indent}  port: 443",
            f"{indent}  cipher: {data['method']}",
            f"{indent}  password: {quote_yaml(data['ss_password'])}",
            f"{indent}  udp: false",
            f"{indent}  ip-version: ipv4",
            f"{indent}  plugin: shadow-tls",
            f"{indent}  client-fingerprint: chrome",
            f"{indent}  plugin-opts:",
            f"{indent}    host: {data['sni']}",
            f"{indent}    password: {quote_yaml(data['st_password'])}",
            f"{indent}    version: 3",
        ]
    )


RULES = """rules:
  - IP-CIDR,0.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,10.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,100.64.0.0/10,DIRECT,no-resolve
  - IP-CIDR,127.0.0.0/8,DIRECT,no-resolve
  - IP-CIDR,169.254.0.0/16,DIRECT,no-resolve
  - IP-CIDR,172.16.0.0/12,DIRECT,no-resolve
  - IP-CIDR,192.168.0.0/16,DIRECT,no-resolve
  - IP-CIDR,224.0.0.0/4,DIRECT,no-resolve
  - IP-CIDR,255.255.255.255/32,DIRECT,no-resolve
  - DOMAIN-SUFFIX,21zhao.com,DIRECT
  - DOMAIN-SUFFIX,lanxin.cn,DIRECT
  - DOMAIN-SUFFIX,css.com.cn,DIRECT
  - DOMAIN-SUFFIX,cec.com.cn,DIRECT
  - DOMAIN-SUFFIX,cn,DIRECT
  - GEOSITE,cn,DIRECT
  - AND,((NETWORK,UDP),(DST-PORT,443)),REJECT
  - DOMAIN-SUFFIX,youtube.com,Proxy
  - DOMAIN-SUFFIX,youtu.be,Proxy
  - DOMAIN-SUFFIX,youtube-nocookie.com,Proxy
  - DOMAIN-SUFFIX,googlevideo.com,Proxy
  - DOMAIN-SUFFIX,ytimg.com,Proxy
  - DOMAIN-SUFFIX,ggpht.com,Proxy
  - DOMAIN-SUFFIX,gstatic.com,Proxy
  - DOMAIN-SUFFIX,googleapis.com,Proxy
  - GEOIP,CN,DIRECT
  - MATCH,Proxy
"""


SURGE_GENERAL_REJECT = "udp-policy-not-supported-behaviour = REJECT"
SURGE_MANAGED_RULES = (
    "PROTOCOL,QUIC,REJECT-NO-DROP",
    "DOMAIN-SUFFIX,youtube.com,Proxy",
    "DOMAIN-SUFFIX,youtu.be,Proxy",
    "DOMAIN-SUFFIX,youtube-nocookie.com,Proxy",
    "DOMAIN-SUFFIX,googlevideo.com,Proxy",
    "DOMAIN-SUFFIX,ytimg.com,Proxy",
    "DOMAIN-SUFFIX,ggpht.com,Proxy",
    "DOMAIN-SUFFIX,gstatic.com,Proxy",
    "DOMAIN-SUFFIX,googleapis.com,Proxy",
)


def ensure_surge_rules(text: str) -> str:
    """Keep QUIC from waiting out, and keep YouTube names ahead of GEOIP."""
    if SURGE_GENERAL_REJECT not in text:
        if "ipv6 = false" not in text:
            raise SystemExit("surge profile has no ipv6 line to anchor the UDP fallback")
        text = text.replace(
            "ipv6 = false\n",
            "ipv6 = false\n" + SURGE_GENERAL_REJECT + "\n",
            1,
        )
    kept = [line for line in text.splitlines() if line.strip() not in SURGE_MANAGED_RULES]
    text = "\n".join(kept)
    if not text.endswith("\n"):
        text += "\n"
    needle = "GEOIP,CN,DIRECT"
    if text.count(needle) != 1:
        raise SystemExit("refusing to place YouTube rules without exactly one GEOIP line")
    block = "\n".join(SURGE_MANAGED_RULES) + "\n"
    return text.replace(needle, block + needle, 1)


def render_mac(data: dict) -> str:
    return f"""# Generated by personal-proxy/scripts/render_clients.py. Do not upload.
# Local only. Do not run this together with Surge system proxy.
mixed-port: 17890
bind-address: 127.0.0.1
allow-lan: false
mode: rule
log-level: warning
ipv6: false
find-process-mode: off
geodata-mode: true
geo-auto-update: false
unified-delay: true
tcp-concurrent: false
dns:
  enable: true
  listen: 127.0.0.1:1053
  ipv6: false
  enhanced-mode: redir-host
  use-hosts: true
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
tun:
  enable: false
proxies:
{clash_proxy(data, "  ")}
proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - NY
      - DIRECT
{RULES}"""


def render_android(data: dict) -> str:
    return f"""# Generated by personal-proxy/scripts/render_clients.py. Do not upload.
# Phone profile. Import locally. The app owns the VPN tunnel.
mode: rule
log-level: warning
ipv6: false
find-process-mode: off
geodata-mode: false
geo-auto-update: false
unified-delay: true
tcp-concurrent: false
dns:
  enable: true
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 28.0.0.1/8
  fake-ip-filter:
    - '*.lan'
    - '*.local'
    - '+.cn'
    - '+.21zhao.com'
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
  fallback:
    - tls://1.1.1.1
    - tls://8.8.8.8
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4
sniffer:
  enable: true
  force-dns-mapping: true
  parse-pure-ip: true
  override-destination: true
  sniff:
    TLS:
      ports: [443, 8443]
    HTTP:
      ports: [80, 8080-8880]
proxies:
{clash_proxy(data, "  ")}
proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - NY
      - DIRECT
{RULES}"""


def check_outputs(data: dict) -> None:
    secrets = (data["ss_password"], data["st_password"], data["host"])
    for path in (MAC_CLASH, ANDROID_CLASH):
        text = path.read_text()
        if "skip-cert-verify" in text or "GEOSITE,cn,DIRECT" not in text:
            raise SystemExit(f"bad clash output: {path.name}")
        for needle in (
            "AND,((NETWORK,UDP),(DST-PORT,443)),REJECT",
            "DOMAIN-SUFFIX,youtube.com,Proxy",
            "DOMAIN-SUFFIX,gstatic.com,Proxy",
            "DOMAIN-SUFFIX,googleapis.com,Proxy",
        ):
            if needle not in text:
                raise SystemExit(f"clash output missing {needle}")
        proc = subprocess.run(
            [str(MIHOMO), "-d", str(CLASH_DIR), "-f", str(path), "-t"],
            capture_output=True,
            text=True,
        )
        message = (proc.stdout or "") + (proc.stderr or "")
        for secret in secrets:
            message = message.replace(secret, "<redacted>")
        print(f"CHECK {path.name} {proc.returncode}")
        if proc.returncode != 0:
            print(message[-800:])
            raise SystemExit(proc.returncode)
    surge_text = SURGE_PATH.read_text()
    for needle in (
        "udp-relay=false",
        "block-quic=on",
        "udp-policy-not-supported-behaviour = REJECT",
        "PROTOCOL,QUIC,REJECT-NO-DROP",
        "DOMAIN-SUFFIX,youtube.com,Proxy",
        "DOMAIN-SUFFIX,gstatic.com,Proxy",
        "DOMAIN-SUFFIX,googleapis.com,Proxy",
        "FINAL,Proxy",
    ):
        if needle not in surge_text:
            raise SystemExit(f"surge profile missing {needle}")
    proc = subprocess.run([str(SURGE_CLI), "--check", str(SURGE_PATH)], capture_output=True, text=True)
    message = (proc.stdout or "") + (proc.stderr or "")
    for secret in secrets:
        message = message.replace(secret, "<redacted>")
    print(f"CHECK surge {proc.returncode}")
    if proc.returncode != 0:
        print(message[-800:])
        raise SystemExit(proc.returncode)


def main() -> None:
    data = ssh_read()
    check_source(data)
    surge_changed = render_surge(data)
    write_private(MAC_CLASH, render_mac(data))
    write_private(ANDROID_CLASH, render_android(data))
    check_outputs(data)
    if surge_changed:
        subprocess.run([str(SURGE_CLI), "reload"], check=True)
        print("SURGE_RELOADED")
    else:
        print("SURGE_UNCHANGED")
    print("WROTE surge", oct(SURGE_PATH.stat().st_mode & 0o777))
    print("WROTE", MAC_CLASH.name, oct(MAC_CLASH.stat().st_mode & 0o777), MAC_CLASH.stat().st_size)
    print("WROTE", ANDROID_CLASH.name, oct(ANDROID_CLASH.stat().st_mode & 0o777), ANDROID_CLASH.stat().st_size)
    print("SNI", data["sni"], "METHOD", data["method"], "PORT", data["port"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"command failed: {exc.cmd[0]} exit {exc.returncode}\n")
        raise SystemExit(exc.returncode) from exc
