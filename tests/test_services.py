from __future__ import annotations

from pathlib import Path

from bdpan_wrapper.accounts.service import DeliveryAccountService
from bdpan_wrapper.accounts.store import DeliveryAccountStore
from bdpan_wrapper.enums import TaskStatus
from bdpan_wrapper.models import TransferShareRequest, UploadShareRequest
from bdpan_wrapper.services import BaiduPanAccountBindingService, BaiduPanFileService
from bdpan_wrapper.task_store import DeliveryTaskStore


class FakeBaiduAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def get_auth_url(self, *, config_path: str) -> str:
        self.calls.append(("get_auth_url", config_path))
        return "https://openapi.baidu.com/oauth/2.0/authorize?device_code=abc"

    def login_with_code(self, *, config_path: str, auth_code: str):
        self.calls.append(("login_with_code", config_path, auth_code))
        return type("WhoAmI", (), {"logged_in": True, "username": "demo", "expires_at": None})()

    def whoami(self, *, config_path: str):
        self.calls.append(("whoami", config_path))
        return type("WhoAmI", (), {"logged_in": True, "username": "demo", "expires_at": None})()

    def mkdir(self, *, config_path: str, remote_path: str):
        self.calls.append(("mkdir", config_path, remote_path))
        return type("Mkdir", (), {"remote_path": remote_path, "created": True})()

    def upload(self, *, config_path: str, local_path: Path, remote_path: str):
        self.calls.append(("upload", config_path, str(local_path), remote_path))
        return type("UploadResult", (), {"status": "success", "remote_path": remote_path, "view_url": None})()

    def share(self, *, config_path: str, remote_path: str):
        self.calls.append(("share", config_path, remote_path))
        return type(
            "ShareResult",
            (),
            {"link": "https://pan.baidu.com/s/1abc", "password": "1234", "period_days": 7, "share_id": 1, "short_url": "1abc"},
        )()

    def transfer(self, *, config_path: str, share_url: str, password: str | None = None, save_path: str | None = None):
        self.calls.append(("transfer", config_path, share_url, password, save_path))
        return type("TransferResult", (), {"remote_path": save_path, "raw_text": '{"save_path":"%s"}' % save_path})()


def test_binding_and_file_services(tmp_path: Path) -> None:
    account_store = DeliveryAccountStore(tmp_path / "accounts")
    account_service = DeliveryAccountService(account_store, tmp_path / "configs")
    task_store = DeliveryTaskStore(tmp_path / "tasks")
    adapter = FakeBaiduAdapter()

    binding = BaiduPanAccountBindingService(account_service, adapter)
    files = BaiduPanFileService(account_service=account_service, task_store=task_store, adapter=adapter)

    session = binding.start_binding(display_name="primary")
    account = binding.complete_binding(account_id=session.account.id, auth_code="abcd")
    whoami = binding.check_account(account_id=account.id)

    assert account.username == "demo"
    assert whoami.logged_in is True

    mkdir_result = files.mkdir(account_id=account.id, remote_path="releases/demo")
    assert mkdir_result.remote_path == "releases/demo"

    local_file = tmp_path / "foo.pdf"
    local_file.write_bytes(b"demo")

    upload_task = files.upload_and_share(
        UploadShareRequest(
            account_id=account.id,
            local_path=local_file,
            remote_path="release/foo.pdf",
        )
    )
    assert upload_task.status == TaskStatus.SUCCEEDED
    assert upload_task.artifact is not None
    assert upload_task.artifact.share_link == "https://pan.baidu.com/s/1abc"

    transfer_task = files.transfer_share(
        TransferShareRequest(
            account_id=account.id,
            share_url="https://pan.baidu.com/s/1abc",
            password="1234",
            save_path="inbox/demo",
        )
    )
    assert transfer_task.status == TaskStatus.SUCCEEDED
    assert transfer_task.artifact is not None
    assert transfer_task.artifact.remote_path == "inbox/demo"

