from __future__ import annotations

from pathlib import Path

from bdpan_wrapper.runtime import build_runtime


def test_build_runtime_creates_expected_directories(tmp_path: Path) -> None:
    runtime = build_runtime(home=tmp_path, bdpan_bin="bdpan")

    assert runtime.paths.home == tmp_path
    assert runtime.paths.runtime_root.exists()
    assert runtime.paths.accounts_dir.exists()
    assert runtime.paths.tasks_dir.exists()
    assert runtime.paths.account_configs_dir.exists()
    assert runtime.paths.uploads_dir.exists()


def test_build_runtime_wires_core_services(tmp_path: Path) -> None:
    runtime = build_runtime(home=tmp_path, bdpan_bin="bdpan")

    assert runtime.accounts is not None
    assert runtime.binding is not None
    assert runtime.files is not None
    assert runtime.tasks is not None
    assert runtime.adapter.bdpan_bin == "bdpan"
