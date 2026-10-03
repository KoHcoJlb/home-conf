import ast
import contextlib
import io
import json
import subprocess
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "home/dot_config/nix/run_before_00_trust_user.py.tmpl"
)
TRUST_COMMAND = [
    "nix",
    "--extra-experimental-features",
    "nix-command",
    "store",
    "info",
    "--store",
    "daemon",
    "--json",
]
SCRIPT = "\n".join(SOURCE.read_text().splitlines()[1:-1])
SCRIPT = SCRIPT.replace("{{ .chezmoi.username | toJson }}", '"alice"')
MODULE = types.ModuleType("nix_trusted_users")
MODULE.__file__ = str(SOURCE.resolve())
# Load the trusted, rendered local template without running its entry point.
exec(compile(SCRIPT, str(SOURCE), "exec"), MODULE.__dict__)  # noqa: S102
ENTRY = compile(
    ast.Module(body=ast.parse(SCRIPT).body[-1:], type_ignores=[]), str(SOURCE), "exec"
)


def run_entry():
    with patch.object(MODULE, "__name__", "__main__"):
        try:
            exec(ENTRY, MODULE.__dict__)  # noqa: S102 - run the trusted local entry point.
        except SystemExit as error:
            if isinstance(error.code, str):
                print(error.code, file=MODULE.sys.stderr)
                return 1
            return error.code or 0
    return 0


def check(files, expected, *, systemd=True, fail=False, restarts=1):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name, content in files.items():
            path = root / name
            path.write_text(content.replace("/etc/nix/", f"{root}/"))
            path.chmod(0o640)

        command = ["systemctl", "restart", "nix-daemon.service"]
        with (
            patch.object(MODULE, "CONFIG", root / "nix.conf"),
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(Path, "is_dir", return_value=systemd),
            patch.object(MODULE.subprocess, "run") as run,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            if fail:
                run.side_effect = [subprocess.CalledProcessError(1, command), None]
            result = run_entry()

        assert result == int(fail)
        for name, content in expected.items():
            path = root / name
            assert path.read_text() == content.replace("/etc/nix/", f"{root}/"), (
                name,
                path.read_text(),
                content,
            )
            assert path.stat().st_mode & 0o777 == 0o640
        assert run.call_count == restarts
        for call in run.call_args_list:
            assert call.args == (command,)
        assert not list(root.glob(".chezmoi-trust.*"))


def check_wait(responses, expected):
    clock = [0.0]
    replies = iter(responses)

    def advance(seconds):
        clock[0] += seconds

    def probe(*, timeout):
        assert 0 < timeout <= min(2, 30 - clock[0])
        response = next(replies, responses[-1])
        if isinstance(response, subprocess.TimeoutExpired):
            advance(timeout)
        if isinstance(response, Exception):
            raise response
        return response

    with (
        patch.object(MODULE.time, "monotonic", side_effect=lambda: clock[0]),
        patch.object(MODULE.time, "sleep", side_effect=advance),
        patch.object(MODULE, "current_user_is_trusted", side_effect=probe),
    ):
        try:
            assert MODULE.wait_for_trust() is None
        except SystemExit as error:
            assert expected == 1
            assert "Timed out confirming Nix trust" in str(error)
        else:
            assert expected == 0

    assert 0 <= clock[0] <= 30
    if expected:
        assert clock[0] == 30


def main():
    for before, after in (
        ("", "extra-trusted-users = alice\n"),
        ("trusted-users = root bob\n", "trusted-users = root bob alice\n"),
        ("extra-trusted-users = bob\n", "extra-trusted-users = bob alice\n"),
        ("trusted-users = root # keep\n", "trusted-users = root alice # keep\n"),
        ("trusted-users =\n", "trusted-users = alice\n"),
        (
            "# trusted-users = alice\n",
            "# trusted-users = alice\nextra-trusted-users = alice\n",
        ),
        ("trusted-users = alice2\n", "trusted-users = alice2 alice\n"),
        ("trusted-users = root", "trusted-users = root alice\n"),
        ("trusted-users = *\n", "trusted-users = * alice\n"),
        (
            "trusted-users = root\nextra-trusted-users = alice\nextra-trusted-users = bob\n",
            "trusted-users = root\nextra-trusted-users = alice\nextra-trusted-users = bob alice\n",
        ),
        (
            "trusted-users = alice\ntrusted-users = root\n",
            "trusted-users = alice\ntrusted-users = root alice\n",
        ),
    ):
        assert MODULE.add_trusted_user(before, "alice") == after
        check({"nix.conf": before}, {"nix.conf": after})
        assert MODULE.add_trusted_user(after, "alice") == after
        check({"nix.conf": after}, {"nix.conf": after})

    for content in (
        "trusted-users = root alice # keep\n",
        "extra-trusted-users = alice\n",
        "trusted-users = root\nextra-trusted-users = bob alice\n",
    ):
        check({"nix.conf": content}, {"nix.conf": content})

    for include in (
        "include nix.custom.conf",
        "!include nix.custom.conf",
        " include ./nix.custom.conf # keep",
        "include /etc/nix/nix.custom.conf",
    ):
        original = {
            "nix.conf": include + "\n",
            "nix.custom.conf": "extra-trusted-users = bob\n",
        }
        check(
            original,
            {**original, "nix.custom.conf": "extra-trusted-users = bob alice\n"},
        )

    original = {
        "nix.conf": "# include nix.custom.conf\n",
        "nix.custom.conf": "trusted-users = bob\n",
    }
    check(
        original,
        {
            **original,
            "nix.conf": original["nix.conf"] + "extra-trusted-users = alice\n",
        },
    )
    original = {"nix.conf": "!include nix.custom.conf\n"}
    check(
        original, {"nix.conf": original["nix.conf"] + "extra-trusted-users = alice\n"}
    )
    check({}, {}, restarts=0)

    original = {
        "nix.conf": "include nix.custom.conf\ntrusted-users = root\n",
        "nix.custom.conf": "extra-trusted-users = alice\n",
    }
    check(
        original,
        {
            **original,
            "nix.conf": "include nix.custom.conf\ntrusted-users = root alice\n",
        },
    )

    original = {"nix.conf": "trusted-users = root\n"}
    check(original, original, systemd=False, restarts=0)
    check(original, original, fail=True, restarts=2)

    for response in (
        '{"trusted": true}',
        '{"trusted": 1}',
        '{"trusted": null}',
        "{}",
        "[]",
        '{"trusted": "true"}',
        '{"trusted": "1"}',
        '{"trusted": "0"}',
        '{"trusted": 2}',
        '{"trusted": -1}',
        '{"trusted": 0.0}',
        '{"trusted": 1.0}',
        "invalid JSON",
        subprocess.CalledProcessError(1, TRUST_COMMAND),
        subprocess.TimeoutExpired(TRUST_COMMAND, 10),
        FileNotFoundError("nix is unavailable"),
    ):
        result = (
            response
            if isinstance(response, Exception)
            else subprocess.CompletedProcess(TRUST_COMMAND, 0, stdout=response)
        )
        with (
            patch.object(Path, "is_dir", return_value=True),
            patch.object(MODULE.os, "geteuid", return_value=1000),
            patch.object(MODULE.subprocess, "run", side_effect=[result]) as run,
            patch.object(MODULE.shutil, "which") as which,
            patch.object(MODULE, "select_config") as select,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            assert run_entry() == 0
            run.assert_called_once_with(
                TRUST_COMMAND,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            which.assert_not_called()
            select.assert_not_called()

    for sudo, returncode, trusted, setup_status, verification_status in (
        (None, 0, False, 0, 0),
        ("/usr/bin/sudo", 1, False, 0, 0),
        ("/usr/bin/sudo", 0, False, 0, 0),
        (None, 0, 0, 0, 0),
        ("/usr/bin/sudo", 1, 0, 0, 0),
        ("/usr/bin/sudo", 0, 0, 0, 0),
        ("/usr/bin/sudo", 0, False, 1, 0),
        ("/usr/bin/sudo", 0, False, 0, 1),
    ):
        with (
            patch.object(Path, "is_dir", return_value=True),
            patch.object(MODULE.os, "geteuid", return_value=1000),
            patch.object(MODULE.shutil, "which", return_value=sudo),
            patch.object(
                MODULE.subprocess,
                "run",
                side_effect=[
                    subprocess.CompletedProcess(
                        TRUST_COMMAND, 0, stdout=json.dumps({"trusted": trusted})
                    ),
                    subprocess.CompletedProcess([], returncode),
                    subprocess.CompletedProcess([], setup_status),
                ],
            ) as run,
            patch.object(
                MODULE,
                "wait_for_trust",
                side_effect=SystemExit("verification failed")
                if verification_status
                else None,
            ) as verify,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = run_entry()

            if sudo and returncode == 0:
                assert result == (setup_status or verification_status)
                assert run.call_count == 3
                run.assert_called_with(
                    [sudo, "-n", MODULE.sys.executable, MODULE.__file__], check=False
                )
                assert verify.call_count == int(setup_status == 0)
            else:
                assert result == 0
                assert run.call_count == (2 if sudo else 1)
                verify.assert_not_called()
            if sudo:
                assert run.call_args_list[1].args == ([sudo, "-n", "true"],)
                assert run.call_args_list[1].kwargs == {
                    "stderr": subprocess.DEVNULL,
                    "check": False,
                }
            assert run.call_args_list[0].args == (TRUST_COMMAND,)

    for responses, expected in (
        ([True], 0),
        ([subprocess.CalledProcessError(1, TRUST_COMMAND), False, True], 0),
        ([subprocess.TimeoutExpired(TRUST_COMMAND, 2), True], 0),
        ([ValueError("invalid JSON"), TypeError("unknown trust status"), True], 0),
        ([False], 1),
        ([subprocess.CalledProcessError(1, TRUST_COMMAND)], 1),
        ([subprocess.TimeoutExpired(TRUST_COMMAND, 2)], 1),
    ):
        check_wait(responses, expected)

    print(
        "PASS: daemon trust check, trust settings, includes, idempotence, sudo, permissions, systemd, rollback, bounded verification"
    )


if __name__ == "__main__":
    main()
