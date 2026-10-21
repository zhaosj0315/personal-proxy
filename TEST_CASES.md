# 测试用例

每条都能在本机重做。命令里的主机用 `banwa`，不要把地址写进新的文档。服务商不参与这些用例。TC1 的位置和节点是 2026-10-15 那一台纽约机器的结果；换地区以后，改成那台机器自己的位置和节点。

| 编号 | 对应需求 | 步骤 | 通过标准 |
|------|----------|------|----------|
| TC1 | R1 | 系统代理开着时访问 `https://www.cloudflare.com/cdn-cgi/trace` | `loc=US`，`colo=EWR` |
| TC2 | R3 | 用 `www.microsoft.com` 这个名字连到 VPS 的 443 | 证书主体是 `www.microsoft.com`，页面 `200` |
| TC3 | R8 | 浏览器或 curl 打开 `http://` 加这台机器的地址 | 没有网页。80 无数据 |
| TC4 | R8 | 用地址本身做 HTTPS，不改名字 | 证书仍是微软的，HTTP 不是一份自建站 |
| TC5 | R4 | 看 firewalld 和监听 | 目标 `DROP`。公网只有 22 和 `443/tcp`。8388 只在 `127.0.0.1`。nginx、Hysteria 不在运行 |
| TC6 | R4 | 看 sing-box 进程用户和配置形状 | 用户是 `sing-box`。443 是 ShadowTLS 3，严格模式，握手名 `www.microsoft.com`。内层算法是 `2022-blake3-aes-128-gcm`，网络是 TCP |
| TC7 | R2 R6 | `surge-cli rule explain` 看百度、QQ、B 站，以及谷歌、GitHub、YouTube | 国内域名直连。国外域名最终是 NY。`Proxy` 组的选择是 NY |
| TC8 | R6 | `surge-cli rule explain mp.weixin.qq.com servicewechat.com` | 两条都是 DIRECT |
| TC9 | R5 | 手机 Clash 日志，或本机 `geosite.dat` 检索 | `qq.com` 一类走中国域名直连。谷歌、GitHub 走 NY。库里有 `weixin.qq.com` 和 `servicewechat.com` |
| TC10 | R7 | `ssh -o BatchMode=yes banwa` 执行 `hostname` 和 `id -un` | 成功，用户是 root，不提示密码 |
| TC11 | R9 | 对照 Surge 手册和手机旧 Clash 的内核字符串 | 旧 Clash 没有 `shadow-tls`。Surge 不改成 Reality |
| TC12 | R10 | 在本目录执行 `python3 scripts/render_clients.py` | 三行 CHECK 都是 0。`Proxy` 仍是 NY。谷歌最终是 NY。`mp.weixin.qq.com` 仍直连。`banwa` 仍免密。仓库子目录没有这台机器的地址 |
| TC14 | R10 | 在本目录执行 `bash scripts/one_click.sh` | 先打印 `CHECK server 0`，再打印三行客户端 CHECK 为 0。不执行 `install_server.py --apply` |
| TC13 | R2 R6 | `surge-cli rule explain www.youtube.com protocol=QUIC`，再对同一主机用 `protocol=HTTPS`；同样看 `i.ytimg.com`、`fonts.gstatic.com` 和 `www.baidu.com` | YouTube 的 QUIC 命中 `PROTOCOL,QUIC,REJECT-NO-DROP`。YouTube、`i.ytimg.com`、`fonts.gstatic.com` 的 HTTPS 命中域名规则，最终是 NY，不经过 `GEOIP,CN`。百度 QUIC 和 HTTPS 仍是直连 |
| TC15 | R6 R11 | `surge-cli rule explain` 看 `googleads.g.doubleclick.net`、`www.youtube.com`、`www.baidu.com`、`safebrowsing.googleapis.com`。再看 `external-resource list` 和本机每天任务 | 广告域名命中公开名单的 `REJECT-TINYGIF`，并带 `update-interval=86400`。YouTube 仍是 NY。百度和安全浏览仍直连。外部资源状态是 ready。每天任务已加载 |
| TC18 | R12 | `surge-cli rule explain` 看 `wbapp.uve.weibo.com`、`sugar.zhihu.com`、`splash.goofish.com`、`acs.m.goofish.com`、`www.goofish.com`、`www.zhihu.com`。再对闲鱼开屏和 `home.nextfresh` 发 HTTPS。本地用脚本里的 33 条样例对一下正则 | 广告主机名是 `REJECT-TINYGIF`，连接马上失败。`acs.m.goofish.com`、`www.goofish.com`、`www.zhihu.com` 仍直连。开屏样例命中，首页和商品接口不命中。MITM 没打开时，开屏请求仍到达源站 |
| TC19 | R13 | `surge-cli dns lookup` 看 `www.youtube.com`、`redirector.googlevideo.com`、`www.gstatic.com`、`www.baidu.com`、`safebrowsing.googleapis.com`。再 `http probe` 看 YouTube 和百度 | 前三个是 Google 地址段，服务器不是 `223.5.5.5`。百度仍是系统 DNS，首页直连且成功。安全浏览仍直连，仍用系统 DNS。YouTube 的 HTTPS 规则仍是 NY |

失败时先看 `Proxy` 组是不是被改成了 DIRECT，以及 NY 配置里那条 VPS 地址直连还在不在 `FINAL` 前面。
