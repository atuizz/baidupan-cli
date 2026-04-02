# Architecture / 架构说明

## Chinese / 中文

### 1. 模块边界

- `src/bdpan_wrapper/cli.py`
  负责 CLI 参数解析、配置加载、默认账号解析、命令路由。
- `src/bdpan_wrapper/config.py`
  负责运行时目录、`config.json`、环境变量覆盖逻辑。
- `src/bdpan_wrapper/runtime/builder.py`
  负责装配运行时，把 store、service、adapter 连接起来。
- `src/bdpan_wrapper/accounts/`
  负责账号元数据和账号状态持久化。
- `src/bdpan_wrapper/bdpan/`
  负责官方 `bdpan` CLI 命令调用和输出解析。
- `src/bdpan_wrapper/services.py`
  负责绑定、mkdir、ls、upload-share、transfer-share 主链服务。
- `src/bdpan_wrapper/api/`
  负责 FastAPI 接口、OpenAPI 文档和浏览器测试台。
- `src/bdpan_wrapper/task_store.py`
  负责任务记录持久化。

### 2. 主链调用关系

1. CLI 或 HTTP API 接收请求
2. `runtime/builder.py` 构建运行时
3. service 层校验账号和输入
4. adapter 层调用官方 `bdpan`
5. parser 把 `bdpan` 输出转成结构化结果
6. service 更新任务状态并返回结果

### 3. 账号模型

- 每个账号对应一个独立配置目录
- 账号状态由 `DRAFT / ACTIVE / ERROR` 表达
- 绑定完成后才会进入可用状态

### 4. 为什么保留内部包名 `bdpan_wrapper`

对外仓库名和项目名已经统一为 `baidupan-cli`，但内部 Python 包名暂时保留 `bdpan_wrapper`，原因是：

- 现有代码引用更稳定
- 迁移成本低
- 不影响 CLI 和 GitHub 仓库表达

后续如果要进一步统一，可以单独做一次包名迁移。

### 5. 测试策略

- adapter 测试：验证命令拼装和解析
- service 测试：验证主链状态流转
- api 测试：验证 HTTP 路由和 envelope
- cli 测试：验证命令入口和配置逻辑
- runtime 测试：验证目录初始化和服务装配

### 6. 当前边界

- 核心能力基于官方 `bdpan`
- 仓库保证“结构清晰、主链稳定、接口明确”
- 真实百度侧联调仍依赖本地或服务器环境具备可用 `bdpan`

## English / 英文

### 1. Module boundaries

- `src/bdpan_wrapper/cli.py`
  CLI parsing, config loading, default account resolution, command dispatch.
- `src/bdpan_wrapper/config.py`
  Runtime paths, `config.json`, and environment override logic.
- `src/bdpan_wrapper/runtime/builder.py`
  Runtime composition and service wiring.
- `src/bdpan_wrapper/accounts/`
  Account metadata and account state persistence.
- `src/bdpan_wrapper/bdpan/`
  Official `bdpan` CLI invocation and output parsing.
- `src/bdpan_wrapper/services.py`
  Main-chain operations: bind, mkdir, ls, upload-share, transfer-share.
- `src/bdpan_wrapper/api/`
  FastAPI routes, OpenAPI docs, and browser test console.
- `src/bdpan_wrapper/task_store.py`
  Task persistence.

### 2. Main request flow

1. CLI or HTTP API receives a request
2. `runtime/builder.py` composes the runtime
3. service layer validates account and input
4. adapter layer calls the official `bdpan`
5. parser converts `bdpan` output into structured data
6. service updates task state and returns the result

### 3. Account model

- each account maps to an independent config directory
- account state is represented by `DRAFT / ACTIVE / ERROR`
- an account becomes usable only after bind completion

### 4. Why the internal package name is still `bdpan_wrapper`

The public repository and project name are already aligned to `baidupan-cli`, but the internal Python package name remains `bdpan_wrapper` for now because:

- it keeps current imports stable
- it avoids a larger migration in the first public release
- it does not affect CLI or GitHub-facing expression

If needed, package renaming can be done in a dedicated follow-up change.

### 5. Test strategy

- adapter tests verify command composition and parsing
- service tests verify main-chain state transitions
- api tests verify HTTP routes and response envelopes
- cli tests verify command entrypoints and config behavior
- runtime tests verify directory initialization and runtime wiring

### 6. Current boundary

- core capability depends on the official `bdpan`
- the repository guarantees a clear structure, stable main-chain logic, and explicit interfaces
- real Baidu-side integration still depends on an environment with a working `bdpan`
