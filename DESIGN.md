# 设计

对照 `REQUIREMENTS.md`。密码和公网地址不写在这里。

服务商不进入设计。下面「服务器」一节是 2026-10-15 那一台的验收事实：系统 AlmaLinux 9，位置纽约。另一台 VPS 只要形状相同，就沿用同一份生成脚本。形状是：SSH 密钥登录，公网只留 22 和 `443/tcp`，443 为 ShadowTLS v3 严格模式，内层 Shadowsocks 2022 只听本机 TCP。脚本只认 `ssh banwa` 里那个地址，不认是谁卖的这台机器。

## 服务器

验收实例的系统是 AlmaLinux 9，位置纽约，没有全球 IPv6。进程是 sing-box 1.14.3，用户 `sing-box`，不是 root。二进制有 `cap_net_bind_service`，用来听 443。

公网只留两个口，firewalld 区域 `public`，目标 `DROP`，接口是上网网卡，服务 `ssh`，端口 `443/tcp`。nginx 和 Hysteria 保持停止。

入站两层：

1. ShadowTLS v3，严格模式，听 `::` 的 443。握手服务器是 `www.microsoft.com:443`。认证通过后转到下一条。
2. Shadowsocks 2022，算法 `2022-blake3-aes-128-gcm`，只听 `127.0.0.1:8388`，只收 TCP。

没登录的人握手会被转到微软，证书主体是 `www.microsoft.com`。对上密码以后才进入里面的 Shadowsocks。SSH 只接受密钥，密码登录关闭。fail2ban 不在系统源里，没有为它加 EPEL。

## 为什么是这套

先用过 Hysteria。QUIC 的首包就能读出 SNI，域名藏不住，所以停掉。

更抗主动探测的是 VLESS Reality。Surge 6.10 的手册只有 hysteria2、trojan、tuic、snell、shadowsocks、shadow-tls。没有 VLESS。所以 443 留在 Surge 和 Clash 都能说的 ShadowTLS 上。再开一个 Reality 端口不能保住这个地址。

明文 HTTP 订阅会把密码放在链路上，已经撤掉，不再恢复。

## 一键生成

日常入口是 `scripts/one_click.sh`。它先跑 `scripts/check_server.py`，再跑 `scripts/render_clients.py`。在 21zhao-site 仓库里，命令是 `bash personal-proxy/scripts/one_click.sh`。单独克隆这份目录时，命令是 `bash scripts/one_click.sh`。

服务器缺件时用 `python3 scripts/install_server.py --apply`。单元文件是 `scripts/sing-box.service`，密钥登录片段是 `scripts/sshd-key-only.conf`，配置形状样例是 `scripts/config.example.json`。样例里的密码不是真密码。

1. `ssh banwa` 读取 `/etc/sing-box/config.json`。握手名必须是 `www.microsoft.com`，端口 443，ShadowTLS 版本 3，严格模式打开，内层算法是 `2022-blake3-aes-128-gcm`，并且只听 `127.0.0.1` 的 TCP。对不上就退出，不改本机文件。
2. Surge 只替换以 `NY = ss,` 开头的那一行，以及那一条 `/32` 直连。中国名单或 `FINAL,Proxy` 不在，就拒绝写入。UDP 中继写成关闭，因为服务器内层只收 TCP。节点上写 `block-quic=on`。`[General]` 写 `udp-policy-not-supported-behaviour = REJECT`。在 `GEOIP,CN` 前面固定放 `PROTOCOL,QUIC,REJECT-NO-DROP`，以及 `youtube.com`、`youtu.be`、`youtube-nocookie.com`、`googlevideo.com`、`ytimg.com`、`ggpht.com`、`gstatic.com`、`googleapis.com` 进 `Proxy`。QUIC 规则在这些域名规则前面，所以这些名字的 QUIC 会立刻收到拒绝，TCP 才进纽约。
3. 写出 `~/Library/Application Support/Clash/NY.yaml` 和同目录的 `NY-android.yaml`，权限 `600`。路径若落在本仓库里，脚本拒绝写入。
4. Mac 这份混合端口是 `127.0.0.1:17890`，TUN 关闭。手机这份不写混合端口，由 App 自己管 VPN。两边都不写 `skip-cert-verify`。
5. Clash 规则从上到下：私网直连，然后 `21zhao.com`、蓝信、中软、CEC，然后 `.cn`，然后 `GEOSITE,cn`，然后 UDP 443 拒绝，然后 `youtube.com`、`youtu.be`、`youtube-nocookie.com`、`googlevideo.com`、`ytimg.com`、`ggpht.com`、`gstatic.com`、`googleapis.com` 进 `Proxy`，然后中国 IP，剩下进策略组 `Proxy`。Surge 仍用 ChinaMax，脚本不替换那份名单。
6. `mihomo -t` 和 `surge-cli --check` 都通过后，只有 Surge 文件变了才 reload。不启动 Clash 的系统代理，也不和 Surge 同时开 TUN。

## 客户端

Surge 的策略是一条 ShadowTLS v3 的 Shadowsocks，伪装名 `www.microsoft.com`，证书照常校验。策略组 `Proxy` 是手动选择，选项是 NY 和 DIRECT。国外流量进这个组，所以组必须选 NY。选 DIRECT 时，国外也不走纽约。

Clash 用同一条节点。本机文件权限 `600`，本机混合端口只给单独运行时用，TUN 关闭，UDP 关闭，指纹是 Chrome。不和 Surge 同时开系统代理。手机上的 Clash for Android 2.5.12 是旧内核，没有 ShadowTLS，也没有 2022-blake3。手机上装的是 Clash Meta for Android 2.11.35，配置名 `NY`。导入用过一次 USB 转到本机的临时地址，导入后关掉。没有公开链接。

## 分流

Mac 的 NY 配置，从上到下：

1. 这台 VPS 自己的地址 `/32` 直连，避免 SSH 被送进自己的代理。
2. `RULE-SET,LAN` 直连，并加 `no-resolve`。
3. `21zhao.com`、蓝信、中软、CEC，以及 `safebrowsing.googleapis.com` 直连。
4. `RULE-SET` 指向 blackmatrix7 的 `Advertising_All_No_Resolve.list`，策略 `REJECT-TINYGIF`，`no-resolve`，`update-interval=86400`。Surge 自己每 24 小时重新下载，不靠手动跑脚本。Mac 另有一个每天触发的 `external-resource update`。手机 Clash 用同网址的 `rule-providers`，`interval: 86400`，经 `NY` 下载。这一条放在 `.cn` 和中国名单前面。
5. 所有 `.cn` 直连。
6. `ChinaMax_Domain.list`：110800 条后缀、269 个完整域名。来源 blackmatrix7，名单日期 2026-10-14。文件在 Surge 配置目录，不进本仓库。
7. `PROTOCOL,QUIC,REJECT-NO-DROP`。没被中国名单接住的 QUIC 立刻拒绝，浏览器马上改走 TCP，不等 UDP 超时。
8. `youtube.com`、`youtu.be`、`youtube-nocookie.com`、`googlevideo.com`、`ytimg.com`、`ggpht.com`、`gstatic.com`、`googleapis.com` 进 `Proxy`。这几条放在中国 IP 规则前面，污染 DNS 把它们解析成国内地址时也不会改走直连。`gstatic.com` 走直连时会间歇连到污染地址，单次能拖到大约 5 秒。
9. 中国 IP 直连。
10. 其余进策略组 `Proxy`。

手机和 Mac 的 Clash 用同一份规则：私网和上面第 3 步的白名单直连，然后同一份广告域名拒绝，然后 `.cn`、`GEOSITE,cn` 直连，UDP 443 拒绝，然后是上面第 8 步那些 YouTube 域名进 `Proxy`，再是中国 IP，剩下进 `Proxy`。`GEOSITE,cn` 在导入手机时约 112060 条。`weixin.qq.com`、`qq.com`、`servicewechat.com` 在这张表里，公众号域名跟着走直连。Surge 仍是 ChinaMax，两边原则相同，名单来源相同。手机上选中的是会自己更新的那份。再跑一键只重写本机文件。

`21zhao.com` 在 Mac 上还由 21zhao-site 仓库里的 21ZHAO DIRECT 模块直连。这个模块本轮没有改。

## 还在的慢

2026-10-17 量过。不在中国名单里的 QUIC 会立刻拒绝。上面第 8 步那些名字的网页走这台 VPS，不再被污染地址判成直连。

任何一个国外站第一次新建连接，到纽约仍有大约一秒，这是 ShadowTLS 握手。

广告域名走公开名单的 `REJECT-TINYGIF`，每 24 小时更新。`recaptcha.net` 不在这份广告名单里，仍可能直连。YouTube 正片域名 `googlevideo.com` 不在广告名单里，片内广告如果和正片走同一个域名，这份名单拦不住。

## SSH

主机别名 `banwa` 指向这台 VPS 的 22 端口，用户 root，只用 `~/.ssh/id_ed25519`，`IdentitiesOnly`。交互终端里的命令是 `banwa`。当前已经打开的终端要先 `source ~/.zshrc`。

## 浏览器

80 不开放。用 IP 访问 443 时，证书仍是微软的，但页面名字不是 `www.microsoft.com`，对端回 400，浏览器显示没有内容。用微软这个名字去握手里，拿到的是微软自己的页面。这里不挂自建网站。
