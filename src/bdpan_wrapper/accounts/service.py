from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from bdpan_wrapper.accounts.models import DeliveryAccount
from bdpan_wrapper.accounts.store import DeliveryAccountStore
from bdpan_wrapper.enums import AccountStatus, DeliveryProvider
from bdpan_wrapper.models import utcnow


class DeliveryAccountService:
    def __init__(self, store: DeliveryAccountStore, account_runtime_root: Path) -> None:
        self._store = store
        self._account_runtime_root = Path(account_runtime_root)
        self._account_runtime_root.mkdir(parents=True, exist_ok=True)

    def create_baidu_account(self, *, display_name: str) -> DeliveryAccount:
        account_id = uuid4().hex
        config_dir = self._account_runtime_root / account_id
        config_dir.mkdir(parents=True, exist_ok=True)
        account = DeliveryAccount(
            id=account_id,
            provider=DeliveryProvider.BAIDU_PAN,
            display_name=display_name,
            config_path=str(config_dir / "config.json"),
            status=AccountStatus.DRAFT,
        )
        self._store.save(account)
        return account

    def get_account(self, account_id: str) -> DeliveryAccount | None:
        return self._store.get(account_id)

    def list_accounts(self) -> list[DeliveryAccount]:
        return self._store.list_accounts()

    def mark_active(self, account_id: str, *, username: str | None, expires_at) -> DeliveryAccount:
        account = self._require_account(account_id)
        account.status = AccountStatus.ACTIVE
        account.username = username
        account.expires_at = expires_at
        account.last_checked_at = utcnow()
        account.last_error = None
        account.updated_at = utcnow()
        return self._store.save(account)

    def mark_error(self, account_id: str, *, message: str) -> DeliveryAccount:
        account = self._require_account(account_id)
        account.status = AccountStatus.ERROR
        account.last_error = message
        account.last_checked_at = utcnow()
        account.updated_at = utcnow()
        return self._store.save(account)

    def touch_check(self, account_id: str, *, username: str | None, expires_at) -> DeliveryAccount:
        account = self._require_account(account_id)
        account.username = username or account.username
        account.expires_at = expires_at
        account.last_checked_at = utcnow()
        account.updated_at = utcnow()
        return self._store.save(account)

    def _require_account(self, account_id: str) -> DeliveryAccount:
        account = self._store.get(account_id)
        if account is None:
            raise KeyError(f"delivery account not found: {account_id}")
        return account

