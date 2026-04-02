from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from bdpan_wrapper.enums import AccountStatus, DeliveryProvider
from bdpan_wrapper.models import utcnow


@dataclass(slots=True)
class DeliveryAccount:
    id: str
    provider: DeliveryProvider
    display_name: str
    config_path: str
    status: AccountStatus = AccountStatus.DRAFT
    username: str | None = None
    expires_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

