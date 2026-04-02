from __future__ import annotations

import subprocess

from bdpan_wrapper.bdpan.adapter import BaiduPanCliAdapter
from bdpan_wrapper.bdpan.parser import parse_ls_output, parse_transfer_output, parse_upload_output, parse_whoami_output


class FakeRunner:
    def __init__(self, responses: list[subprocess.CompletedProcess[str]]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def run(self, args: list[str], *, input_text=None, env=None):
        self.calls.append(args)
        if not self.responses:
            raise AssertionError("no fake response left")
        return self.responses.pop(0)


def _completed(stdout: str, *, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_adapter_runs_expected_commands() -> None:
    runner = FakeRunner(
        [
            _completed("https://openapi.baidu.com/oauth/2.0/authorize?device_code=abc"),
            _completed(""),
            _completed('{"status":"logged_in","username":"demo","expires_at":"2026-04-02T10:00:00+08:00"}'),
            _completed('{"path":"releases/demo"}'),
            _completed('{"status":"success","local_path":"./foo.pdf","remote_path":"folder/foo.pdf"}'),
            _completed('{"link":"https://pan.baidu.com/s/1abc","short_url":"1abc","share_id":1,"period":7,"pwd":"1234"}'),
            _completed('{"save_path":"inbox/demo"}'),
            _completed('{"list":[{"path":"/apps/bdpan/demo","server_filename":"demo","isdir":1},{"path":"/apps/bdpan/demo/a.txt","server_filename":"a.txt","isdir":0,"size":12}]}'),
        ]
    )
    adapter = BaiduPanCliAdapter(bdpan_bin="bdpan", runner=runner)

    auth_url = adapter.get_auth_url(config_path="/tmp/config.json")
    whoami = adapter.login_with_code(config_path="/tmp/config.json", auth_code="abcd1234abcd1234abcd1234abcd1234")
    mkdir = adapter.mkdir(config_path="/tmp/config.json", remote_path="releases/demo")
    upload = adapter.upload(config_path="/tmp/config.json", local_path="foo.pdf", remote_path="folder/foo.pdf")
    share = adapter.share(config_path="/tmp/config.json", remote_path="folder/foo.pdf")
    transfer = adapter.transfer(
        config_path="/tmp/config.json",
        share_url="https://pan.baidu.com/s/1abc",
        password="1234",
        save_path="inbox/demo",
    )
    entries = adapter.ls(config_path="/tmp/config.json", remote_path="/apps/bdpan/demo")

    assert auth_url.startswith("https://openapi.baidu.com/")
    assert whoami.logged_in is True
    assert mkdir.remote_path == "releases/demo"
    assert upload.remote_path == "folder/foo.pdf"
    assert share.link == "https://pan.baidu.com/s/1abc"
    assert transfer.remote_path == "inbox/demo"
    assert len(entries) == 2
    assert entries[0].is_dir is True
    assert runner.calls[0] == ["bdpan", "--config-path", "/tmp/config.json", "login", "--accept-disclaimer", "--get-auth-url"]
    assert runner.calls[1] == ["bdpan", "--config-path", "/tmp/config.json", "login", "--accept-disclaimer", "--set-code-stdin"]
    assert runner.calls[2] == ["bdpan", "--config-path", "/tmp/config.json", "whoami", "--json"]
    assert runner.calls[3] == ["bdpan", "--config-path", "/tmp/config.json", "mkdir", "releases/demo", "--json"]
    assert runner.calls[4] == ["bdpan", "--config-path", "/tmp/config.json", "upload", "foo.pdf", "folder/foo.pdf", "--json"]
    assert runner.calls[5] == ["bdpan", "--config-path", "/tmp/config.json", "share", "--json", "folder/foo.pdf"]
    assert runner.calls[6] == ["bdpan", "--config-path", "/tmp/config.json", "transfer", "https://pan.baidu.com/s/1abc", "-p", "1234", "inbox/demo", "--json"]
    assert runner.calls[7] == ["bdpan", "--config-path", "/tmp/config.json", "ls", "--json", "/apps/bdpan/demo"]


def test_parse_whoami_handles_unauthenticated_json() -> None:
    whoami = parse_whoami_output(
        '{"authenticated": false, "expires_at": "0001-01-01T00:00:00Z", "has_valid_token": false}'
    )

    assert whoami.logged_in is False
    assert whoami.expires_at is None


def test_parse_upload_raises_on_baidu_error_payload() -> None:
    try:
        parse_upload_output('{"code":1,"data":null,"error":"创建文件失败: errno=-10"}')
    except RuntimeError as exc:
        assert "errno=-10" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for bdpan upload error payload")


def test_parse_transfer_accepts_plain_json_shape() -> None:
    result = parse_transfer_output('{"remote_path":"inbox/demo.pdf"}')
    assert result.remote_path == "inbox/demo.pdf"


def test_parse_ls_output_supports_list_payload() -> None:
    entries = parse_ls_output('{"list":[{"path":"/apps/bdpan/a","server_filename":"a","isdir":1},{"path":"/apps/bdpan/a.txt","server_filename":"a.txt","isdir":0,"size":7}]}')
    assert len(entries) == 2
    assert entries[0].name == "a"
    assert entries[1].size == 7
