# 个人代理 · 全流程材料

这是一套个人代理的通用过程。服务商名称不写进过程。2026-10-15 验收的那一台在纽约，出口是 EWR，所以策略名叫 `NY`。换一台 VPS 时，出口城市跟着那台机器走。

机器要满足同一形状：SSH 只用密钥；公网只留 22 和 `443/tcp`；443 是 ShadowTLS v3 严格模式，握手名 `www.microsoft.com`；内层 Shadowsocks 2022 只听 `127.0.0.1` 的 TCP。系统不必是 AlmaLinux，只要能跑 sing-box，防火墙按这个形状收口。本机 SSH 配置里的主机别名 `banwa` 指向哪一台，脚本就读哪一台。

2026-10-17 补上第一次打开国外页面时的 QUIC 立刻拒绝，以及 YouTube、`gstatic`、`googleapis` 在中国 IP 规则前面走代理。公开副本：<https://github.com/zhaosj0315/personal-proxy>。里面没有密码，也没有机器的公网地址。

阅读顺序：`REQUIREMENTS.md` → `DESIGN.md` → `TEST_CASES.md` → `TESTING.md`。

在 21zhao-site 仓库里重新生成本机连接：

```bash
python3 personal-proxy/scripts/render_clients.py
```

单独克隆本目录时：

```bash
python3 scripts/render_clients.py
```

脚本经 `ssh banwa` 读取服务器现网配置。它替换 Surge 里 NY 那一行和那条地址直连，并写上 QUIC 立刻拒绝，以及 YouTube、`gstatic`、`googleapis` 这几条在中国 IP 规则前面走代理。然后写出两份 Clash 文件。密码和地址只落在本机应用目录，脚本拒绝写进本仓库。检查通过后，Surge 文件有变化才 reload。手机文件留在本机，等手机连上再导入。

## 不入库的东西

密码、密钥、订阅令牌、面板口令、公网 IP 都不写在这里。活配置只在本机：

- Surge 配置名 `NY`
- Clash Meta 本机文件 `~/Library/Application Support/Clash/NY.yaml`，权限 `600`
- 手机用的本地文件 `~/Library/Application Support/Clash/NY-android.yaml`，权限 `600`
- 手机 Clash Meta 里的配置名 `NY`
- SSH 主机名 `banwa`，写在 `~/.ssh/config`，别名在 `~/.zshrc`

## 一句话

443 端口用 ShadowTLS v3 伪装成 `www.microsoft.com`。里面是只听本机的 Shadowsocks 2022。国内直连，其余走这台 VPS。浏览器打开那台机器的地址不是网站。

## 边界

这份目录不改 `remote-control/`，不重启站点服务，不把代理指到这台 Mac，也不使用 `21zhao.com` 做伪装。
