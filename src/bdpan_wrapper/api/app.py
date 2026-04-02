from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from shutil import copyfileobj
import shutil
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bdpan_wrapper.models import TransferShareRequest, UploadShareRequest
from bdpan_wrapper.runtime import build_runtime

ROOT_PATH = "/apps/bdpan"


class BindStartBody(BaseModel):
    display_name: str = Field(default="", description="Local account display name")


class BindCompleteBody(BaseModel):
    account_id: str
    auth_code: str


class MkdirBody(BaseModel):
    account_id: str
    remote_path: str


class UploadShareBody(BaseModel):
    account_id: str
    local_path: str
    remote_path: str


class TransferShareBody(BaseModel):
    account_id: str
    share_url: str
    password: str | None = None
    save_path: str | None = None


class LsBody(BaseModel):
    account_id: str
    remote_path: str | None = None


def build_success(data, *, message: str = "ok", request_id: str | None = None, code: int = 0) -> dict:
    return {
        "success": True,
        "code": code,
        "message": message,
        "request_id": request_id or uuid4().hex,
        "data": jsonable_encoder(data),
    }


def build_error(
    *,
    message: str,
    code: int,
    status_code: int,
    request_id: str | None = None,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code,
            "message": message,
            "request_id": request_id or uuid4().hex,
            "data": None,
            "details": jsonable_encoder(details or {}),
        },
    )


def to_dict(value):
    return jsonable_encoder(asdict(value) if hasattr(value, "__dataclass_fields__") else value)


def run_enveloped(callback, *, message: str = "ok"):
    request_id = uuid4().hex
    try:
        return build_success(callback(), message=message, request_id=request_id)
    except KeyError as exc:
        return build_error(message=str(exc), code=40401, status_code=404, request_id=request_id)
    except FileNotFoundError as exc:
        return build_error(message=str(exc), code=40404, status_code=404, request_id=request_id)
    except HTTPException as exc:
        return build_error(message=str(exc.detail), code=exc.status_code * 100, status_code=exc.status_code, request_id=request_id)
    except Exception as exc:
        return build_error(message=str(exc), code=40000, status_code=400, request_id=request_id)


def create_app() -> FastAPI:
    runtime = build_runtime()
    static_dir = Path(__file__).resolve().parent / "static"
    app = FastAPI(
        title="BaiduPan CLI API",
        version="0.2.0",
        description=(
            "Third-party Baidu Netdisk CLI and API wrapper built on the official bdpan CLI. "
            "This service does not expose cookie or token handling and works with one bdpan config directory per account."
        ),
        openapi_tags=[
            {"name": "system", "description": "Service health, runtime status, and capability metadata."},
            {"name": "accounts", "description": "Account bind, login state check, and account listing."},
            {"name": "files", "description": "Directory, listing, and upload/share operations under /apps/bdpan."},
            {"name": "shares", "description": "Transfer share links into the selected Baidu account."},
            {"name": "compat", "description": "Compatibility-oriented endpoints with mainstream envelope/query usage."},
        ],
    )

    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    def system_status_payload() -> dict:
        bdpan_bin = os.environ.get("BDPAN_BIN", "bdpan")
        return {
            "bdpan_bin": bdpan_bin,
            "bdpan_available": bool(shutil.which(bdpan_bin)),
            "runtime_home": str(runtime.paths.home),
            "uploads_dir": str(runtime.paths.uploads_dir),
            "protocols": {
                "rest_json": True,
                "multipart_upload": True,
                "query_compat": True,
                "openapi": True,
            },
            "limitations": [
                "Built on the official bdpan CLI.",
                "One config directory per account.",
                "Does not expose token or cookie handling.",
                "Primary working scope is /apps/bdpan.",
                "search is not reliable and is excluded from the main contract.",
            ],
        }

    def accounts_payload() -> list[dict]:
        return [to_dict(account) for account in runtime.accounts.list_accounts()]

    def tasks_payload() -> list[dict]:
        return [to_dict(task) for task in runtime.tasks.list_tasks()]

    def start_bind_payload(body: BindStartBody) -> dict:
        session = runtime.binding.start_binding(display_name=body.display_name)
        return {"account": to_dict(session.account), "auth_url": session.auth_url}

    def complete_bind_payload(body: BindCompleteBody) -> dict:
        return to_dict(runtime.binding.complete_binding(account_id=body.account_id, auth_code=body.auth_code))

    def check_account_payload(account_id: str) -> dict:
        return to_dict(runtime.binding.check_account(account_id=account_id))

    def mkdir_payload(body: MkdirBody) -> dict:
        return to_dict(runtime.files.mkdir(account_id=body.account_id, remote_path=body.remote_path))

    def ls_payload(body: LsBody) -> list[dict]:
        return [to_dict(item) for item in runtime.files.ls(account_id=body.account_id, remote_path=body.remote_path)]

    def upload_share_payload(body: UploadShareBody) -> dict:
        task = runtime.files.upload_and_share(
            UploadShareRequest(
                account_id=body.account_id,
                local_path=body.local_path,
                remote_path=body.remote_path,
            )
        )
        return to_dict(task)

    def transfer_share_payload(body: TransferShareBody) -> dict:
        task = runtime.files.transfer_share(
            TransferShareRequest(
                account_id=body.account_id,
                share_url=body.share_url,
                password=body.password,
                save_path=body.save_path,
            )
        )
        return to_dict(task)

    def browser_upload_share_payload(account_id: str, remote_path: str, file: UploadFile) -> dict:
        suffix = Path(file.filename or "upload.bin").suffix
        local_path = runtime.paths.uploads_dir / f"{uuid4().hex}{suffix}"
        try:
            with local_path.open("wb") as output:
                copyfileobj(file.file, output)
            task = runtime.files.upload_and_share(
                UploadShareRequest(
                    account_id=account_id,
                    local_path=str(local_path),
                    remote_path=remote_path,
                )
            )
            return to_dict(task)
        finally:
            file.file.close()
            local_path.unlink(missing_ok=True)

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/portal", include_in_schema=False)
    def portal() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/system/status", tags=["system"])
    def system_status() -> dict:
        return system_status_payload()

    @app.get("/api/accounts", tags=["accounts"])
    def list_accounts() -> list[dict]:
        return accounts_payload()

    @app.get("/api/tasks", tags=["system"])
    def list_tasks() -> list[dict]:
        return tasks_payload()

    @app.post("/api/accounts/bind/start", tags=["accounts"])
    def bind_start(body: BindStartBody) -> dict:
        try:
            return start_bind_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/accounts/bind/complete", tags=["accounts"])
    def bind_complete(body: BindCompleteBody) -> dict:
        try:
            return complete_bind_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/accounts/{account_id}/check", tags=["accounts"])
    def check_account(account_id: str) -> dict:
        try:
            return check_account_payload(account_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/mkdir", tags=["files"])
    def mkdir(body: MkdirBody) -> dict:
        try:
            return mkdir_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/ls", tags=["files"])
    def ls(body: LsBody) -> list[dict]:
        try:
            return ls_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/upload-share", tags=["files"])
    def upload_share(body: UploadShareBody) -> dict:
        try:
            return upload_share_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/files/browser-upload-share", tags=["files"])
    def browser_upload_share(
        account_id: str = Form(...),
        remote_path: str = Form(...),
        file: UploadFile = File(...),
    ) -> dict:
        try:
            return browser_upload_share_payload(account_id, remote_path, file)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/shares/transfer", tags=["shares"])
    def transfer_share(body: TransferShareBody) -> dict:
        try:
            return transfer_share_payload(body)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/v1/meta/capabilities", tags=["system"])
    def api_v1_capabilities():
        return run_enveloped(system_status_payload, message="capabilities ready")

    @app.get("/api/v1/system/status", tags=["system"])
    def api_v1_system_status():
        return run_enveloped(system_status_payload, message="system status ready")

    @app.get("/api/v1/accounts", tags=["accounts"])
    def api_v1_accounts():
        return run_enveloped(accounts_payload, message="accounts ready")

    @app.get("/api/v1/tasks", tags=["system"])
    def api_v1_tasks():
        return run_enveloped(tasks_payload, message="tasks ready")

    @app.post("/api/v1/accounts/bind/start", tags=["accounts"])
    def api_v1_bind_start(body: BindStartBody):
        return run_enveloped(lambda: start_bind_payload(body), message="bind session created")

    @app.post("/api/v1/accounts/bind/complete", tags=["accounts"])
    def api_v1_bind_complete(body: BindCompleteBody):
        return run_enveloped(lambda: complete_bind_payload(body), message="account bind completed")

    @app.post("/api/v1/accounts/{account_id}/check", tags=["accounts"])
    def api_v1_check_account(account_id: str):
        return run_enveloped(lambda: check_account_payload(account_id), message="account status checked")

    @app.post("/api/v1/files/list", tags=["files"])
    def api_v1_list_files(body: LsBody):
        return run_enveloped(lambda: ls_payload(body), message="directory listed")

    @app.post("/api/v1/files/mkdir", tags=["files"])
    def api_v1_mkdir(body: MkdirBody):
        return run_enveloped(lambda: mkdir_payload(body), message="directory created")

    @app.post("/api/v1/files/upload-share", tags=["files"])
    def api_v1_upload_share(body: UploadShareBody):
        return run_enveloped(lambda: upload_share_payload(body), message="upload and share completed")

    @app.post("/api/v1/files/browser-upload-share", tags=["files"])
    def api_v1_browser_upload_share(
        account_id: str = Form(...),
        remote_path: str = Form(...),
        file: UploadFile = File(...),
    ):
        return run_enveloped(
            lambda: browser_upload_share_payload(account_id, remote_path, file),
            message="browser upload and share completed",
        )

    @app.post("/api/v1/shares/transfer", tags=["shares"])
    def api_v1_transfer_share(body: TransferShareBody):
        return run_enveloped(lambda: transfer_share_payload(body), message="share transfer completed")

    @app.get("/compat/baidu/transfer", tags=["compat"])
    def compat_baidu_transfer(
        account_id: str = Query(...),
        url: str = Query(...),
        pwd: str | None = Query(default=None),
        path: str | None = Query(default=None),
    ):
        body = TransferShareBody(account_id=account_id, share_url=url, password=pwd, save_path=path)
        return run_enveloped(lambda: transfer_share_payload(body), message="compat transfer completed")

    @app.post("/compat/baidu/transfer", tags=["compat"])
    def compat_baidu_transfer_post(body: TransferShareBody):
        return run_enveloped(lambda: transfer_share_payload(body), message="compat transfer completed")

    @app.get("/compat/baidu/list", tags=["compat"])
    def compat_baidu_list(
        account_id: str = Query(...),
        path: str | None = Query(default=ROOT_PATH),
    ):
        body = LsBody(account_id=account_id, remote_path=path)
        return run_enveloped(lambda: ls_payload(body), message="compat list completed")

    @app.post("/compat/baidu/mkdir", tags=["compat"])
    def compat_baidu_mkdir(body: MkdirBody):
        return run_enveloped(lambda: mkdir_payload(body), message="compat mkdir completed")

    @app.post("/compat/baidu/upload-share", tags=["compat"])
    def compat_baidu_upload_share(
        account_id: str = Form(...),
        remote_path: str = Form(...),
        file: UploadFile = File(...),
    ):
        return run_enveloped(
            lambda: browser_upload_share_payload(account_id, remote_path, file),
            message="compat upload and share completed",
        )

    return app
