from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from bdpan_wrapper.accounts.models import DeliveryAccount
from bdpan_wrapper.bdpan.parser import BaiduMkdirResult, BaiduWhoAmIResult
from bdpan_wrapper.enums import AccountStatus
from bdpan_wrapper.api import app as app_module
from bdpan_wrapper.enums import DeliveryProvider, TaskKind, TaskStatus
from bdpan_wrapper.models import DeliveryArtifact, DeliveryTaskRecord


def test_healthz_endpoint() -> None:
    client = TestClient(app_module.create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@dataclass
class FakePaths:
    uploads_dir: Path


@dataclass
class FakeLsEntry:
    path: str
    name: str
    is_dir: bool
    size: int | None = None
    fs_id: int | None = None
    raw: dict | None = None


class FakeFiles:
    def mkdir(self, *, account_id, remote_path):
        return BaiduMkdirResult(remote_path=remote_path, created=True, raw_text="")

    def upload_and_share(self, request):
        return DeliveryTaskRecord(
            id="task-1",
            kind=TaskKind.UPLOAD_SHARE,
            provider=DeliveryProvider.BAIDU_PAN,
            account_id=request.account_id,
            local_path=str(request.local_path),
            remote_path=request.remote_path,
            status=TaskStatus.SUCCEEDED,
            artifact=DeliveryArtifact(
                provider=DeliveryProvider.BAIDU_PAN,
                remote_path=request.remote_path,
                share_link="https://pan.baidu.com/s/test",
            ),
        )

    def ls(self, *, account_id, remote_path=None):
        return [
            FakeLsEntry(path="/apps/bdpan/demo", name="demo", is_dir=True, size=None, fs_id=1, raw={"x": 1}),
        ]


class FakeAccounts:
    def list_accounts(self):
        return []


class FakeTasks:
    def list_tasks(self):
        return []


class FakeBinding:
    def start_binding(self, display_name):
        return type(
            "Session",
            (),
            {
                "account": type("Account", (), {"id": "acc-1", "display_name": display_name})(),
                "auth_url": "https://example.com/auth",
            },
        )()

    def complete_binding(self, *, account_id, auth_code):
        return DeliveryAccount(
            id=account_id,
            provider=DeliveryProvider.BAIDU_PAN,
            display_name="primary",
            config_path="/tmp/config.json",
            username="demo",
            status=AccountStatus.ACTIVE,
        )

    def check_account(self, *, account_id):
        return BaiduWhoAmIResult(logged_in=True, username="demo", expires_at=None)


class FailingBinding:
    def start_binding(self, display_name):
        raise RuntimeError(f"bind failed for {display_name}")


@dataclass
class FakeRuntime:
    paths: FakePaths
    files: FakeFiles
    accounts: FakeAccounts
    tasks: FakeTasks
    binding: FakeBinding


def test_browser_upload_share_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.post(
        "/api/files/browser-upload-share",
        data={"account_id": "acc-1", "remote_path": "releases/demo.txt"},
        files={"file": ("demo.txt", b"hello")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["artifact"]["share_link"] == "https://pan.baidu.com/s/test"
    assert list(tmp_path.iterdir()) == []


def test_bind_start_returns_http_400_on_runtime_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FailingBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.post("/api/accounts/bind/start", json={"display_name": "broken"})

    assert response.status_code == 400
    assert "bind failed" in response.json()["detail"]


def test_ls_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.post("/api/files/ls", json={"account_id": "acc-1", "remote_path": "/apps/bdpan"})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "demo"


def test_api_v1_transfer_endpoint_returns_enveloped_payload(tmp_path: Path, monkeypatch) -> None:
    class FakeTransferFiles(FakeFiles):
        def transfer_share(self, request):
            return DeliveryTaskRecord(
                id="task-transfer",
                kind=TaskKind.TRANSFER_SHARE,
                provider=DeliveryProvider.BAIDU_PAN,
                account_id=request.account_id,
                remote_path=request.save_path,
                status=TaskStatus.SUCCEEDED,
                artifact=DeliveryArtifact(
                    provider=DeliveryProvider.BAIDU_PAN,
                    remote_path=request.save_path or "/apps/bdpan/demo",
                ),
            )

    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeTransferFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.post(
        "/api/v1/shares/transfer",
        json={
            "account_id": "acc-1",
            "share_url": "https://pan.baidu.com/s/test",
            "password": "abcd",
            "save_path": "/apps/bdpan/inbox/demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["artifact"]["remote_path"] == "/apps/bdpan/inbox/demo"


def test_api_v1_bind_start_complete_and_check(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    start_response = client.post("/api/v1/accounts/bind/start", json={"display_name": "primary"})
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["success"] is True
    assert start_payload["data"]["auth_url"] == "https://example.com/auth"

    complete_response = client.post(
        "/api/v1/accounts/bind/complete",
        json={"account_id": "acc-1", "auth_code": "abcd"},
    )
    assert complete_response.status_code == 200
    complete_payload = complete_response.json()
    assert complete_payload["success"] is True
    assert complete_payload["data"]["id"] == "acc-1"

    check_response = client.post("/api/v1/accounts/acc-1/check")
    assert check_response.status_code == 200
    check_payload = check_response.json()
    assert check_payload["success"] is True
    assert check_payload["data"]["logged_in"] is True


def test_api_v1_mkdir_and_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    mkdir_response = client.post(
        "/api/v1/files/mkdir",
        json={"account_id": "acc-1", "remote_path": "/apps/bdpan/releases"},
    )
    assert mkdir_response.status_code == 200
    mkdir_payload = mkdir_response.json()
    assert mkdir_payload["success"] is True
    assert mkdir_payload["data"]["created"] is True

    list_response = client.post(
        "/api/v1/files/list",
        json={"account_id": "acc-1", "remote_path": "/apps/bdpan"},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert list_payload["data"][0]["name"] == "demo"


def test_compat_transfer_endpoint_accepts_query_params(tmp_path: Path, monkeypatch) -> None:
    class FakeTransferFiles(FakeFiles):
        def transfer_share(self, request):
            return DeliveryTaskRecord(
                id="task-transfer",
                kind=TaskKind.TRANSFER_SHARE,
                provider=DeliveryProvider.BAIDU_PAN,
                account_id=request.account_id,
                remote_path=request.save_path,
                status=TaskStatus.SUCCEEDED,
                artifact=DeliveryArtifact(
                    provider=DeliveryProvider.BAIDU_PAN,
                    remote_path=request.save_path or "/apps/bdpan/inbox/demo",
                ),
            )

    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeTransferFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.get(
        "/compat/baidu/transfer",
        params={
            "account_id": "acc-1",
            "url": "https://pan.baidu.com/s/test",
            "pwd": "abcd",
            "path": "/apps/bdpan/inbox/demo",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["artifact"]["remote_path"] == "/apps/bdpan/inbox/demo"


def test_portal_page_is_served(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "build_runtime",
        lambda: FakeRuntime(
            paths=FakePaths(uploads_dir=tmp_path),
            files=FakeFiles(),
            accounts=FakeAccounts(),
            tasks=FakeTasks(),
            binding=FakeBinding(),
        ),
    )
    client = TestClient(app_module.create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "test console" in response.text
