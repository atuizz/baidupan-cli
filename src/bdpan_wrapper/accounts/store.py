from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from bdpan_wrapper.accounts.models import DeliveryAccount
from bdpan_wrapper.enums import AccountStatus, DeliveryProvider
from bdpan_wrapper.models import utcnow


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _deserialize_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class DeliveryAccountStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def account_file(self, account_id: str) -> Path:
        return self._root / f"{account_id}.json"

    def save(self, account: DeliveryAccount) -> DeliveryAccount:
        payload = asdict(account)
        payload["provider"] = account.provider.value
        payload["status"] = account.status.value
        for key in ("expires_at", "last_checked_at", "created_at", "updated_at"):
            payload[key] = _serialize_datetime(getattr(account, key))
        self.account_file(account.id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return account

    def get(self, account_id: str) -> DeliveryAccount | None:
        path = self.account_file(account_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DeliveryAccount(
            id=str(payload["id"]),
            provider=DeliveryProvider(str(payload["provider"])),
            display_name=str(payload["display_name"]),
            config_path=str(payload["config_path"]),
            status=AccountStatus(str(payload["status"])),
            username=payload.get("username"),
            expires_at=_deserialize_datetime(payload.get("expires_at")),
            last_checked_at=_deserialize_datetime(payload.get("last_checked_at")),
            last_error=payload.get("last_error"),
            metadata=dict(payload.get("metadata") or {}),
            created_at=_deserialize_datetime(payload.get("created_at")) or utcnow(),
            updated_at=_deserialize_datetime(payload.get("updated_at")) or utcnow(),
        )

    def list_accounts(self) -> list[DeliveryAccount]:
        return [account for path in sorted(self._root.glob("*.json")) if (account := self.get(path.stem)) is not None]

