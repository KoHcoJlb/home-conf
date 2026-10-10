import os
import subprocess
import tempfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "update.zsh"
MOCKS = """
git() {
  case "$1" in
    rev-parse) print -r -- target ;;
    -c) print -r -- G ;;
    *) print -r -- "git:$*" ;;
  esac
}
chezmoi() {
  print -r -- "chezmoi:$*"
  builtin read -r reply
  return "$FAIL_APPLY"
}
tmux() { print -r -- error; }
read() { print -r -- read; }
"""


def check_signatures():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        origin = home / "origin"
        checkout = home / ".local/share/chezmoi"
        key = home / "signing-key"
        (home / ".shellenv").write_text("chezmoi() { print -r -- applied; }\n")
        env = dict(
            os.environ,
            HOME=directory,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            SSH_AUTH_SOCK="",
            TMUX_PANE="",
        )

        def git(*args, cwd=origin, input=None):
            return subprocess.run(
                ["git", *args],
                cwd=cwd,
                env=env,
                input=input,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout.strip()

        def update(expected, *, applied=False, error=None):
            result = subprocess.run(
                [str(SOURCE)],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            assert result.returncode == (1 if error else 0), result
            assert ("applied" in result.stdout.splitlines()) == applied, result
            assert git("rev-parse", "HEAD", cwd=checkout) == expected, result
            if error:
                assert error in result.stderr, result

        for path in (key, home / "untrusted-key"):
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(path)],
                env=env,
                check=True,
                timeout=10,
            )

        origin.mkdir()
        git("init", "-b", "master")
        git("config", "user.name", "Test")
        git("config", "user.email", "test@example.com")
        git("config", "gpg.format", "ssh")
        git("config", "user.signingkey", str(key))
        (origin / "allowed_signers").write_text(
            'test@example.com namespaces="git" ' + key.with_suffix(".pub").read_text()
        )
        git("add", "allowed_signers")
        git("commit", "-m", "Unsigned legacy history")
        baseline = git("rev-parse", "HEAD")
        checkout.parent.mkdir(parents=True)
        git("clone", str(origin), str(checkout))

        update(baseline, error="Unsigned commit")

        git("commit", "--allow-empty", "-S", "-m", "Trusted signature")
        signed = git("rev-parse", "HEAD")
        update(signed, applied=True)

        git("commit", "--allow-empty", "-m", "Unsigned tip")
        update(signed, error="Unsigned commit")

        git("commit", "--allow-empty", "-S", "-m", "Signed after unsigned")
        signed = git("rev-parse", "HEAD")
        update(signed, applied=True)

        git(
            "-c",
            f"user.signingkey={home / 'untrusted-key'}",
            "commit",
            "--allow-empty",
            "-S",
            "-m",
            "Untrusted signature",
        )
        update(signed, error="Invalid or untrusted signature")

        content = git("cat-file", "commit", signed) + "\nTampered message\n"
        tampered = git("hash-object", "-t", "commit", "-w", "--stdin", input=content)
        git("update-ref", "refs/heads/master", tampered)
        update(signed, error="Invalid or untrusted signature")

        git("update-ref", "refs/heads/master", signed)
        (checkout / "allowed_signers").unlink()
        update(signed, error="Invalid or untrusted signature")


def check():
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / ".local/share/chezmoi/.git").mkdir(parents=True)
        (Path(directory) / ".shellenv").write_text(MOCKS)
        env = dict(os.environ, HOME=directory, FAIL_APPLY="0", TMUX_PANE="")
        command = [str(SOURCE)]

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
    check_signatures()
    print("chezmoi update locking and signature checks passed")
