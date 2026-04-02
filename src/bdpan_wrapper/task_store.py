from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from bdpan_wrapper.enums import DeliveryProvider, TaskKind, TaskStatus
from bdpan_wrapper.models import DeliveryArtifact, DeliveryTaskRecord, utcnow


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _deserialize_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class DeliveryTaskStore:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def task_file(self, task_id: str) -> Path:
        return self._root / f"{task_id}.json"

    def save(self, task: DeliveryTaskRecord) -> DeliveryTaskRecord:
        payload = asdict(task)
        payload["kind"] = task.kind.value
        payload["provider"] = task.provider.value
        payload["status"] = task.status.value
        payload["created_at"] = _serialize_datetime(task.created_at)
        payload["updated_at"] = _serialize_datetime(task.updated_at)
        if task.artifact is not None:
            payload["artifact"]["provider"] = task.artifact.provider.value
        self.task_file(task.id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return task

    def get(self, task_id: str) -> DeliveryTaskRecord | None:
        path = self.task_file(task_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        artifact_payload = payload.get("artifact")
        artifact = None
        if artifact_payload:
            artifact = DeliveryArtifact(
                provider=DeliveryProvider(str(artifact_payload["provider"])),
                remote_path=str(artifact_payload.get("remote_path") or ""),
                share_link=artifact_payload.get("share_link"),
                share_password=artifact_payload.get("share_password"),
                share_period_days=artifact_payload.get("share_period_days"),
                extra=dict(artifact_payload.get("extra") or {}),
            )
        return DeliveryTaskRecord(
            id=str(payload["id"]),
            kind=TaskKind(str(payload["kind"])),
            provider=DeliveryProvider(str(payload["provider"])),
            account_id=str(payload["account_id"]),
            local_path=payload.get("local_path"),
            remote_path=payload.get("remote_path"),
            status=TaskStatus(str(payload["status"])),
            error_message=payload.get("error_message"),
            artifact=artifact,
            created_at=_deserialize_datetime(payload.get("created_at")) or utcnow(),
            updated_at=_deserialize_datetime(payload.get("updated_at")) or utcnow(),
        )

    def list_tasks(self) -> list[DeliveryTaskRecord]:
        return [task for path in sorted(self._root.glob("*.json")) if (task := self.get(path.stem)) is not None]

