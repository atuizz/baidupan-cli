from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    home: Path
    runtime_root: Path
    accounts_dir: Path
    tasks_dir: Path
    account_configs_dir: Path
    uploads_dir: Path


@dataclass(slots=True)
class BaiduPanCliConfig:
    runtime_home: str | None = None
    bdpan_bin: str | None = None
    default_account_id: str | None = None


@dataclass(slots=True)
class ProjectConfig:
    BaiduPan: BaiduPanCliConfig


def default_home() -> Path:
    return Path(os.environ.get("BDPAN_WRAPPER_HOME") or (Path.home() / ".bdpan-wrapper"))


def build_runtime_paths(home: Path | None = None) -> RuntimePaths:
    resolved_home = Path(home) if home is not None else default_home()
    runtime_root = resolved_home / ".runtime"
    return RuntimePaths(
        home=resolved_home,
        runtime_root=runtime_root,
        accounts_dir=runtime_root / "accounts",
        tasks_dir=runtime_root / "tasks",
        account_configs_dir=runtime_root / "account_configs",
        uploads_dir=runtime_root / "uploads",
    )


def default_project_config() -> ProjectConfig:
    return ProjectConfig(
        BaiduPan=BaiduPanCliConfig(
            runtime_home="~/.bdpan-wrapper",
            bdpan_bin="bdpan",
            default_account_id="",
        )
    )


def load_project_config(path: Path | str | None) -> ProjectConfig:
    if path is None:
        return default_project_config()

    file_path = Path(path)
    if not file_path.exists():
        return default_project_config()

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    section = raw.get("BaiduPan") or {}
    return ProjectConfig(
        BaiduPan=BaiduPanCliConfig(
            runtime_home=section.get("runtime_home"),
            bdpan_bin=section.get("bdpan_bin"),
            default_account_id=section.get("default_account_id"),
        )
    )


def write_project_config(path: Path | str, *, force: bool = False) -> Path:
    file_path = Path(path)
    if file_path.exists() and not force:
        raise FileExistsError(f"config already exists: {file_path}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(default_project_config())
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def effective_runtime_home(config: ProjectConfig) -> Path | None:
    value = os.environ.get("BDPAN_WRAPPER_HOME") or config.BaiduPan.runtime_home
    if not value:
        return None
    return Path(value).expanduser()


def effective_bdpan_bin(config: ProjectConfig) -> str | None:
    return os.environ.get("BDPAN_BIN") or config.BaiduPan.bdpan_bin or "bdpan"


def effective_default_account_id(config: ProjectConfig) -> str | None:
    return (config.BaiduPan.default_account_id or "").strip() or None
