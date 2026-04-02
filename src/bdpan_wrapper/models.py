from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bdpan_wrapper.enums import DeliveryProvider, TaskKind, TaskStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DeliveryArtifact:
    provider: DeliveryProvider
    remote_path: str
    share_link: str | None = None
    share_password: str | None = None
    share_period_days: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UploadShareRequest:
    account_id: str
    local_path: Path | str
    remote_path: str
    task_id: str | None = None


@dataclass(slots=True)
class TransferShareRequest:
    account_id: str
    share_url: str
    password: str | None = None
    save_path: str | None = None
    task_id: str | None = None


@dataclass(slots=True)
class DeliveryTaskRecord:
    id: str
    kind: TaskKind
    provider: DeliveryProvider
    account_id: str
    remote_path: str | None = None
    local_path: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    error_message: str | None = None
    artifact: DeliveryArtifact | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

