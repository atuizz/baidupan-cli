from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    pass


class DeliveryProvider(_StrEnum):
    BAIDU_PAN = "baidu_pan"


class AccountStatus(_StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class TaskStatus(_StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskKind(_StrEnum):
    UPLOAD_SHARE = "upload_share"
    TRANSFER_SHARE = "transfer_share"
    MKDIR = "mkdir"

