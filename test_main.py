"""Perform integration/main tests on the Python launcher.

Due to the fact that Rust's testing infrastructure doesn't allow for direct
testing of main.rs, this file executes a debug build of the Python launcher to
exercise main.rs. All code contained elsewhere in this project is expected to
be tested using Rust code.
"""

import os
import pathlib
import subprocess
import sys

import pytest


@pytest.fixture
def py(monkeypatch):
    """Provide a convenience function for calling the Python launcher.

    The function has a 'path' attribute for a pathlib.Path object pointing
    at where the Python launcher is located.

    The critical environment variables which can influence the execution of
    the Python launcher are set to a known good state. This includes setting
    PATH to a single directory of where the Python interpreter executing this
    file is located.
    """
    python_executable = pathlib.Path(sys.executable)
    monkeypatch.delenv("PYLAUNCH_DEBUG", raising=False)
    monkeypatch.setenv("PATH", os.fspath(python_executable.parent))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    py_path = pathlib.Path(__file__).parent / "target" / "debug" / "py"

    def call_py(*args, debug=False):
        call = [py_path]
        call.extend(args)
        env = os.environ.copy()
        if debug:
            env["PYLAUNCH_DEBUG"] = "1"
        return subprocess.run(call, capture_output=True, text=True, env=env)

    call_py.path = py_path
    yield call_py


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help(py, flag):
    call = py(flag)
    assert not call.returncode
    assert os.fspath(py.path) in call.stdout
    assert sys.executable in call.stdout
    assert not call.stderr


def test_list(py):
    call = py("--list")
    assert not call.returncode
    assert sys.executable in call.stdout
    assert ".".join(map(str, sys.version_info[:2])) in call.stdout
    assert not call.stderr


@pytest.mark.parametrize(
    "python_version",
    [None, f"-{sys.version_info[0]}", f"-{sys.version_info[0]}.{sys.version_info[1]}"],
)
def test_execute(py, python_version):
    # Don't use sys.executable as symlinks and such make it hard to get an
    # easy comparison.
    args = ["-c" "import sys; print(sys.version)"]
    if python_version:
        args.insert(0, python_version)
    call = py(*args)
    assert not call.returncode
    assert call.stdout.strip() == sys.version
    assert not call.stderr


class TestExitCode:
    def test_malformed_version(self, py):
        call = py("-3.")
        assert call.returncode
        assert call.stderr

    def test_nonexistent_version(self, py):
        call = py("-0.9")
        assert call.returncode
        assert call.stderr

    def test_unexecutable_file(self, py, tmp_path, monkeypatch):
        version = "0.1"
        not_executable = tmp_path / f"python{version}"
        not_executable.touch()
        monkeypatch.setenv("PATH", os.fspath(tmp_path), prepend=os.pathsep)
        call = py(f"-{version}")
        assert call.returncode
        assert call.stderr


def test_PYLAUNCH_DEBUG(py):
    call = py("-c", "pass", debug=True)
    assert not call.returncode
    assert call.stderr


if __name__ == "__main__":
    pytest.main()
