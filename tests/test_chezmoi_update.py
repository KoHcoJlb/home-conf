import os
import subprocess
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "ohmyzsh/zshrc"
UPDATE = SOURCE.read_text().split("function chezmoi_update {", 1)[1]
UPDATE = "function chezmoi_update {" + UPDATE.split("\n}\n", 1)[0] + "\n}\n"
SCRIPT = (
    UPDATE
    + """
git() { print -r -- "git:$*"; }
chezmoi() {
  print -r -- "chezmoi:$*"
  builtin read -r reply
  return "$FAIL_APPLY"
}
tmux() { print -r -- error; }
read() { print -r -- read; }
chezmoi_update
"""
)


def check():
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / ".local/share/chezmoi/.git").mkdir(parents=True)
        env = dict(os.environ, HOME=directory, FAIL_APPLY="0", TMUX_PANE="")
        command = ["zsh", "-f", "-c", SCRIPT]

        for fail, pane in (("0", ""), ("1", ""), ("1", "%test")):
            with subprocess.Popen(
                command,
                env=dict(env, FAIL_APPLY=fail, TMUX_PANE=pane),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as owner:
                try:
                    assert owner.stdout.readline() == "git:fetch\n"

                    duplicate = subprocess.run(
                        command,
                        env=env,
                        input="\n",
                        capture_output=True,
                        text=True,
                        timeout=2,
                        check=True,
                    )
                    assert duplicate.stdout == duplicate.stderr == "", (
                        duplicate.stdout,
                        duplicate.stderr,
                    )
                    assert owner.poll() is None

                    stdout, stderr = owner.communicate("\n", timeout=2)
                    assert owner.returncode == int(fail)
                    assert stderr == ""
                    assert "chezmoi:apply\n" in stdout
                    assert ("error\n" in stdout) == (fail == "1" and bool(pane))
                    assert ("read\n" in stdout) == (fail == "1" and bool(pane))
                finally:
                    if owner.poll() is None:
                        owner.kill()
                        owner.communicate()

            retry = subprocess.run(
                command,
                env=env,
                input="\n",
                capture_output=True,
                text=True,
                timeout=2,
                check=True,
            )
            assert "git:fetch\n" in retry.stdout
            assert "chezmoi:apply\n" in retry.stdout
            assert "error\n" not in retry.stdout
            assert retry.stderr == ""


if __name__ == "__main__":
    check()
    print("chezmoi update locking checks passed")
