# Python Integration

## Chinese / 中文

当前项目的 Python 接入建议分为两类：

1. 脚本型或自动化场景：优先直接调用 `bdpan-cli`
2. 服务集成场景：优先调用 `/api/v1/*`

当前仓库不单独承诺一个稳定的“内部 Python SDK”接口层，因为底层能力仍然围绕官方 `bdpan` CLI 和运行时目录组织。

如果你确实需要在 Python 里嵌入：

- CLI 场景：通过 `subprocess` 调 `bdpan-cli`
- 服务场景：通过 `httpx` / `requests` 调 HTTP API

## English / 英文

Recommended Python integration paths:

1. scripting or automation: call `bdpan-cli`
2. service integration: call `/api/v1/*`

This repository does not currently promise a stable internal Python SDK layer, because the real capability boundary still centers on the official `bdpan` CLI and the runtime directory layout.

If you need Python integration:

- CLI scenario: call `bdpan-cli` via `subprocess`
- service scenario: call the HTTP API via `httpx` or `requests`
