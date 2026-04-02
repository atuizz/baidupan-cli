# Python SDK

当前项目的 Python 能力主要通过两种方式接入：

1. 直接调用 CLI：适合脚本、运维任务、其他进程。
2. 调用 HTTP API：适合 SaaS、面板、分发平台、机器人服务。

如果你要在 Python 里嵌入使用，优先建议：

- CLI 场景：调用 `bdpan-cli`
- 服务场景：调用 `/api/v1/*`

当前不单独承诺稳定的“内部 Python API”，因为底层能力仍围绕官方 `bdpan` CLI 和运行时目录组织。
