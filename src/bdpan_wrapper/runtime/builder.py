from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bdpan_wrapper.accounts.service import DeliveryAccountService
from bdpan_wrapper.accounts.store import DeliveryAccountStore
from bdpan_wrapper.bdpan.adapter import BaiduPanCliAdapter
from bdpan_wrapper.config import RuntimePaths, build_runtime_paths
from bdpan_wrapper.services import BaiduPanAccountBindingService, BaiduPanFileService
from bdpan_wrapper.task_store import DeliveryTaskStore


@dataclass(slots=True)
class AppRuntime:
    paths: RuntimePaths
    accounts: DeliveryAccountService
    binding: BaiduPanAccountBindingService
    files: BaiduPanFileService
    tasks: DeliveryTaskStore
    adapter: BaiduPanCliAdapter


def build_runtime(home: Path | None = None, *, bdpan_bin: str | None = None) -> AppRuntime:
    paths = build_runtime_paths(home)
    for path in (paths.runtime_root, paths.accounts_dir, paths.tasks_dir, paths.account_configs_dir, paths.uploads_dir):
        path.mkdir(parents=True, exist_ok=True)

    account_store = DeliveryAccountStore(paths.accounts_dir)
    account_service = DeliveryAccountService(account_store, paths.account_configs_dir)
    task_store = DeliveryTaskStore(paths.tasks_dir)
    adapter = BaiduPanCliAdapter(bdpan_bin=bdpan_bin or os.environ.get("BDPAN_BIN", "bdpan"))
    binding = BaiduPanAccountBindingService(account_service, adapter)
    files = BaiduPanFileService(account_service=account_service, task_store=task_store, adapter=adapter)
    return AppRuntime(
        paths=paths,
        accounts=account_service,
        binding=binding,
        files=files,
        tasks=task_store,
        adapter=adapter,
    )
