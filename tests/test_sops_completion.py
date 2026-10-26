import os
import pty
import select
import shlex
import shutil
import signal
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_until(fd, marker):
    output = b""
    deadline = time.monotonic() + 10
    while marker not in output:
        remaining = deadline - time.monotonic()
        assert remaining > 0 and select.select([fd], [], [], remaining)[0], output
        output += os.read(fd, 65536)
    return output


def check():
    zsh = shutil.which("zsh")
    assert zsh and shutil.which("sops"), "Run with zsh and sops on PATH"

    pid, fd = pty.fork()
    if pid == 0:
        os.execv(zsh, [zsh, "-dfi"])

    try:
        # Use the existing tests directory as a harmless filename fixture.
        setup = (
            f"export PATH={shlex.quote(os.environ['PATH'])}; "
            f"cd {shlex.quote(str(ROOT))}; "
            f"fpath=({shlex.quote(str(ROOT / 'completions'))} $fpath); "
            "autoload -Uz compinit; compinit -D; bindkey -e; "
            "capture() { print -r -- $'\\nBUFFER:'\"$BUFFER\"$'\\nEND'; }; "
            "zle -N capture; bindkey '^X' capture; "
            "PROMPT='READY> '; RPROMPT=''; print INITIALIZED"
        )
        os.write(fd, (setup + "\n").encode())
        read_until(fd, b"\r\nINITIALIZED\r\n")

        for line, expected in (
            ("sops decrypt -i tests/test_sops_c", "tests/test_sops_completion.py"),
            (
                "sops decrypt --in-place tests/test_sops_c",
                "tests/test_sops_completion.py",
            ),
            ("sops encrypt -i tests/test_sops_c", "tests/test_sops_completion.py"),
            ("sops -d -i tests/test_sops_c", "tests/test_sops_completion.py"),
            ("sops decrypt -i ", "tests/"),
            ("sops dec", "sops decrypt"),
            ("sops decrypt --in-pl", "sops decrypt --in-place"),
        ):
            os.write(fd, ("\x15" + line + "\t\x18").encode())
            output = read_until(fd, b"\r\nEND\r\n").decode()
            assert expected in output, (line, output)
    finally:
        os.kill(pid, signal.SIGTERM)
        os.close(fd)
        os.waitpid(pid, 0)


if __name__ == "__main__":
    check()
    print("SOPS completion checks passed")
