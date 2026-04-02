## Current Stage
- Goal: reshape the repo into a CLI-first Baidu Netdisk project, benchmarked against the structure/readme style of `kuake_cli`.
- Completed:
  - Reworked the CLI entry in `src/bdpan_wrapper/cli.py`.
  - Added a proper config file workflow:
    - `bdpan-cli config init`
    - `config.json` support
    - runtime_home / bdpan_bin / default_account_id fields
  - Added simpler CLI command groups:
    - `config`
    - `account`
    - `bind`
    - `list`
    - `mkdir`
    - `upload`
    - `transfer`
    - `api`
  - Kept compatibility for legacy command names through argv normalization without exposing them in help.
  - Added an additional console script entry: `bdpan-cli`.
  - Added CLI-facing top-level structure:
    - `cmd/bdpan-cli.py`
    - `sdk/python/README.md`
  - Rewrote `README.md` to match a CLI-project presentation:
    - 开源说明
    - 功能特性
    - 系统要求
    - 项目结构
    - 安装
    - 快速开始
    - 配置说明
    - CLI 工具使用
    - HTTP API
    - 在线文档与测试台
    - 注意事项
    - 免责声明
    - 许可证

## Verification
- Command: `python -m pytest -q`
- Result: `16 passed`
- Command: `python -m bdpan_wrapper --help`
- Result: new CLI command surface is shown correctly
- Command: `python -m bdpan_wrapper config init -c temp-config.json --force`
- Result: config file creation works
- Remaining risk:
  - the repo is still Python-first under `src/`, not a Go-style command tree; the benchmarking is on project expression and CLI UX, not language-level parity
  - README and CLI are aligned, but the HTTP portal/API pages still reflect the service layer orientation from the earlier stage

## Key Files
- `src/bdpan_wrapper/cli.py`
- `src/bdpan_wrapper/config.py`
- `pyproject.toml`
- `README.md`
- `cmd/bdpan-cli.py`
- `sdk/python/README.md`
- `tests/test_cli.py`

## Git Status
- Branch: not available; this directory is not a git repository
- Recent commit: none
- Pushed: no
