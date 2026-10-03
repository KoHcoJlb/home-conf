import os
import subprocess
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "home/dot_config/systemd/user/run_after_enable_chezmoi_update.sh.tmpl"
)
SCRIPT = "\n".join(SOURCE.read_text().splitlines()[1:-1])
MOCKS = """
test() { return "$SYSTEMD_STATUS"; }
id() { printf '%s\n' "$USER_ID"; }
systemctl() {
    sh -c 'printf "%s|%s\\n" "${XDG_RUNTIME_DIR:?missing runtime directory}" "$*"' sh "$@"
}
"""


def check():
    for uid, runtime, systemd in (
        ("0", None, "0"),
        ("1000", None, "0"),
        ("1000", "", "0"),
        ("1000", "/custom/runtime", "0"),
        ("1000", None, "1"),
    ):
        env = dict(os.environ, USER_ID=uid, SYSTEMD_STATUS=systemd)
        env.pop("XDG_RUNTIME_DIR", None)
        env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        if runtime is not None:
            env["XDG_RUNTIME_DIR"] = runtime

        result = subprocess.run(
            ["sh", "-c", MOCKS + SCRIPT],
            env=env,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )

        expected = ""
        if systemd == "0":
            path = runtime or f"/run/user/{uid}"
            expected = (
                f"{path}|--user daemon-reload\n"
                f"{path}|--user enable --now chezmoi-update.timer\n"
            )
        assert (result.returncode, result.stdout, result.stderr) == (0, expected, "")


if __name__ == "__main__":
    check()
    print("user timer environment checks passed")
