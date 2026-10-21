# 验收记录

日期：2026-10-15。下面是当天已经做过的结果。没有把密码和公网地址抄进来。

| 用例 | 结果 |
|------|------|
| TC1 | Cloudflare 追踪是 `loc=US`，`colo=EWR`，TLS 1.3。Mac 经 Surge，以及本机 mihomo 1.19.30 经这份节点，都是这个结果 |
| TC2 | 用微软的名字连 443，证书主体 `www.microsoft.com`，签发者是 Microsoft TLS G2。HTTP/2 `200`，正文约 201 KB |
| TC3 | `http://` 加地址：TCP 后 8 秒 0 字节，然后超时 |
| TC4 | `https://` 加地址本身：TLS 1.3，证书仍是 `www.microsoft.com`，接着是 HTTP/1.0 `400`，正文 312 字节。浏览器因此显示没有内容 |
| TC5 | 2026-10-15 再次登录查看：`sing-box` 听 `*:443` 和 `127.0.0.1:8388`。sshd 听 22。firewalld 目标 `DROP`，服务 ssh，端口 `443/tcp`。`sing-box` 与 firewalld 为 active。nginx、Hysteria 为 inactive |
| TC6 | 配置形状：ShadowTLS 版本 3，`strict_mode` 为真，握手服务器 `www.microsoft.com`，转到内层。内层 `127.0.0.1:8388`，TCP，`2022-blake3-aes-128-gcm`。进程用户是 `sing-box`，pid 1689 |
| TC7 | `surge-cli --check` 通过并已 reload。百度、QQ、淘宝、微信、B 站、京东、知乎、微博、网易、抖音、美团、小米、华为、携程命中 ChinaMax 直连。`12306.cn`、`people.com.cn` 命中 `.cn`。谷歌、GitHub、YouTube、维基百科、Netflix、OpenAI、Telegram、X 的最终策略是 NY。`policy-group get Proxy` 的选择是 NY |
| TC8 | `mp.weixin.qq.com`、`servicewechat.com`、`res.wx.qq.com`、`myqcloud.com`、`qcloud.com`、`wxapp.tc.qq.com` 都是 DIRECT。实连公众号首页：连接 3.6 毫秒，首字节 219 毫秒，总共 251 毫秒，`200`。同一时刻百度总共 77 毫秒。连接时间说明没有绕纽约 |
| TC9 | 手机当时在线。Clash Meta `2.11.35` 配置 NY 处于运行。日志里 `qq.com`、百度按 GeoSite cn 直连，谷歌和 GitHub 走 Proxy NY。后来手机拔线。本机 `geosite.dat` 含 `weixin.qq.com`、`qq.com`、`servicewechat.com`、`qpic.cn`、`myqcloud.com`、`qcloud.la`，不含单独的 `mp.weixin.qq.com` 字符串，子域名跟着 `weixin.qq.com` |
| TC10 | `ssh -o BatchMode=yes banwa` 退出 0。用户 root。主机名与面板一致。新终端的别名是 `banwa=ssh banwa` |
| TC11 | 手机旧包 `com.github.kr328.clash.foss` 2.5.12 的 `libclash.so` 没有 `shadow-tls`，也没有 `2022-blake3`。Clash Meta 的库里有 `shadow-tls`。安装包 sha256 `af7f05d8801798a8e75de682e5f67070138becb8623b7a341c3e5cd042a3753d`，与 GitHub 上 `v2.11.35` 的 arm64 发布记录一致 |
| TC12 | 2026-10-15 再跑 `render_clients.py`，退出 0。`NY.yaml`、`NY-android.yaml`、Surge 三行 CHECK 都是 0，Surge 已 reload。`policy-group get Proxy` 仍是 NY。谷歌命中 `FINAL,Proxy` 到 NY。`mp.weixin.qq.com` 和百度命中 ChinaMax 直连。Cloudflare 追踪仍是 `loc=US`、`colo=EWR`。`banwa` 退出 0，用户 root。两份 Clash 权限 `600`。Mac 这份补上 `GEOSITE,cn`。Surge 的 UDP 中继改为关闭，与服务器只收 TCP 一致。手机当时没连着，`NY-android.yaml` 只留在本机，没有导入。仓库子目录没有这台机器的地址。没有打开 Clash 的系统代理 |
| TC13 | 2026-10-17 跑 `render_clients.py`，三行 CHECK 为 0，Surge 已 reload。`www.youtube.com` 与 `fonts.gstatic.com` 的 QUIC 命中 `PROTOCOL,QUIC,REJECT-NO-DROP`（0.2–0.6 毫秒）。两者的 HTTPS 命中域名规则，最终 NY。`i.ytimg.com` 同样是 NY。百度 QUIC 和 HTTPS 仍是 ChinaMax 直连，首页总共 63 毫秒。`fonts.gstatic.com` 连续两次 1.26 秒、1.02 秒，不再出现直连污染地址时的大约 5 秒。YouTube 首页 949744 字节，首字节 1.03 秒，总共 2.26 秒，大约每秒 420 KB。手机 Clash 文件已写在本机，没有导入 |

| TC14 | 2026-10-17 `bash scripts/one_click.sh` 退出 0。先是 `CHECK server 0`，然后 Clash 两份和 Surge 的 CHECK 都是 0。Surge 文件没有变化，所以没有 reload。没有执行 `install_server.py --apply` |
| TC15 | 2026-10-17 广告名单 289521 条域名规则写入 Surge 配置目录的 `AdBlock.list`，不进仓库。Surge 已 reload。`googleads.g.doubleclick.net`、`googlesyndication.com`、`s2.youtube.com` 命中 `REJECT-TINYGIF`。对 `googleads.g.doubleclick.net` 的连接在 0.012 秒失败。`www.youtube.com` 仍是 NY，首页 `200`。百度仍直连，总共 0.061 秒。`safebrowsing.googleapis.com` 和 `mp.weixin.qq.com` 仍直连。手机 USB 已连接。Clash Meta `2.11.35` 里会自己更新广告名单的那份 `NY` 已选中，时间是刚才。临时地址已关掉。更早的一份 `NY` 仍在列表里，没有选中 |

| TC16 | 2026-10-17 全流程再验。`py_compile` 通过，安装脚本的远端片段能编译。密钥和公网地址扫描没有命中。`bash scripts/one_click.sh` 退出 0：`CHECK server 0`，Clash 两份和 Surge 的 CHECK 都是 0，Surge 未改所以没有 reload，打印 `ADBLOCK_SCHEDULE 86400`。`Proxy` 仍是 NY。百度、`mp.weixin.qq.com`、`safebrowsing.googleapis.com` 直连。`www.youtube.com` 的 QUIC 是 `REJECT-NO-DROP`，HTTPS 是 NY。`fonts.gstatic.com` 是 NY。`github.com` 最终是 NY。`googleads.g.doubleclick.net` 命中公开名单 `REJECT-TINYGIF`，带 `update-interval=86400`。外部资源状态 ready，更新时间 `2026-10-17 12:29:24 +08:00`。每天任务 `com.21zhao.personal-proxy.adblock` 已加载，`runs = 1`。两份 Clash 权限 `600`。百度首页 `200`，0.056 秒。广告域名 0.007 秒断开。YouTube 首页 `200`，首字节 1.995 秒，总共 3.850 秒。没有执行 `install_server.py --apply`。没有跑全仓 pytest |

没有跑全仓 `pytest`。这一轮不改站点业务代码，也不改 `remote-control/`。不升 `version.json`。

| TC17 | 2026-10-17 21:48 带宽对照。服务器负载 0.00，拥塞控制是 `bbr`，队列 `fq`，`tcp_bbr` 挂着 657 个连接，写在 `/etc/sysctl.conf`。服务器在美国本地拉 Cloudflare 20MB，速度每秒 153846153 字节，首字节 0.043 秒。同一时刻客户端走代理 15 秒收到 2080768 字节，速度每秒 138661 字节，首字节 1.604 秒。`test-policy NY` 的 RTT 是 967 毫秒。没有改拥塞控制，没有执行 `install_server.py --apply` |

| TC18 | 2026-10-21 改规则前：`acs.m.goofish.com`、`g-acs.m.goofish.com`、`sugar.zhihu.com`、`wbapp.uve.weibo.com`、`splash.jd.com`、`splash.xiaohongshu.com`、`splash.pinduoduo.com` 都是中国名单或 `.cn` 直连。`googleads.g.doubleclick.net`、`tanx.com`、`open.e.kuaishou.com`、`pangolin-sdk-toutiao.com` 已是公开名单 `REJECT-TINYGIF`。对 `https://acs.m.goofish.com/gw/mtop.taobao.idlecommerce.splash.async.ads/1.0/` 的请求 0.085 秒返回 HTTP 200，正文里的 `api` 是 `mtop.taobao.idlecommerce.splash.async.ads`。改规则后 `render_clients.py` 的 CHECK 为 0，Surge 已 reload。33 条路径样例通过。`wbapp.uve.weibo.com`、`sugar.zhihu.com`、`splash.goofish.com`、`splash.jd.com`、`ads.xiaohongshu.com`、`jad-api.jin10.com` 命中 `REJECT-TINYGIF`。实连 `sugar.zhihu.com` 0.011 秒、`splash.goofish.com` 0.007 秒、`wbapp.uve.weibo.com` 0.007 秒，TLS 被断开。百度首页仍 200，0.088 秒。YouTube 响应头 200，1.205 秒，规则仍是 NY。`www.zhihu.com`、`www.goofish.com`、`h5.m.goofish.com`、`acs.m.goofish.com`、`acs.m.taobao.com`、`app.bilibili.com` 仍直连。`acs.m.goofish.com` 的 QUIC 是 `REJECT-NO-DROP`，HTTPS 仍直连。系统钥匙串里的 Surge CA 信任项数量是 0，`feature set mitm on` 失败，打印 `MITM_BLOCKED`。因此开屏路径改写还没套到活连接上，同一条闲鱼开屏在改完后仍返回源站 JSON。`home.nextfresh` 也仍到达源站。手机 `adb devices` 为空，`NY-android.yaml` 已写入，没有导入。没有执行 `install_server.py --apply`。没有跑全仓 pytest |

残留：ShadowTLS 仍有公开的探测研究。一台促销机的地址以后仍可能被封。面板 root 口令如果还没在服务商面板里改掉，应只在面板里改，不要写进仓库。第一次连上这台 VPS 仍大约一秒。YouTube 正片和片内广告若走同一个 `googlevideo.com`，广告名单拦不住。回程变慢时，播放会转圈。闲鱼开屏在 `acs.m.goofish.com` 的路径上，本机 Surge CA 还没有信任项，MITM 没打开，这条改写还没生效。手机 Clash 导入新文件之前，也还在用 2026-10-17 那一版。
