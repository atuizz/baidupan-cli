from __future__ import annotations

import json
from pathlib import Path

from bdpan_wrapper import cli


def test_write_project_config(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    cli.write_project_config(target)

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["BaiduPan"]["bdpan_bin"] == "bdpan"
    assert payload["BaiduPan"]["runtime_home"] == "~/.bdpan-wrapper"


def test_cli_config_init_command(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(
        "sys.argv",
        ["bdpan-cli", "-c", str(config_path), "config", "init"],
    )

    cli.main()

    assert config_path.exists()
    output = capsys.readouterr().out
    assert "Config file created" in output


def test_resolve_account_id_uses_default_account(monkeypatch) -> None:
    class FakeAccount:
        def __init__(self, account_id: str, status: str) -> None:
            self.id = account_id
            self.status = status

    class FakeRuntime:
        class Accounts:
            @staticmethod
            def list_accounts():
                return [FakeAccount("acc-default", "active")]

        accounts = Accounts()

    project_config = cli.load_project_config(None)
    resolved = cli._resolve_account_id(FakeRuntime(), project_config, None)
    assert resolved == "acc-default"
