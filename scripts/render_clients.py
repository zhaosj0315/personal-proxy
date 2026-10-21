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
ADBLOCK_URL = (
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/"
    "rule/Surge/Advertising/Advertising_All_No_Resolve.list"
)
ADBLOCK_PROVIDER = f"""rule-providers:
  adblock:
    type: http
    behavior: classical
    format: text
    url: {ADBLOCK_URL}
    path: ./ruleset/adblock.list
    interval: 86400
    proxy: NY
"""

# Hosts the public list still sends direct, and that are ad endpoints rather than
# the app's own API. Company suffixes stay untouched.
APP_AD_DOMAINS = (
    "uve.weibo.com",
    "splash.pinduoduo.com",
    "splash.goofish.com",
    "ad.goofish.com",
    "sugar.zhihu.com",
    "splash.zhihu.com",
    "splash.jd.com",
    "ads.jd.com",
    "splash.xiaohongshu.com",
    "ads.xiaohongshu.com",
    "api-ad-product.huxiu.com",
    "jad-api.jin10.com",
)

# HTTPS paths on a shared API host. Domain reject would take the app down with the ad.
# Surge answers these locally. Clash Meta only sees the hostname, so it cannot apply them.
SPLASH_REWRITES = (
    r"^https?://(g-)?acs\.m\.goofish\.com/gw/mtop\..*splash(\.async)?\.ads",
    r"^https?://(g-)?acs\.m\.goofish\.com/gw/mtop\.idle\.ad\.expose",
    r"^https?://(g-)?acs\.m\.goofish\.com/gw/mtop\.idle\.idleadv\.(app\.launch\.report|scene\.restore)",
    r"^https?://acs\.m\.taobao\.com/gw/mtop\.taobao\.idle\.home\.welcome",
    r"^https?://acs\.m\.taobao\.com/gw/mtop\.alibaba\.advertisementservice\.getadv",
    r"^https?://app\.bilibili\.com/x/v2/splash/",
    r"^https?://manga\.bilibili\.com/twirp/comic\.v[0-9]+\.Comic/(Flash|ListFlash)",
    r"^https?://api\.m\.jd\.com/client\.action\?(?:.*&)?functionId=lite_advertising(?:&|$)",
    r"^https?://ms\.jr\.jd\.com/gw/generic/aladdin/(?:new)?na/m/getLoadingPicture",
    r"^https?://homefront\.qunar\.com/front/splash/ad",
    r"^https?://appconf\.mail\.163\.com/mmad/get\.do",
    r"^https?://api\.kkmh\.com/v[0-9]+/(?:ad|advertisement)/",
    r"^https?://app\.58\.com/api/home/(?:advertising|appadv)/",
)

MITM_HOSTS = (
    "acs.m.goofish.com",
    "g-acs.m.goofish.com",
    "acs.m.taobao.com",
    "app.bilibili.com",
    "manga.bilibili.com",
    "api.m.jd.com",
    "ms.jr.jd.com",
    "homefront.qunar.com",
    "appconf.mail.163.com",
    "api.kkmh.com",
    "app.58.com",
)

SPLASH_CASES = (
    ("https://acs.m.goofish.com/gw/mtop.taobao.idlecommerce.splash.async.ads/1.0/", True),
    ("https://g-acs.m.goofish.com/gw/mtop.foo.splash.ads/1.0/?data=1", True),
    ("https://acs.m.goofish.com/gw/mtop.idle.ad.expose/1.0/", True),
    ("https://g-acs.m.goofish.com/gw/mtop.idle.idleadv.app.launch.report/1.0/", True),
    ("https://acs.m.goofish.com/gw/mtop.idle.idleadv.scene.restore/1.0/", True),
    ("https://acs.m.goofish.com/gw/mtop.taobao.idlehome.home.nextfresh/1.0/", False),
    ("https://acs.m.goofish.com/gw/mtop.taobao.idle.item.recommend/1.0/", False),
    ("https://h5.m.goofish.com/wow/moyu", False),
    ("https://acs.m.taobao.com/gw/mtop.taobao.idle.home.welcome/1.0/", True),
    ("https://acs.m.taobao.com/gw/mtop.alibaba.advertisementservice.getadv/1.0/", True),
    ("https://acs.m.taobao.com/gw/mtop.taobao.idle.item.recommend/1.0/", False),
    ("https://app.bilibili.com/x/v2/splash/show?ts=1", True),
    ("https://app.bilibili.com/x/v2/feed/index", False),
    ("https://api.bilibili.com/x/v2/splash/show", False),
    ("https://manga.bilibili.com/twirp/comic.v1.Comic/Flash", True),
    ("https://manga.bilibili.com/twirp/comic.v1.Comic/GetComic", False),
    ("https://api.m.jd.com/client.action?functionId=lite_advertising&client=android", True),
    ("https://api.m.jd.com/client.action?functionId=start&client=android", False),
    ("https://api.m.jd.com/client.action?functionId=welcomeHome", False),
    ("https://ms.jr.jd.com/gw/generic/aladdin/na/m/getLoadingPicture", True),
    ("https://ms.jr.jd.com/gw/generic/aladdin/newna/m/getLoadingPicture", True),
    ("https://ms.jr.jd.com/gw/generic/aladdin/na/m/getHome", False),
    ("https://homefront.qunar.com/front/splash/ad", True),
    ("https://homefront.qunar.com/front/home", False),
    ("https://appconf.mail.163.com/mmad/get.do", True),
    ("https://appconf.mail.163.com/mmad/other", False),
    ("https://api.kkmh.com/v1/ad/show", True),
    ("https://api.kkmh.com/v2/advertisement/list", True),
    ("https://api.kkmh.com/v1/home", False),
    ("https://app.58.com/api/home/advertising/list", True),
    ("https://app.58.com/api/home/appadv/list", True),
    ("https://app.58.com/api/home/feed", False),
    ("https://www.baidu.com/", False),
)

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


RULES = f"""rules:
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
  - DOMAIN-SUFFIX,safebrowsing.googleapis.com,DIRECT
{chr(10).join(f"  - DOMAIN-SUFFIX,{host},REJECT" for host in APP_AD_DOMAINS)}
  - RULE-SET,adblock,REJECT
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
SURGE_WHITELIST = (
    "DOMAIN-SUFFIX,21zhao.com,DIRECT",
    "DOMAIN-SUFFIX,lanxin.cn,DIRECT",
    "DOMAIN-SUFFIX,css.com.cn,DIRECT",
    "DOMAIN-SUFFIX,cec.com.cn,DIRECT",
    "DOMAIN-SUFFIX,safebrowsing.googleapis.com,DIRECT",
)
SURGE_ADBLOCK = (
    "RULE-SET,"
    + ADBLOCK_URL
    + ",REJECT-TINYGIF,no-resolve,update-interval=86400"
)
SURGE_APP_AD_RULES = tuple(
    f"DOMAIN-SUFFIX,{host},REJECT-TINYGIF,no-resolve" for host in APP_AD_DOMAINS
)
SURGE_APP_QUIC = tuple(
    f"AND,((PROTOCOL,QUIC),(DOMAIN,{host})),REJECT-NO-DROP" for host in MITM_HOSTS
)
SURGE_EARLY_RULES = (
    *SURGE_WHITELIST,
    *SURGE_APP_AD_RULES,
    SURGE_ADBLOCK,
    *SURGE_APP_QUIC,
)
SURGE_LATE_RULES = (
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
SURGE_MANAGED_RULES = SURGE_EARLY_RULES + SURGE_LATE_RULES
MARKER_BEGIN = "# personal-proxy-app-ads"
MARKER_END = "# end-personal-proxy-app-ads"
# Plain UDP to the system resolver returns another company's address for these
# names. DoH to 1.1.1.1 over DIRECT times out, so the lookup follows the proxy.
# safebrowsing stays on the system resolver because its rule is DIRECT.
SURGE_DOH = "https://1.1.1.1/dns-query"
DOH_VIA_NY = SURGE_DOH + "#NY"
SURGE_DOH_FOLLOW = "encrypted-dns-follow-outbound-mode = true"
HOST_BEGIN = "# personal-proxy-doh"
HOST_END = "# end-personal-proxy-doh"
DNS_PROXY_SUFFIXES = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "googlevideo.com",
    "ytimg.com",
    "ggpht.com",
    "gstatic.com",
    "googleapis.com",
    "google.com",
    "googleusercontent.com",
)


def is_managed_rule(line: str) -> bool:
    stripped = line.strip()
    if stripped in SURGE_MANAGED_RULES:
        return True
    return stripped.startswith("RULE-SET,") and (
        "AdBlock.list" in stripped or "Advertising_All_No_Resolve.list" in stripped
    )


def ensure_surge_rules(text: str) -> str:
    """Reject ad hostnames before China rules, and keep YouTube names ahead of GEOIP."""
    if SURGE_GENERAL_REJECT not in text:
        if "ipv6 = false" not in text:
            raise SystemExit("surge profile has no ipv6 line to anchor the UDP fallback")
        text = text.replace(
            "ipv6 = false\n",
            "ipv6 = false\n" + SURGE_GENERAL_REJECT + "\n",
            1,
        )
    kept = [line for line in text.splitlines() if not is_managed_rule(line)]
    text = "\n".join(kept)
    if not text.endswith("\n"):
        text += "\n"
    lan = "RULE-SET,LAN,DIRECT,no-resolve"
    if text.count(lan) != 1:
        raise SystemExit("refusing to place adblock without the LAN rule")
    text = text.replace(lan + "\n", lan + "\n" + "\n".join(SURGE_EARLY_RULES) + "\n", 1)
    needle = "GEOIP,CN,DIRECT"
    if text.count(needle) != 1:
        raise SystemExit("refusing to place YouTube rules without exactly one GEOIP line")
    text = text.replace(needle, "\n".join(SURGE_LATE_RULES) + "\n" + needle, 1)
    return ensure_surge_dns(ensure_app_ad_sections(text))


def remove_marked(text: str) -> str:
    pattern = re.compile(
        re.escape(MARKER_BEGIN) + r"\n.*?" + re.escape(MARKER_END) + r"\n?",
        re.S,
    )
    return pattern.sub("", text)


def insert_marked(text: str, section: str, body: str) -> str:
    block = MARKER_BEGIN + "\n" + body.rstrip() + "\n" + MARKER_END + "\n"
    header = f"[{section}]"
    if header not in text:
        if not text.endswith("\n"):
            text += "\n"
        return text + "\n" + header + "\n" + block
    return text.replace(header + "\n", header + "\n" + block, 1)


def ensure_app_ad_sections(text: str) -> str:
    """Rewrite only splash paths. The shared API host itself stays reachable."""
    text = remove_marked(text)
    rewrites = "\n".join(f"{pattern} reject-200" for pattern in SPLASH_REWRITES)
    text = insert_marked(text, "URL Rewrite", rewrites)
    mitm = "hostname = " + ", ".join(MITM_HOSTS) + "\nh2 = true"
    return insert_marked(text, "MITM", mitm)


def remove_block(text: str, begin: str, end: str) -> str:
    pattern = re.compile(re.escape(begin) + r"\n.*?" + re.escape(end) + r"\n?", re.S)
    return pattern.sub("", text)


def surge_host_lines() -> list[str]:
    lines = [
        "safebrowsing.googleapis.com = server:223.5.5.5",
        "*.safebrowsing.googleapis.com = server:223.5.5.5",
    ]
    for suffix in DNS_PROXY_SUFFIXES:
        lines.append(f"{suffix} = server:{SURGE_DOH}")
        lines.append(f"*.{suffix} = server:{SURGE_DOH}")
    return lines


def ensure_surge_dns(text: str) -> str:
    """Resolve poisoned video names with DoH through the proxy. Leave other names alone."""
    if SURGE_DOH_FOLLOW not in text:
        anchor = SURGE_GENERAL_REJECT + "\n"
        if anchor not in text:
            raise SystemExit("surge profile has no UDP fallback line to anchor encrypted DNS")
        text = text.replace(anchor, anchor + SURGE_DOH_FOLLOW + "\n", 1)
    text = remove_block(text, HOST_BEGIN, HOST_END)
    body = HOST_BEGIN + "\n" + "\n".join(surge_host_lines()) + "\n" + HOST_END + "\n"
    header = "[Host]\n"
    if header not in text:
        rewrite = "[URL Rewrite]\n"
        if rewrite not in text:
            raise SystemExit("surge profile has no URL Rewrite section to anchor Host")
        return text.replace(rewrite, "[Host]\n" + body + "\n" + rewrite, 1)
    return text.replace(header, header + body, 1)


def clash_nameserver_policy(indent: str) -> str:
    rows = [
        f"{indent}  'safebrowsing.googleapis.com': '223.5.5.5'",
        f"{indent}  '+.safebrowsing.googleapis.com': '223.5.5.5'",
    ]
    for suffix in DNS_PROXY_SUFFIXES:
        rows.append(f"{indent}  '+.{suffix}': '{DOH_VIA_NY}'")
    return f"{indent}nameserver-policy:\n" + "\n".join(rows) + "\n"


def check_splash_patterns() -> None:
    compiled = [re.compile(pattern) for pattern in SPLASH_REWRITES]
    for url, should_match in SPLASH_CASES:
        matched = any(item.search(url) for item in compiled)
        if matched != should_match:
            raise SystemExit(f"splash pattern mismatch: {url} matched={matched}")
    print(f"CHECK splash-patterns {len(SPLASH_CASES)}")


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
{clash_nameserver_policy("  ")}tun:
  enable: false
{ADBLOCK_PROVIDER}
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
{clash_nameserver_policy("  ")}sniffer:
  enable: true
  force-dns-mapping: true
  parse-pure-ip: true
  override-destination: true
  sniff:
    TLS:
      ports: [443, 8443]
    HTTP:
      ports: [80, 8080-8880]
{ADBLOCK_PROVIDER}
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
            "RULE-SET,adblock,REJECT",
            "DOMAIN-SUFFIX,uve.weibo.com,REJECT",
            "DOMAIN-SUFFIX,splash.goofish.com,REJECT",
            "DOMAIN-SUFFIX,sugar.zhihu.com,REJECT",
            "interval: 86400",
            ADBLOCK_URL,
            "DOMAIN-SUFFIX,safebrowsing.googleapis.com,DIRECT",
            "'safebrowsing.googleapis.com': '223.5.5.5'",
            DOH_VIA_NY,
            "'+.googlevideo.com':",
            "'+.gstatic.com':",
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
        "Advertising_All_No_Resolve.list,REJECT-TINYGIF,no-resolve,update-interval=86400",
        "DOMAIN-SUFFIX,uve.weibo.com,REJECT-TINYGIF,no-resolve",
        "DOMAIN-SUFFIX,splash.goofish.com,REJECT-TINYGIF,no-resolve",
        "DOMAIN-SUFFIX,sugar.zhihu.com,REJECT-TINYGIF,no-resolve",
        "AND,((PROTOCOL,QUIC),(DOMAIN,acs.m.goofish.com)),REJECT-NO-DROP",
        "splash(\\.async)?\\.ads reject-200",
        "functionId=lite_advertising",
        "hostname = " + ", ".join(MITM_HOSTS),
        "h2 = true",
        "DOMAIN-SUFFIX,safebrowsing.googleapis.com,DIRECT",
        "FINAL,Proxy",
        SURGE_DOH_FOLLOW,
        "safebrowsing.googleapis.com = server:223.5.5.5",
        f"googlevideo.com = server:{SURGE_DOH}",
        f"*.gstatic.com = server:{SURGE_DOH}",
        f"*.googleapis.com = server:{SURGE_DOH}",
    ):
        if needle not in surge_text:
            raise SystemExit(f"surge profile missing {needle}")
    if "functionId=start" in surge_text:
        raise SystemExit("surge profile rejects JD startup, not only the ad call")
    proc = subprocess.run([str(SURGE_CLI), "--check", str(SURGE_PATH)], capture_output=True, text=True)
    message = (proc.stdout or "") + (proc.stderr or "")
    for secret in secrets:
        message = message.replace(secret, "<redacted>")
    print(f"CHECK surge {proc.returncode}")
    if proc.returncode != 0:
        print(message[-800:])
        raise SystemExit(proc.returncode)


def enable_surge_https_rewrite() -> None:
    """Turn on URL rewrite. MITM stays off when the local CA has no trust entry."""
    proc = subprocess.run(
        [str(SURGE_CLI), "feature", "set", "rewrite", "on"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        message = ((proc.stdout or "") + (proc.stderr or ""))[-400:]
        raise SystemExit(f"failed to enable rewrite: {message}")
    print("FEATURE rewrite on")
    proc = subprocess.run(
        [str(SURGE_CLI), "feature", "set", "mitm", "on"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("MITM_BLOCKED")
        return
    print("FEATURE mitm on")


def main() -> None:
    check_splash_patterns()
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
    enable_surge_https_rewrite()
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
