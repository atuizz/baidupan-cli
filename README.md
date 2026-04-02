# BaiduPan CLI

Third-party Baidu Netdisk CLI and API wrapper built on the official `bdpan` CLI.

This project is not an official Baidu SDK and does not pretend to be one. Its goal is pragmatic: provide a clean CLI and service layer for the stable part of the official `bdpan` command chain, without asking users to maintain cookies, reverse engineer the web app, or handle tokens themselves.

The current supported workspace is intentionally limited to `/apps/bdpan`.

## Open Source Scope

This repository includes:

- a Python package
- a CLI tool
- an optional HTTP API
- OpenAPI docs
- a browser test console

Core rules:

- depends on the official `bdpan` CLI
- one account maps to one config directory
- does not expose token or cookie handling
- prioritizes stable operations over broad coverage

## Supported Features

Primary supported operations:

- account bind
- login state check
- directory listing
- directory creation
- file upload
- file share
- share transfer

Not in the main support contract:

- `search`

Reason:

- `search` is not reliable enough under `/apps/bdpan`
- upload verification should rely on `ls` and `share`, not `search`

## Requirements

- Python 3.10+
- Linux, macOS, or Windows
- official `bdpan` CLI installed and working
- a valid Baidu Netdisk account

## Project Layout

```text
.github/
  workflows/
    ci.yml
cmd/
  bdpan-cli.py
deploy/
  gcp/
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
  test_services.py
```

## Installation

```bash
git clone https://github.com/atuizz/baidupan-cli.git
cd baidupan-cli
pip install -e .[dev]
```

Available commands:

```bash
baidupan-cli --help
bdpan-cli --help
bdpan-wrapper --help
```

## Official `bdpan` CLI

This project strongly depends on the official `bdpan` CLI.

If `bdpan` is not in `PATH`, set it explicitly.

Linux/macOS:

```bash
export BDPAN_BIN=/absolute/path/to/bdpan
```

Windows PowerShell:

```powershell
$env:BDPAN_BIN="C:\path\to\bdpan.exe"
```

## Quick Start

### 1. Create a config file

```bash
bdpan-cli config init
```

This writes `config.json` in the current directory by default.

### 2. Start account bind

```bash
bdpan-cli bind start --name primary
```

The result includes:

- `account_id`
- `config_path`
- `auth_url`

### 3. Complete account bind

```bash
bdpan-cli bind complete --account-id <account_id> --code <auth_code>
```

### 4. Check login state

```bash
bdpan-cli account user --account-id <account_id>
```

### 5. List a directory

```bash
bdpan-cli list /apps/bdpan
```

### 6. Upload and share

```bash
bdpan-cli upload ./demo.pdf /apps/bdpan/releases/demo.pdf --account-id <account_id>
```

### 7. Transfer a public share

```bash
bdpan-cli transfer "https://pan.baidu.com/s/xxxx" /apps/bdpan/inbox/demo --pwd 1234 --account-id <account_id>
```

## Config File

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
- `default_account_id`: default account used when `--account-id` is omitted

Environment variables override config values:

- `BDPAN_WRAPPER_HOME`
- `BDPAN_BIN`

## CLI Usage

Basic form:

```bash
bdpan-cli -c config.json <command> [arguments...]
```

Config:

```bash
bdpan-cli config init
bdpan-cli config init --force
```

Accounts:

```bash
bdpan-cli account list
bdpan-cli account user --account-id <account_id>
```

Bind:

```bash
bdpan-cli bind start --name primary
bdpan-cli bind complete --account-id <account_id> --code <auth_code>
```

Files:

```bash
bdpan-cli list /apps/bdpan --account-id <account_id>
bdpan-cli mkdir /apps/bdpan/releases --account-id <account_id>
bdpan-cli upload ./demo.pdf /apps/bdpan/releases/demo.pdf --account-id <account_id>
bdpan-cli transfer "https://pan.baidu.com/s/xxxx" /apps/bdpan/inbox/demo --pwd 1234 --account-id <account_id>
```

API service:

```bash
bdpan-cli api serve --host 127.0.0.1 --port 8787
```

## HTTP API

Available protocol layers:

- legacy endpoints: `/api/*`
- primary REST endpoints: `/api/v1/*`
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

## Docs and Test Console

After starting the API server, open:

- `/`
- `/portal`
- `/docs`
- `/redoc`

## Notes

- this project depends on the official `bdpan` CLI and does not attempt to bypass official auth flows
- one account should use one config directory
- the primary working scope is `/apps/bdpan`
- relative paths are preferred when possible
- verify uploads with `ls` or share results, not `search`
- `search` is intentionally excluded from the stable path

## Disclaimer

This is a third-party open source wrapper for learning, automation, and legitimate service integration.

You are responsible for making sure:

- your account usage complies with Baidu Netdisk terms
- your deployment and sharing flows comply with local law and policy
- your production environment has proper isolation, audit, and access control

## License

MIT
