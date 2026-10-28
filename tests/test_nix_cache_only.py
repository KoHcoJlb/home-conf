import os
import subprocess
import tempfile
from pathlib import Path

from test_chezmoi_update import MOCKS, SOURCE

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "home/dot_config/nix/executable_cache-only-hook"


def check():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        (home / ".local/share/chezmoi/.git").mkdir(parents=True)
        (home / ".shellenv").write_text(
            MOCKS + '\nchezmoi() { print -rn -- "$NIX_CONFIG" > "$HOME/nix-config"; }\n'
        )
        hook = home / ".config/nix/cache-only-hook"
        hook.parent.mkdir(parents=True)
        hook.write_bytes(HOOK.read_bytes())
        hook.chmod(0o755)
        inherited = (
            "max-jobs = 1\nbuilders =\nsandbox = false\n"
            "build-users-group =\nconnect-timeout = 7"
        )
        env = dict(os.environ, HOME=directory, NIX_CONFIG=inherited, TMUX_PANE="")
        config_file = home / "nix-config"

        for args in (["--allow-build"], []):
            subprocess.run([str(SOURCE), *args], env=env, check=True, timeout=10)
            config = config_file.read_text()
            if args:
                assert config == inherited, config
            else:
                assert config.startswith(inherited + "\n"), config
                assert "\nmax-jobs = 0\n" in config, config
                assert "\nbuilders =\n" in config, config
                assert "\nalways-allow-substitutes = true\n" in config, config
                assert config.endswith(f"pre-build-hook = {hook}"), config

        config_file.unlink()
        for option, status in (("--help", 0), ("--unknown", 1)):
            result = subprocess.run(
                [str(SOURCE), option], env=env, check=False, timeout=10
            )
            assert result.returncode == status, result
            assert not config_file.exists()

        env["NIX_CONFIG"] = config
        command = [
            "nix",
            "build",
            "--impure",
            "--extra-experimental-features",
            "nix-command",
            "--store",
            f"local?store={home}/store&state={home}/state&log={home}/log",
            "--option",
            "substituters",
            "",
            "--no-link",
            "--expr",
        ]

        for prefer_local in ("false", "true"):
            result = subprocess.run(
                command
                + [
                    (
                        'derivation { name = "cache-only-test"; '
                        'system = builtins.currentSystem; builder = "/bin/sh"; '
                        'args = [ "-c" "exit 99" ]; '
                        f"preferLocalBuild = {prefer_local}; }}"
                    )
                ],
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, result
            assert "max-jobs" in result.stderr, result.stderr
            assert "exit code 99" not in result.stderr, result.stderr

        subprocess.run(
            command + ['builtins.toFile "cache-only-present" "available"'],
            env=env,
            check=True,
            timeout=30,
        )

        result = subprocess.run(
            command
            + [
                (
                    'derivation { name = "allow-build-test"; '
                    'system = builtins.currentSystem; builder = "/bin/sh"; '
                    'args = [ "-c" "exit 99" ]; }'
                )
            ],
            env=dict(env, NIX_CONFIG=inherited),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0, result
        assert "exit code 99" in result.stderr, result.stderr


if __name__ == "__main__":
    check()
    print("Nix cache-only updater checks passed")
