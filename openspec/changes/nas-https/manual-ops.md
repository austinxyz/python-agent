# nas-https Group 1 — 手动 Ops 清单

> `tasks.md` 第 1 组的 1.1 → 1.8 全是要在浏览器 / NAS shell / Google Cloud Console 操作的事，agent 没法代做。
> 把这个文件当 checklist 一步步过，跑完把 `TAILNET_NAME` + `GOOGLE_CLIENT_ID` 两个值发到对话里，agent 从 Group 2 接着做。
>
> **预计时间** 30-45 分钟。
> **NAS 情况说明：** UGREEN UGOS App Center **没有 Tailscale 应用**，所以走 Docker 容器部署（步骤 1.3）。

---

## 1.1 注册 Tailscale + 拿 tailnet 名字

1. 浏览器打开 https://login.tailscale.com/start
2. 点 "Sign up with Google" → 用 `austin.xyz@gmail.com`（这个账号是 tailnet 的 owner）
3. 进 admin 控制台后，看页面上的 **tailnet 名字**：
   - 路径：https://login.tailscale.com/admin/dns → 顶上一行写着 `<something>.ts.net`
   - `<something>` 一般是 `tail-abc123` 或 `taildogfish` 之类随机字符串

**✅ 完成标志：** 记下这个 tailnet 名（= `TAILNET_NAME`），比如 `tail-abc123`。NAS 最终的 URL 会是 `python-agent.<TAILNET_NAME>.ts.net`。

tail67f33e.ts.net
---

## 1.2 验证 free 档够用

1. admin 控制台 → Settings → Subscription
2. 看 "Personal" plan 限制：
   - **Devices**: 100（够爆）
   - **Users**: 3（够 2 个 admin + 几个家人）

**家人加入方式**有两种 —— 选一种现在就定：

- **(i) 各自独立 Tailscale 账号**（每人用自己 Google 登）—— 占用 user 数。你 + bucolic = 2 users，留 1 个余量。**推荐这条，权限独立**。
- **(ii) 共用一个 Tailscale 账号**（家人都登 admin 的）—— 1 user 多设备。简单粗暴。

**✅ 完成标志：** 决定哪种模式 + 确认 user 数够用。选 (i) 后超 3 个就要付费（$6/user/月）或回退到 (ii)。

---

## 1.3 NAS 上装 Tailscale（Docker 路径）

UGOS App Center 没收录 Tailscale，走 Docker 部署。

### 1.3.a 建 host 数据目录

NAS 上找一个稳定的数据目录（重启后保留），用 UGOS 文件管理器或 Docker 项目目录：

```
/volume1/docker/tailscale/
```

UGOS 文件管理器里新建这个文件夹。

### 1.3.b 在 UGOS Docker UI 创建容器

UGOS → Docker → "Container" → "Create"：

| 字段 | 值 |
|---|---|
| Image | `tailscale/tailscale:stable` |
| Container name | `tailscale` |
| Restart policy | `unless-stopped` |
| Network | **Host**（不是 bridge —— 重要） |

**Capabilities（点 "Advanced" 或 "Privileges"）：**
- 勾上 `NET_ADMIN`
- 勾上 `NET_RAW`

**Devices：**
- Host path: `/dev/net/tun` → Container path: `/dev/net/tun`

**Volumes（bind mount）：**
- Host path: `/volume1/docker/tailscale` → Container path: `/var/lib/tailscale`

**Environment variables：**
- `TS_STATE_DIR=/var/lib/tailscale`
- `TS_HOSTNAME=python-agent`
- `TS_USERSPACE=false`

点 Create + Start。

### 1.3.c 验证守护起来了

UGOS Docker → 选 `tailscale` 容器 → Logs，应该看到类似：

```
Backend: logs: in state Stopped, NeedsLogin
Backend: logs: in state NeedsLogin
```

"NeedsLogin" 是正常的 —— 1.4 解决。

**✅ 完成标志：** 容器状态 Running + logs 显示 "NeedsLogin"。

---

## 1.4 NAS 加入 tailnet

UGOS Docker → 选 `tailscale` 容器 → "Terminal" / "Exec"（不同 UGOS 版本叫法不同）→ 输入：

```bash
tailscale up
```

会打印一行 `https://login.tailscale.com/a/xxxxxxxxxx`。**复制这个 URL，在已经登录 Tailscale 的浏览器**（1.1 那个）打开 → 点 "Connect"。

回到容器 Terminal 跑：

```bash
tailscale status
```

应该看到 NAS 自己在列表里，机器名 `python-agent`，IP 形如 `100.x.x.x`。

**✅ 完成标志：** `tailscale status` 列表里 `python-agent` 有 `100.x.x.x` IP。

---

## 1.5 开 HTTPS Certificates 功能

1. 浏览器回到 admin 控制台 → DNS（左边导航）
2. 翻到底部 "HTTPS Certificates" 区块
3. 点 **Enable HTTPS** 按钮，确认

**✅ 完成标志：** 那一区显示 "HTTPS is enabled for your tailnet"。

---

## 1.6 给 NAS 签证书

回到容器 Terminal 跑：

```bash
tailscale cert python-agent.<TAILNET_NAME>.ts.net
```

`<TAILNET_NAME>` 替换成 1.1 拿到的名字（**不带 `.ts.net`**，比如 `tail-abc123`）。

第一次签需要 30-60 秒（DNS-01 challenge）。完成后打印：

```
Wrote public cert to python-agent.<TAILNET_NAME>.ts.net.crt
Wrote private key to python-agent.<TAILNET_NAME>.ts.net.key
```

**✅ 完成标志：** 容器里跑 `ls /var/lib/tailscale/certs/` 看到两个文件（`.crt` 和 `.key`）。

**也就是 host 上的 `/volume1/docker/tailscale/certs/` 也有这两个文件**（因为是 bind mount）—— 后端容器读 cert 状态时会用这个路径。

---

## 1.7 Google OAuth client

1. 浏览器打开 https://console.cloud.google.com/apis/credentials
2. 选一个 project（没有就 New Project → 起名 `python-agent`）
3. 左边 → "OAuth consent screen"：
   - User Type: **External**
   - App name: `python-agent`
   - User support email: 你的 Gmail
   - App domain：跳过
   - Authorized domains: `ts.net`
   - Developer contact: 你的 Gmail
   - Save and Continue → Scopes 全跳过 → Test users 先跳过 → Save
4. 左边 → "Credentials" → "+ CREATE CREDENTIALS" → "OAuth client ID"：
   - Application type: **Web application**
   - Name: `python-agent NAS`
   - Authorized JavaScript origins: `https://python-agent.<TAILNET_NAME>.ts.net`
   - Authorized redirect URIs: `https://python-agent.<TAILNET_NAME>.ts.net`（同一个 URL，没有路径后缀）
   - Create

弹出对话框给两个值：
- **Client ID** 形如 `123456789-abcdefg.apps.googleusercontent.com` ← **这就是 `GOOGLE_CLIENT_ID`**
- **Client secret** —— **不用复制**，Google Identity Services 走前端纯 JS 流程，不用 secret

**✅ 完成标志：** 记下 `GOOGLE_CLIENT_ID`。

---

## 1.8 把家人加为 Test users

1. console.cloud.google.com → APIs & Services → "OAuth consent screen"
2. 翻到 "Test users" 区块 → "+ ADD USERS"
3. 加 `austin.xyz@gmail.com` 和 `bucolic.xyz@gmail.com`
4. Save

App 状态保持 "Testing"，**不要点 "Publish to production"**。

**✅ 完成标志：** Test users 列表里有家人的 email。

---

## 跑完后回报

回到对话一行说：

```
TAILNET_NAME=tail-abc123
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
```

（实际值替换）。

我收下这两个值，从 Group 2 接着做（写后端 `/api/admin/cert-status` + `@require_admin` 装饰器 + 测试 + code review）。

注：以后 Group 5 部署阶段，**`tailscale serve` 命令也要在容器里跑**：

```bash
docker exec tailscale tailscale serve --https=443 http://localhost:8910
```

因为 `--network=host`，容器内的 `tailscale serve` 看得到 host 上的 `localhost:8910`（python-agent-dev-frontend 容器映射的端口）。这条不用现在做，记一下 Group 5 时候要用。

---

## 卡点应对

| 卡点 | 怎么办 |
|---|---|
| Docker 启不来，报 `/dev/net/tun: no such file` | NAS host 没加载 tun 模块；先在 NAS 启动脚本里 `modprobe tun`，或者 1.3 容器环境变量加 `TS_USERSPACE=true`（不用 tun 设备，性能稍降但够用） |
| `tailscale up` 在容器里跑没反应 / 卡住 | 容器没用 host network；回 1.3.b 检查 Network 是不是 Host 不是 Bridge |
| `tailscale cert` 一直 pending / 超时 | 1.5 那个 HTTPS Certificates toggle 没开成；admin 控制台再开一次，等 1 分钟再 retry 1.6 |
| OAuth consent screen 报错 "Authorized domain not allowed" | 1.7 第 3 步的 `Authorized domains` 写 `ts.net`（不带前缀）；如果还报错，跳过这一栏 |
| Google 一直跳 "App not verified" | 1.8 没把 email 加成 Test user，或加错了 |
| 家人 Google 账号 console.cloud 看不到东西 | 正常，OAuth client 只对 Test users 列表里的 email 开放 |
| 签出来的证书过期了 | Tailscale daemon 自动 renew，到期前 30 天会重签；手动强 renew 跑 `docker exec tailscale tailscale cert --force python-agent.<TAILNET_NAME>.ts.net` |
| Docker 容器重启后 tailscale 没自动起 | 1.3.b Restart policy 选了 `unless-stopped` 应该会自动。如果没起，UGOS Docker 界面手动 Start |
