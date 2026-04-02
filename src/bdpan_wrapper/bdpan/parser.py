from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BaiduWhoAmIResult:
    logged_in: bool
    username: str | None = None
    expires_at: datetime | None = None
    raw_text: str = ""


@dataclass(frozen=True, slots=True)
class BaiduUploadResult:
    status: str
    local_path: str
    remote_path: str
    view_url: str | None = None


@dataclass(frozen=True, slots=True)
class BaiduShareResult:
    link: str
    password: str | None
    period_days: int | None
    share_id: int | None = None
    short_url: str | None = None


@dataclass(frozen=True, slots=True)
class BaiduMkdirResult:
    remote_path: str
    created: bool = True
    raw_text: str = ""


@dataclass(frozen=True, slots=True)
class BaiduTransferResult:
    remote_path: str | None
    raw_text: str = ""


@dataclass(frozen=True, slots=True)
class BaiduLsEntry:
    path: str
    name: str
    is_dir: bool
    size: int | None = None
    fs_id: int | None = None
    raw: dict | None = None


def parse_whoami_output(stdout: str) -> BaiduWhoAmIResult:
    text = (stdout or "").strip()
    if not text:
        return BaiduWhoAmIResult(logged_in=False, raw_text=text)
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        status = str(payload.get("status") or payload.get("auth_status") or "").strip().lower()
        username = payload.get("username") or payload.get("user_name")
        expires_raw = payload.get("expires_at") or payload.get("token_expire_at")
        authenticated = payload.get("authenticated")
        has_valid_token = payload.get("has_valid_token")
        logged_in = (
            authenticated is True
            or has_valid_token is True
            or status in {"logged_in", "active", "ok", "success"}
            or bool(username)
        )
        return BaiduWhoAmIResult(
            logged_in=logged_in,
            username=str(username) if username else None,
            expires_at=_maybe_parse_datetime(expires_raw),
            raw_text=text,
        )
    logged_in = "已登录" in text
    username = None
    expires_at = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("用户名"):
            username = line.split(":", 1)[1].strip() or None
        if line.startswith("Token 有效期至:"):
            expires_at = _maybe_parse_datetime(line.split(":", 1)[1].strip())
    return BaiduWhoAmIResult(logged_in=logged_in, username=username, expires_at=expires_at, raw_text=text)


def parse_upload_output(stdout: str) -> BaiduUploadResult:
    payload = json.loads((stdout or "").strip())
    _raise_if_error_payload(payload, default_message="bdpan upload failed")
    status = str(payload.get("status") or "")
    if status and status.lower() != "success":
        raise RuntimeError(str(payload.get("error") or f"bdpan upload returned status={status}"))
    return BaiduUploadResult(
        status=status or "success",
        local_path=str(payload.get("local_path") or ""),
        remote_path=str(payload.get("remote_path") or payload.get("remote") or ""),
        view_url=payload.get("viewUrl") or payload.get("view_url"),
    )


def parse_share_output(stdout: str) -> BaiduShareResult:
    payload = json.loads((stdout or "").strip())
    _raise_if_error_payload(payload, default_message="bdpan share failed")
    return BaiduShareResult(
        link=str(payload.get("link") or ""),
        password=payload.get("pwd") or payload.get("password"),
        period_days=int(payload["period"]) if payload.get("period") is not None else None,
        share_id=int(payload["share_id"]) if payload.get("share_id") is not None else None,
        short_url=payload.get("short_url"),
    )


def parse_mkdir_output(stdout: str, remote_path: str) -> BaiduMkdirResult:
    text = (stdout or "").strip()
    if not text:
        return BaiduMkdirResult(remote_path=remote_path, raw_text=text)
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        _raise_if_error_payload(payload, default_message="bdpan mkdir failed")
        actual_remote = str(payload.get("remote_path") or payload.get("path") or remote_path)
        return BaiduMkdirResult(remote_path=actual_remote, created=True, raw_text=text)
    return BaiduMkdirResult(remote_path=remote_path, created=True, raw_text=text)


def parse_transfer_output(stdout: str) -> BaiduTransferResult:
    text = (stdout or "").strip()
    if not text:
        return BaiduTransferResult(remote_path=None, raw_text=text)
    if text.startswith("{") or text.startswith("["):
        payload = json.loads(text)
        _raise_if_error_payload(payload, default_message="bdpan transfer failed")
        remote_path = payload.get("remote_path") or payload.get("save_path") or payload.get("path")
        return BaiduTransferResult(remote_path=str(remote_path) if remote_path else None, raw_text=text)
    return BaiduTransferResult(remote_path=None, raw_text=text)


def parse_ls_output(stdout: str) -> list[BaiduLsEntry]:
    text = (stdout or "").strip()
    if not text:
        return []
    payload = json.loads(text)
    _raise_if_error_payload(payload, default_message="bdpan ls failed")

    items: list[dict]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        maybe_list = payload.get("list") or payload.get("items") or payload.get("data") or []
        if isinstance(maybe_list, list):
            items = maybe_list
        else:
            items = []
    else:
        items = []

    results: list[BaiduLsEntry] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or item.get("server_filename") or item.get("name") or "")
        name = str(item.get("server_filename") or item.get("name") or PathLike.basename(path))
        is_dir = bool(item.get("isdir") in (1, True, "1") or item.get("is_dir") is True)
        size_raw = item.get("size")
        fs_id_raw = item.get("fs_id") or item.get("fsid")
        results.append(
            BaiduLsEntry(
                path=path,
                name=name,
                is_dir=is_dir,
                size=int(size_raw) if size_raw not in (None, "") else None,
                fs_id=int(fs_id_raw) if fs_id_raw not in (None, "") else None,
                raw=item,
            )
        )
    return results


def _raise_if_error_payload(payload: object, *, default_message: str) -> None:
    if isinstance(payload, dict) and payload.get("code") not in (None, 0):
        raise RuntimeError(str(payload.get("error") or default_message))


def _maybe_parse_datetime(value: object | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.year <= 1:
            return None
        return parsed
    except ValueError:
        return None


class PathLike:
    @staticmethod
    def basename(path: str) -> str:
        normalized = str(path or "").rstrip("/")
        if not normalized:
            return ""
        return normalized.split("/")[-1]
