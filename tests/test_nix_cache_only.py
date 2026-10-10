import ast
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "home/dot_config/systemd/user/chezmoi-update.service.tmpl"
HOOK = ROOT / "home/dot_config/nix/executable_cache-only-hook"


def check():
    setting = next(
        line.removeprefix("Environment=")
        for line in SERVICE.read_text().splitlines()
        if line.startswith('Environment="NIX_CONFIG=')
    )
    config = ast.literal_eval(setting).removeprefix("NIX_CONFIG=")

    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        hook = home / ".config/nix/cache-only-hook"
        hook.parent.mkdir(parents=True)
        hook.write_bytes(HOOK.read_bytes())
        hook.chmod(0o755)
        env = dict(os.environ, NIX_CONFIG=config.replace("%h", str(home)))
        command = [
            "nix",
            "build",
            "--impure",
            "--extra-experimental-features",
            "nix-command",
            "--store",
            f"local?root={home}/store",
            "--option",
            "substituters",
            "",
            "--no-link",
            "--expr",
        ]

        for prefer_local in ("false", "true"):
            # Exercise the hook independently of the max-jobs scheduling guard.
            options = (
                ["--option", "max-jobs", "1", "--option", "sandbox", "false"]
                if prefer_local == "true"
                else []
            )
            result = subprocess.run(
                command
                + [
                    (
                        'derivation { name = "cache-only-test"; '
                        'system = builtins.currentSystem; builder = "/bin/sh"; '
                        'args = [ "-c" "exit 99" ]; '
                        f"preferLocalBuild = {prefer_local}; }}"
                    )
                ]
                + options,
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode != 0, result
            expected = (
                "Cache-only chezmoi update: refusing to build"
                if prefer_local == "true"
                else "max-jobs"
            )
            assert expected in result.stderr, result.stderr
            assert "exit code 99" not in result.stderr, result.stderr

        subprocess.run(
            command + ['builtins.toFile "cache-only-present" "available"'],
            env=env,
            check=True,
            timeout=30,
        )


if __name__ == "__main__":
    check()
    print("Nix cache-only service checks passed")
