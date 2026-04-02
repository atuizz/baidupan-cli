from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
import sys

import uvicorn

from bdpan_wrapper.api.app import create_app
from bdpan_wrapper.config import (
    effective_bdpan_bin,
    effective_default_account_id,
    effective_runtime_home,
    load_project_config,
    write_project_config,
)
from bdpan_wrapper.models import TransferShareRequest, UploadShareRequest
from bdpan_wrapper.runtime import build_runtime


def _print(payload: object) -> None:
    if is_dataclass(payload):
        payload = asdict(payload)
    elif isinstance(payload, list):
        payload = [asdict(item) if is_dataclass(item) else item for item in payload]
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _build_runtime(config_path: str | None):
    project_config = load_project_config(config_path)
    return build_runtime(
        home=effective_runtime_home(project_config),
        bdpan_bin=effective_bdpan_bin(project_config),
    ), project_config


def _resolve_account_id(runtime, project_config, account_id: str | None) -> str:
    if account_id:
        return account_id

    configured = effective_default_account_id(project_config)
    if configured:
        return configured

    accounts = runtime.accounts.list_accounts()
    active_accounts = [account for account in accounts if str(account.status) == "active"]
    if len(active_accounts) == 1:
        return active_accounts[0].id
    if len(accounts) == 1:
        return accounts[0].id

    raise SystemExit(
        "Could not resolve account_id. Pass --account-id explicitly or set default_account_id in config.json."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bdpan-cli",
        description="Third-party Baidu Netdisk CLI built on the official bdpan CLI.",
    )
    parser.add_argument("-c", "--config", default="config.json", help="Path to config.json.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config", help="Config file helpers")
    config_sub = config_parser.add_subparsers(dest="config_command", required=True)
    config_init = config_sub.add_parser("init", help="Create a default config.json")
    config_init.add_argument("--force", action="store_true", help="Overwrite an existing file")

    account_parser = subparsers.add_parser("account", help="Account commands")
    account_sub = account_parser.add_subparsers(dest="account_command", required=True)
    account_sub.add_parser("list", help="List local accounts")

    account_user = account_sub.add_parser("user", help="Check the current login state for an account")
    account_user.add_argument("--account-id")

    bind_parser = subparsers.add_parser("bind", help="Account bind flow")
    bind_sub = bind_parser.add_subparsers(dest="bind_command", required=True)
    bind_start = bind_sub.add_parser("start", help="Create a local account and return an official auth URL")
    bind_start.add_argument("--name", required=True, help="Display name for the local account")
    bind_complete = bind_sub.add_parser("complete", help="Complete bind with the auth code")
    bind_complete.add_argument("--account-id", required=True)
    bind_complete.add_argument("--code", required=True)

    list_parser = subparsers.add_parser("list", aliases=["ls"], help="List a remote directory")
    list_parser.add_argument("remote_path", nargs="?", default="/apps/bdpan")
    list_parser.add_argument("--account-id")

    mkdir_parser = subparsers.add_parser("mkdir", help="Create a remote directory")
    mkdir_parser.add_argument("remote_path")
    mkdir_parser.add_argument("--account-id")

    upload_parser = subparsers.add_parser("upload", help="Upload a file and create a share link")
    upload_parser.add_argument("local_path")
    upload_parser.add_argument("remote_path")
    upload_parser.add_argument("--account-id")

    transfer_parser = subparsers.add_parser("transfer", help="Transfer a public share link into an account")
    transfer_parser.add_argument("share_url")
    transfer_parser.add_argument("save_path")
    transfer_parser.add_argument("--pwd")
    transfer_parser.add_argument("--account-id")

    api_parser = subparsers.add_parser("api", help="Serve the HTTP API and docs portal")
    api_sub = api_parser.add_subparsers(dest="api_command", required=True)
    api_serve = api_sub.add_parser("serve", help="Start the API server")
    api_serve.add_argument("--host", default="127.0.0.1")
    api_serve.add_argument("--port", type=int, default=8787)

    return parser


def normalize_legacy_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv

    global_args: list[str] = []
    remaining = list(argv)
    while "-c" in remaining or "--config" in remaining:
        flag = "-c" if "-c" in remaining else "--config"
        index = remaining.index(flag)
        try:
            value = remaining[index + 1]
        except IndexError as exc:
            raise SystemExit(f"missing value for {flag}") from exc
        global_args.extend([flag, value])
        del remaining[index:index + 2]

    head, *tail = remaining
    if head == "account-bind-start":
        return global_args + ["bind", "start", "--name", _pop_value(tail, "--display-name")]
    if head == "account-bind-complete":
        return global_args + [
            "bind",
            "complete",
            "--account-id",
            _pop_value(tail, "--account-id"),
            "--code",
            _pop_value(tail, "--auth-code"),
        ]
    if head == "account-check":
        return global_args + ["account", "user", "--account-id", _pop_value(tail, "--account-id")]
    if head == "account-list":
        return global_args + ["account", "list"]
    if head == "upload-share":
        return global_args + [
            "upload",
            _pop_value(tail, "--local-path"),
            _pop_value(tail, "--remote-path"),
            "--account-id",
            _pop_value(tail, "--account-id"),
        ]
    if head == "transfer-share":
        normalized = [
            "transfer",
            _pop_value(tail, "--share-url"),
            _pop_value(tail, "--save-path") if "--save-path" in tail else "",
            "--account-id",
            _pop_value(tail, "--account-id"),
        ]
        if "--password" in tail:
            normalized.extend(["--pwd", _pop_value(tail, "--password")])
        return global_args + [item for item in normalized if item != ""]
    if head == "serve-api":
        normalized = ["api", "serve"]
        if "--host" in tail:
            normalized.extend(["--host", _pop_value(tail, "--host")])
        if "--port" in tail:
            normalized.extend(["--port", _pop_value(tail, "--port")])
        return global_args + normalized
    return global_args + remaining


def _pop_value(args: list[str], flag: str) -> str:
    if flag not in args:
        raise SystemExit(f"legacy command missing required flag: {flag}")
    index = args.index(flag)
    try:
        return args[index + 1]
    except IndexError as exc:
        raise SystemExit(f"legacy command missing value for {flag}") from exc


def main() -> None:
    parser = build_parser()
    normalized = normalize_legacy_argv(sys.argv[1:])
    args = parser.parse_args(normalized)

    if args.command == "config" and args.config_command == "init":
        created = write_project_config(args.config, force=args.force)
        _print({"config_path": str(created), "message": "Config file created"})
        return

    if args.command == "api" and args.api_command == "serve":
        uvicorn.run(create_app(), host=args.host, port=args.port)
        return

    runtime, project_config = _build_runtime(args.config)

    if args.command == "bind" and args.bind_command == "start":
        session = runtime.binding.start_binding(display_name=args.name)
        _print(
            {
                "account_id": session.account.id,
                "display_name": session.account.display_name,
                "config_path": session.account.config_path,
                "auth_url": session.auth_url,
            }
        )
        return

    if args.command == "bind" and args.bind_command == "complete":
        account = runtime.binding.complete_binding(account_id=args.account_id, auth_code=args.code)
        _print(account)
        return

    if args.command == "account" and args.account_command == "list":
        _print(runtime.accounts.list_accounts())
        return

    if args.command == "account" and args.account_command == "user":
        resolved_account_id = _resolve_account_id(runtime, project_config, args.account_id)
        result = runtime.binding.check_account(account_id=resolved_account_id)
        _print(result)
        return

    if args.command in {"list", "ls"}:
        resolved_account_id = _resolve_account_id(runtime, project_config, args.account_id)
        _print(runtime.files.ls(account_id=resolved_account_id, remote_path=args.remote_path))
        return

    if args.command == "mkdir":
        resolved_account_id = _resolve_account_id(runtime, project_config, args.account_id)
        _print(runtime.files.mkdir(account_id=resolved_account_id, remote_path=args.remote_path))
        return

    if args.command == "upload":
        resolved_account_id = _resolve_account_id(runtime, project_config, args.account_id)
        task = runtime.files.upload_and_share(
            UploadShareRequest(
                account_id=resolved_account_id,
                local_path=args.local_path,
                remote_path=args.remote_path,
            )
        )
        _print(task)
        return

    if args.command == "transfer":
        resolved_account_id = _resolve_account_id(runtime, project_config, args.account_id)
        task = runtime.files.transfer_share(
            TransferShareRequest(
                account_id=resolved_account_id,
                share_url=args.share_url,
                password=args.pwd,
                save_path=args.save_path,
            )
        )
        _print(task)
        return

    raise SystemExit(f"unsupported command: {args.command}")
