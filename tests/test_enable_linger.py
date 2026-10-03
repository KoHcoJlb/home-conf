import os
import subprocess
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "home/dot_config/systemd/user/run_before_enable_linger.sh.tmpl"
)
SCRIPT = "\n".join(SOURCE.read_text().splitlines()[1:-1])
MOCKS = """
test() { return "$SYSTEMD_STATUS"; }
id() { printf '%s\n' "$USER_ID"; }
command() { return "$SUDO_MISSING"; }
loginctl() { printf 'loginctl %s\n' "$*"; return "$LOGINCTL_STATUS"; }
sudo() {
    [ "$1" = -n ] || exit 99
    shift
    [ "$SUDO_STATUS" = 0 ] || return "$SUDO_STATUS"
    printf 'sudo %s\n' "$*"
    "$@"
}
"""


def check():
    defaults = dict(
        os.environ,
        SYSTEMD_STATUS="0",
        USER_ID="1000",
        SUDO_MISSING="0",
        SUDO_STATUS="0",
        LOGINCTL_STATUS="0",
    )
    sudo_output = (
        "sudo true\nsudo loginctl enable-linger 1000\nloginctl enable-linger 1000\n"
    )
    cases = (
        ({"USER_ID": "0", "SUDO_MISSING": "1"}, "loginctl enable-linger 0\n", 0),
        ({}, sudo_output, 0),
        ({"SUDO_MISSING": "1"}, "", 0),
        ({"SUDO_STATUS": "1"}, "", 0),
        ({"SYSTEMD_STATUS": "1"}, "", 0),
        ({"LOGINCTL_STATUS": "1"}, sudo_output, 1),
    )

    for overrides, output, status in cases:
        result = subprocess.run(
            ["sh", "-c", MOCKS + SCRIPT],
            env=defaults | overrides,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        assert (result.returncode, result.stdout, result.stderr) == (status, output, "")


if __name__ == "__main__":
    check()
    print("linger privilege checks passed")
