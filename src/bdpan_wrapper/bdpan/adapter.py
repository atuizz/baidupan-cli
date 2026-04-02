from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bdpan_wrapper.bdpan.parser import (
    BaiduLsEntry,
    BaiduMkdirResult,
    BaiduShareResult,
    BaiduTransferResult,
    BaiduUploadResult,
    BaiduWhoAmIResult,
    parse_ls_output,
    parse_mkdir_output,
    parse_share_output,
    parse_transfer_output,
    parse_upload_output,
    parse_whoami_output,
)


class CommandRunner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessCommandRunner:
    def run(
        self,
        args: list[str],
        *,
        input_text: str | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            encoding="utf-8",
            errors="replace",
        )


class BaiduPanCliError(RuntimeError):
    pass


@dataclass(slots=True)
class BaiduPanCliAdapter:
    bdpan_bin: str = "bdpan"
    runner: CommandRunner | None = None

    def __post_init__(self) -> None:
        if self.runner is None:
            self.runner = SubprocessCommandRunner()

    def whoami(self, *, config_path: str) -> BaiduWhoAmIResult:
        completed = self._run(["whoami", "--json"], config_path=config_path)
        return parse_whoami_output(completed.stdout)

    def get_auth_url(self, *, config_path: str) -> str:
        completed = self._run(["login", "--accept-disclaimer", "--get-auth-url"], config_path=config_path)
        url = (completed.stdout or "").strip()
        if not url.startswith("http"):
            raise BaiduPanCliError(f"bdpan login did not return a valid auth url: {url or completed.stderr}")
        return url

    def login_with_code(self, *, config_path: str, auth_code: str) -> BaiduWhoAmIResult:
        self._run(
            ["login", "--accept-disclaimer", "--set-code-stdin"],
            config_path=config_path,
            input_text=f"{auth_code}\n",
        )
        return self.whoami(config_path=config_path)

    def mkdir(self, *, config_path: str, remote_path: str) -> BaiduMkdirResult:
        completed = self._run(["mkdir", remote_path, "--json"], config_path=config_path)
        return parse_mkdir_output(completed.stdout, remote_path)

    def ls(self, *, config_path: str, remote_path: str | None = None) -> list[BaiduLsEntry]:
        args = ["ls", "--json"]
        if remote_path:
            args.append(remote_path)
        completed = self._run(args, config_path=config_path)
        return parse_ls_output(completed.stdout)

    def upload(self, *, config_path: str, local_path: Path, remote_path: str) -> BaiduUploadResult:
        completed = self._run(["upload", str(local_path), remote_path, "--json"], config_path=config_path)
        return parse_upload_output(completed.stdout)

    def share(self, *, config_path: str, remote_path: str) -> BaiduShareResult:
        completed = self._run(["share", "--json", remote_path], config_path=config_path)
        return parse_share_output(completed.stdout)

    def transfer(
        self,
        *,
        config_path: str,
        share_url: str,
        password: str | None = None,
        save_path: str | None = None,
    ) -> BaiduTransferResult:
        args = ["transfer", share_url]
        if password:
            args.extend(["-p", password])
        if save_path:
            args.append(save_path)
        args.append("--json")
        completed = self._run(args, config_path=config_path)
        return parse_transfer_output(completed.stdout)

    def _run(
        self,
        args: list[str],
        *,
        config_path: str,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        full_args = [self.bdpan_bin, "--config-path", config_path, *args]
        env = os.environ.copy()
        env["BDPAN_CONFIG_PATH"] = config_path
        try:
            completed = self.runner.run(full_args, input_text=input_text, env=env)
        except FileNotFoundError as exc:
            raise BaiduPanCliError(
                f"bdpan executable not found: {self.bdpan_bin}. Set BDPAN_BIN or install the official bdpan CLI first."
            ) from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise BaiduPanCliError(f"bdpan command failed ({' '.join(full_args)}): {stderr}")
        return completed
