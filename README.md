# BaiduPan CLI

第三方百度网盘 CLI / API 封装，底层依赖官方 `bdpan` CLI。  
A third-party Baidu Netdisk CLI / API wrapper built on the official `bdpan` CLI.

本项目不是百度官方 SDK，也不伪装成官方产品。它的目标很明确：把已经验证稳定的官方命令链整理成一个易于集成、易于部署、易于自动化调用的开源项目。  
This project is not an official Baidu SDK and does not pretend to be one. Its goal is narrow and practical: package the stable part of the official command chain into an open source project that is easy to integrate, deploy, and automate.

当前主工作范围明确限制在 `/apps/bdpan`。  
The current supported workspace is intentionally limited to `/apps/bdpan`.

## Chinese / 中文

### 项目定位

- 第三方开源封装，不属于百度官方项目
- 底层依赖官方 `bdpan` CLI
- 一账号一配置目录
- 不暴露 token / cookie
- 不要求接入方自行抓包、逆向网页或维护 cookie

### 当前稳定支持

- 账号绑定
- 登录状态检查
- 目录浏览
- 创建目录
- 上传文件
- 上传后生成分享链接
- 转存公开分享链接

### 当前明确限制

- 主工作范围为 `/apps/bdpan`
- `search` 不进入主链承诺
- 上传后校验建议依赖 `ls` 和 `share`，不要依赖 `search`

### 安装

```bash
git clone https://github.com/atuizz/baidupan-cli.git
cd baidupan-cli
pip install -e .[dev]
```

### 命令入口

```bash
baidupan-cli --help
bdpan-cli --help
bdpan-wrapper --help
```

### 官方 `bdpan` CLI

本项目强依赖官方 `bdpan` CLI。

如果 `bdpan` 不在 `PATH` 中，可以显式指定：

Linux/macOS:

```bash
export BDPAN_BIN=/absolute/path/to/bdpan
```

Windows PowerShell:

```powershell
$env:BDPAN_BIN="C:\path\to\bdpan.exe"
```

### 快速开始

1. 初始化配置文件

```bash
bdpan-cli config init
```

2. 创建绑定会话

```bash
bdpan-cli bind start --name primary
```

返回结果中会包含：

- `account_id`
- `config_path`
- `auth_url`

3. 拿到授权码后完成绑定

```bash
bdpan-cli bind complete --account-id <account_id> --code <auth_code>
```

4. 检查登录状态

```bash
bdpan-cli account user --account-id <account_id>
```

5. 列目录

```bash
bdpan-cli list /apps/bdpan --account-id <account_id>
```

6. 创建目录

```bash
bdpan-cli mkdir /apps/bdpan/releases --account-id <account_id>
```

7. 上传并分享

```bash
bdpan-cli upload ./demo.pdf /apps/bdpan/releases/demo.pdf --account-id <account_id>
```

8. 转存分享链接

```bash
bdpan-cli transfer "https://pan.baidu.com/s/xxxx" /apps/bdpan/inbox/demo --pwd 1234 --account-id <account_id>
```

### 配置文件

默认文件名为 `config.json`：

```json
{
  "BaiduPan": {
    "runtime_home": "~/.bdpan-wrapper",
    "bdpan_bin": "bdpan",
    "default_account_id": ""
  }
}
```

字段说明：

- `runtime_home`: 运行时根目录
- `bdpan_bin`: 官方 `bdpan` 可执行文件路径
- `default_account_id`: 默认账号 ID，省略 `--account-id` 时会优先使用

环境变量优先级高于配置文件：

- `BDPAN_WRAPPER_HOME`
- `BDPAN_BIN`

### HTTP API

当前提供三层协议：

- 旧接口：`/api/*`
- 主接口：`/api/v1/*`
- 兼容接口：`/compat/baidu/*`

建议新接入优先使用 `/api/v1/*`。

统一响应结构示例：

```json
{
  "success": true,
  "code": 0,
  "message": "ok",
  "request_id": "xxxx",
  "data": {}
}
```

核心接口：

- `GET /api/v1/system/status`
- `GET /api/v1/accounts`
- `GET /api/v1/tasks`
- `POST /api/v1/accounts/bind/start`
- `POST /api/v1/accounts/bind/complete`
- `POST /api/v1/accounts/{account_id}/check`
- `POST /api/v1/files/list`
- `POST /api/v1/files/mkdir`
- `POST /api/v1/files/upload-share`
- `POST /api/v1/files/browser-upload-share`
- `POST /api/v1/shares/transfer`

兼容接口：

- `GET /compat/baidu/list`
- `POST /compat/baidu/mkdir`
- `GET /compat/baidu/transfer`
- `POST /compat/baidu/transfer`
- `POST /compat/baidu/upload-share`

### 文档与浏览器测试台

启动 API 服务后可直接打开：

- `/`
- `/portal`
- `/docs`
- `/redoc`

### 仓库结构

```text
.github/
  workflows/
    ci.yml
cmd/
  bdpan-cli.py
deploy/
  gcp/
docs/
  ARCHITECTURE.md
sdk/
  python/
    README.md
src/
  bdpan_wrapper/
    accounts/
    api/
    bdpan/
    runtime/
    cli.py
tests/
  test_api.py
  test_bdpan_adapter.py
  test_cli.py
  test_runtime.py
  test_services.py
```

模块职责：

- `accounts/`: 账号元数据与持久化
- `bdpan/`: 官方 `bdpan` CLI 适配层与输出解析
- `services.py`: 绑定、mkdir、ls、upload-share、transfer-share 主链服务
- `runtime/`: 运行时装配和目录初始化
- `api/`: FastAPI、OpenAPI 和浏览器测试台
- `tests/`: 以假适配器和假运行时覆盖主链逻辑

### 验证现状

当前仓库已覆盖这些验证：

- CLI 帮助可正常输出
- 配置文件初始化可正常生成
- 绑定服务主链已由 service 测试覆盖
- mkdir / ls / upload-share / transfer-share 已由 service / api / adapter 测试覆盖
- API 门户页和主要接口由测试覆盖

已知边界：

- 真实百度侧联调依赖本机或服务器已安装可用的官方 `bdpan`
- 当前测试以 fake adapter / fake runtime 为主，用于保证开源仓库结构和主链逻辑稳定

### 免责声明

本项目是第三方开源封装，仅用于学习、自动化和合法合规的业务集成。

你需要自行确认：

- 账号使用符合百度网盘服务条款
- 部署、分享、分发行为符合当地法律法规
- 生产环境已做好权限控制、隔离和审计

## English / 英文

### Project Positioning

- third-party open source wrapper, not an official Baidu project
- built on the official `bdpan` CLI
- one account maps to one config directory
- does not expose token or cookie handling
- does not require packet capture, web reverse engineering, or manual cookie maintenance

### Stable Features

- account bind
- login state check
- directory listing
- directory creation
- file upload
- upload then create share link
- transfer a public share link

### Explicit Limitations

- primary working scope is `/apps/bdpan`
- `search` is excluded from the main support contract
- upload verification should rely on `ls` and `share`, not `search`

### Installation

```bash
git clone https://github.com/atuizz/baidupan-cli.git
cd baidupan-cli
pip install -e .[dev]
```

### Command Entrypoints

```bash
baidupan-cli --help
bdpan-cli --help
bdpan-wrapper --help
```

### Official `bdpan` CLI

This project strongly depends on the official `bdpan` CLI.

If `bdpan` is not in `PATH`, set it explicitly:

Linux/macOS:

```bash
export BDPAN_BIN=/absolute/path/to/bdpan
```

Windows PowerShell:

```powershell
$env:BDPAN_BIN="C:\path\to\bdpan.exe"
```

### Quick Start

1. Create a config file

```bash
bdpan-cli config init
```

2. Start an account bind session

```bash
bdpan-cli bind start --name primary
```

The result includes:

- `account_id`
- `config_path`
- `auth_url`

3. Complete bind with the auth code

```bash
bdpan-cli bind complete --account-id <account_id> --code <auth_code>
```

4. Check account login state

```bash
bdpan-cli account user --account-id <account_id>
```

5. List a directory

```bash
bdpan-cli list /apps/bdpan --account-id <account_id>
```

6. Create a directory

```bash
bdpan-cli mkdir /apps/bdpan/releases --account-id <account_id>
```

7. Upload and share

```bash
bdpan-cli upload ./demo.pdf /apps/bdpan/releases/demo.pdf --account-id <account_id>
```

8. Transfer a public share

```bash
bdpan-cli transfer "https://pan.baidu.com/s/xxxx" /apps/bdpan/inbox/demo --pwd 1234 --account-id <account_id>
```

### Config File

Default file name: `config.json`

```json
{
  "BaiduPan": {
    "runtime_home": "~/.bdpan-wrapper",
    "bdpan_bin": "bdpan",
    "default_account_id": ""
  }
}
```

Fields:

- `runtime_home`: runtime root directory
- `bdpan_bin`: path to the official `bdpan` executable
- `default_account_id`: default account ID used when `--account-id` is omitted

Environment variables override config values:

- `BDPAN_WRAPPER_HOME`
- `BDPAN_BIN`

### HTTP API

Three protocol layers are available:

- legacy endpoints: `/api/*`
- primary endpoints: `/api/v1/*`
- compatibility endpoints: `/compat/baidu/*`

Recommended for new integrations: `/api/v1/*`

Unified response envelope example:

```json
{
  "success": true,
  "code": 0,
  "message": "ok",
  "request_id": "xxxx",
  "data": {}
}
```

Core endpoints:

- `GET /api/v1/system/status`
- `GET /api/v1/accounts`
- `GET /api/v1/tasks`
- `POST /api/v1/accounts/bind/start`
- `POST /api/v1/accounts/bind/complete`
- `POST /api/v1/accounts/{account_id}/check`
- `POST /api/v1/files/list`
- `POST /api/v1/files/mkdir`
- `POST /api/v1/files/upload-share`
- `POST /api/v1/files/browser-upload-share`
- `POST /api/v1/shares/transfer`

Compatibility endpoints:

- `GET /compat/baidu/list`
- `POST /compat/baidu/mkdir`
- `GET /compat/baidu/transfer`
- `POST /compat/baidu/transfer`
- `POST /compat/baidu/upload-share`

### Docs and Browser Test Console

After starting the API server, open:

- `/`
- `/portal`
- `/docs`
- `/redoc`

### Repository Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a bilingual breakdown of module boundaries, runtime wiring, and request flow.

### Validation Status

The repository currently verifies:

- CLI help output
- config initialization
- bind flow at the service layer
- mkdir / ls / upload-share / transfer-share at service, adapter, and API layers
- portal page and primary API routes

Known boundary:

- real Baidu-side verification still depends on an environment with a working official `bdpan`
- most tests use fake adapters and fake runtimes to guarantee repository structure and main-chain behavior

### Disclaimer

This is a third-party open source wrapper for learning, automation, and legitimate service integration.

You are responsible for ensuring:

- your account usage complies with Baidu Netdisk terms
- your deployment and sharing flows comply with local law and policy
- your production environment has proper isolation, audit, and access control

## License

MIT
