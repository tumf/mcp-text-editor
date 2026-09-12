"""Tests for utility helpers."""

import os
import pathlib
import subprocess
import sys

from mcp_text_editor import utils


def test_locked_file_uses_shared_lock_for_read(monkeypatch, tmp_path):
    """Read mode should acquire a shared lock and release it on exit."""
    file_path = tmp_path / "shared.txt"
    file_path.write_text("hello\n", encoding="utf-8")
    lock_calls = []
    unlock_calls = []

    monkeypatch.setattr(
        utils.portalocker,
        "lock",
        lambda file_obj, lock_type: lock_calls.append(lock_type),
    )
    monkeypatch.setattr(
        utils.portalocker,
        "unlock",
        lambda file_obj: unlock_calls.append(file_obj.name),
    )

    with utils.locked_file(str(file_path), "r") as file_obj:
        assert file_obj.read() == "hello\n"

    assert lock_calls == [utils.portalocker.LOCK_SH]
    assert unlock_calls == [str(file_path)]


def test_locked_file_uses_exclusive_lock_for_write(monkeypatch, tmp_path):
    """Write mode should create parent directories and use an exclusive lock."""
    file_path = tmp_path / "nested" / "exclusive.txt"
    lock_calls = []
    unlock_calls = []

    monkeypatch.setattr(
        utils.portalocker,
        "lock",
        lambda file_obj, lock_type: lock_calls.append(lock_type),
    )
    monkeypatch.setattr(
        utils.portalocker,
        "unlock",
        lambda file_obj: unlock_calls.append(file_obj.name),
    )

    with utils.locked_file(str(file_path), "w") as file_obj:
        file_obj.write("created\n")

    assert file_path.read_text(encoding="utf-8") == "created\n"
    assert lock_calls == [utils.portalocker.LOCK_EX]
    assert unlock_calls == [str(file_path)]


def test_package_import_succeeds_without_fcntl():
    """Import should not crash when the package itself no longer imports fcntl."""
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not existing_pythonpath
        else os.pathsep.join([src_path, existing_pythonpath])
    )
    code = """
import builtins
import importlib
import sys
import types

fake_portalocker = types.ModuleType("portalocker")
fake_portalocker.LOCK_SH = 1
fake_portalocker.LOCK_EX = 2
fake_portalocker.lock = lambda file_obj, lock_type: None
fake_portalocker.unlock = lambda file_obj: None
sys.modules["portalocker"] = fake_portalocker

orig_import = builtins.__import__

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "fcntl":
        raise ImportError("blocked for test")
    return orig_import(name, globals, locals, fromlist, level)

builtins.__import__ = guarded_import
importlib.import_module("mcp_text_editor")
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
