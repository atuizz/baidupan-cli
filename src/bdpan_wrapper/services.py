from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from bdpan_wrapper.accounts.models import DeliveryAccount
from bdpan_wrapper.accounts.service import DeliveryAccountService
from bdpan_wrapper.bdpan.adapter import BaiduPanCliAdapter
from bdpan_wrapper.bdpan.parser import BaiduMkdirResult, BaiduWhoAmIResult
from bdpan_wrapper.enums import DeliveryProvider, TaskKind, TaskStatus
from bdpan_wrapper.models import (
    DeliveryArtifact,
    DeliveryTaskRecord,
    TransferShareRequest,
    UploadShareRequest,
    utcnow,
)
from bdpan_wrapper.task_store import DeliveryTaskStore


@dataclass(frozen=True, slots=True)
class AuthSession:
    account: DeliveryAccount
    auth_url: str


class BaiduPanAccountBindingService:
    def __init__(self, account_service: DeliveryAccountService, adapter: BaiduPanCliAdapter) -> None:
        self._account_service = account_service
        self._adapter = adapter

    def start_binding(self, *, display_name: str) -> AuthSession:
        account = self._account_service.create_baidu_account(display_name=display_name)
        auth_url = self._adapter.get_auth_url(config_path=account.config_path)
        return AuthSession(account=account, auth_url=auth_url)

    def complete_binding(self, *, account_id: str, auth_code: str) -> DeliveryAccount:
        account = self._require_account(account_id)
        whoami = self._adapter.login_with_code(config_path=account.config_path, auth_code=auth_code)
        if not whoami.logged_in:
            raise RuntimeError("bdpan login completed but account is still not authenticated")
        return self._account_service.mark_active(
            account_id,
            username=whoami.username,
            expires_at=whoami.expires_at,
        )

    def check_account(self, *, account_id: str) -> BaiduWhoAmIResult:
        account = self._require_account(account_id)
        whoami = self._adapter.whoami(config_path=account.config_path)
        if whoami.logged_in:
            self._account_service.touch_check(
                account_id,
                username=whoami.username,
                expires_at=whoami.expires_at,
            )
        else:
            self._account_service.mark_error(account_id, message="bdpan account is not logged in")
        return whoami

    def _require_account(self, account_id: str) -> DeliveryAccount:
        account = self._account_service.get_account(account_id)
        if account is None:
            raise KeyError(f"delivery account not found: {account_id}")
        return account


class BaiduPanFileService:
    def __init__(
        self,
        *,
        account_service: DeliveryAccountService,
        task_store: DeliveryTaskStore,
        adapter: BaiduPanCliAdapter,
    ) -> None:
        self._account_service = account_service
        self._task_store = task_store
        self._adapter = adapter

    def mkdir(self, *, account_id: str, remote_path: str) -> BaiduMkdirResult:
        account = self._require_account(account_id)
        task = DeliveryTaskRecord(
            id=uuid4().hex,
            kind=TaskKind.MKDIR,
            provider=DeliveryProvider.BAIDU_PAN,
            account_id=account.id,
            remote_path=remote_path,
            status=TaskStatus.RUNNING,
        )
        self._task_store.save(task)
        try:
            result = self._adapter.mkdir(config_path=account.config_path, remote_path=remote_path)
            task.status = TaskStatus.SUCCEEDED
            task.updated_at = utcnow()
            task.artifact = DeliveryArtifact(
                provider=DeliveryProvider.BAIDU_PAN,
                remote_path=result.remote_path,
                extra={"created": result.created},
            )
            self._task_store.save(task)
            return result
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.updated_at = utcnow()
            self._task_store.save(task)
            raise

    def ls(self, *, account_id: str, remote_path: str | None = None):
        account = self._require_account(account_id)
        return self._adapter.ls(config_path=account.config_path, remote_path=remote_path)

    def upload_and_share(self, request: UploadShareRequest) -> DeliveryTaskRecord:
        account = self._require_account(request.account_id)
        local_path = Path(request.local_path)
        if not local_path.exists() or not local_path.is_file():
            raise FileNotFoundError(f"local file not found: {local_path}")
        task = DeliveryTaskRecord(
            id=request.task_id or uuid4().hex,
            kind=TaskKind.UPLOAD_SHARE,
            provider=DeliveryProvider.BAIDU_PAN,
            account_id=account.id,
            local_path=str(local_path),
            remote_path=request.remote_path,
            status=TaskStatus.PENDING,
        )
        self._task_store.save(task)
        try:
            task.status = TaskStatus.RUNNING
            task.updated_at = utcnow()
            self._task_store.save(task)
            upload_result = self._adapter.upload(
                config_path=account.config_path,
                local_path=local_path,
                remote_path=request.remote_path,
            )
            share_result = self._adapter.share(
                config_path=account.config_path,
                remote_path=upload_result.remote_path or request.remote_path,
            )
            task.artifact = DeliveryArtifact(
                provider=DeliveryProvider.BAIDU_PAN,
                remote_path=upload_result.remote_path or request.remote_path,
                share_link=share_result.link,
                share_password=share_result.password,
                share_period_days=share_result.period_days,
                extra={
                    "upload_status": upload_result.status,
                    "share_id": share_result.share_id,
                    "short_url": share_result.short_url,
                    "view_url": upload_result.view_url,
                },
            )
            task.status = TaskStatus.SUCCEEDED
            task.updated_at = utcnow()
            return self._task_store.save(task)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.updated_at = utcnow()
            self._task_store.save(task)
            raise

    def transfer_share(self, request: TransferShareRequest) -> DeliveryTaskRecord:
        account = self._require_account(request.account_id)
        task = DeliveryTaskRecord(
            id=request.task_id or uuid4().hex,
            kind=TaskKind.TRANSFER_SHARE,
            provider=DeliveryProvider.BAIDU_PAN,
            account_id=account.id,
            remote_path=request.save_path,
            status=TaskStatus.PENDING,
        )
        self._task_store.save(task)
        try:
            task.status = TaskStatus.RUNNING
            task.updated_at = utcnow()
            self._task_store.save(task)
            result = self._adapter.transfer(
                config_path=account.config_path,
                share_url=request.share_url,
                password=request.password,
                save_path=request.save_path,
            )
            task.artifact = DeliveryArtifact(
                provider=DeliveryProvider.BAIDU_PAN,
                remote_path=result.remote_path or request.save_path or "",
                extra={"raw_text": result.raw_text},
            )
            task.status = TaskStatus.SUCCEEDED
            task.updated_at = utcnow()
            return self._task_store.save(task)
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error_message = str(exc)
            task.updated_at = utcnow()
            self._task_store.save(task)
            raise

    def _require_account(self, account_id: str) -> DeliveryAccount:
        account = self._account_service.get_account(account_id)
        if account is None:
            raise KeyError(f"delivery account not found: {account_id}")
        return account
