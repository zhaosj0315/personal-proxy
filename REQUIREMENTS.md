# 需求

日期：2026-10-15。范围是一台符合下面形状的 VPS，以及本机 Surge、手机 Clash Meta。服务商不进入需求。验收实例在纽约。

| 编号 | 需求 | 完成标准 |
|------|------|----------|
| R1 | 有一条自己的 VPS 出口 | 经这条线路访问 Cloudflare 的追踪页，位置和节点跟这台机器所在地一致。2026-10-15 那一台是美国，节点 EWR |
| R2 | Mac 用 Surge 能用 | Surge 6.10 能说的协议。当前策略组 `Proxy` 选 NY |
| R3 | 域名隐藏 | 没登录的 TLS 看到 `www.microsoft.com` 的真证书。不用 `21zhao.com` 当伪装名 |
| R4 | 不把密码明文发出去 | 没有公开订阅网址。客户端校验证书，不跳过校验 |
| R5 | 手机 Clash 走同一条 | 旧版 Clash 不会这条协议时，换装会说 ShadowTLS 的 Clash Meta。配置不上传 |
| R6 | 国内直连，国外走这台 VPS | Mac 和手机都按这个原则。微信公众号域名走直连。不在中国名单里的 QUIC 立刻拒绝。`youtube.com`、`youtu.be`、`youtube-nocookie.com`、`googlevideo.com`、`ytimg.com`、`ggpht.com`、`gstatic.com`、`googleapis.com` 在中国 IP 规则前面进策略组 `Proxy`。验收实例里这个组选的是 `NY` |
| R7 | `banwa` 免密直连这台机器 | 只用密钥。这条 SSH 不能再被送进它自己的代理 |
| R8 | 这个地址不是网站 | 80 关闭。浏览器打开 IP 不应当得到一个自建网页 |
| R9 | 不承诺地址永远不被封 | 文档写明残留风险。不为了「多开一个口」去加端口 |
| R10 | 一键重新生成 Surge 和 Clash 连接 | 在本目录执行 `python3 scripts/render_clients.py` 退出 0。在 21zhao-site 仓库里，同一条命令是 `python3 personal-proxy/scripts/render_clients.py`。仓库里没有密码和这台机器的地址。本机两份 Clash 权限是 `600` |

明确不做：

- VLESS Reality。Surge 6.10 没有这个协议。
- 再开一个公网端口。地址被封时，多端口一起断。
- 把 Hysteria 或明文订阅再开起来。
- 为这份材料升站点版本号。
