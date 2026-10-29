"""Run with tmux on PATH: python3 tests/test_btop_layout.py /path/to/patched/btop."""

import itertools
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def check_screen(screen, width, height, shown, beside, option):
    lines = screen.splitlines()
    boxes = {}
    for row, line in enumerate(lines):
        for title in re.finditer(r"[¹²³⁴](cpu|mem|net|proc)|(?<=┌─┐)(disks)", line):
            left = title.start() - 3
            bottom_title = line[left] == "└"
            edge = re.search(
                r"┘(?=└|$)" if bottom_title else r"┐(?=[┌│]|$)", line[title.end() :]
            )
            assert edge is not None, screen
            right = title.end() + edge.start()
            top = (
                max(y for y in range(row) if lines[y][left] == "┌")
                if bottom_title
                else row
            )
            bottom = next(y for y in range(top + 1, height) if lines[y][left] == "└")
            boxes[title[1] or title[2]] = (left, top, right + 1, bottom + 1)

    expected = set(shown.split())
    if beside and "show_disks = false" not in option:
        expected.add("disks")
    assert set(boxes) == expected, screen
    for left, top, right, bottom in boxes.values():
        assert 0 <= left < right <= width and 0 <= top < bottom <= height, screen
        assert lines[top][left] == "┌" and lines[bottom - 1][right - 1] == "┘", screen

    for a, b in itertools.combinations(boxes.values(), 2):
        assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], screen
    assert sum((r - l) * (b - t) for l, t, r, b in boxes.values()) == width * height

    sidebar_width = max(36, int(width * 0.30 + 0.5)) if "proc" in boxes else width
    for name in ("disks", "net"):
        if name in boxes:
            assert boxes[name][2] - boxes[name][0] == sidebar_width, screen

    if beside:
        cpu, mem = boxes["cpu"], boxes["mem"]
        assert cpu[2] == mem[0] and cpu[1::2] == mem[1::2], screen
        assert mem[2] - mem[0] == max(20, int(width * 0.20 + 0.5)), screen
        assert "┬" not in lines[mem[1]][mem[0] : mem[2]], screen
        assert all(
            line[mem[2] - 1] in "│┤" for line in lines[mem[1] + 1 : mem[3] - 1]
        ), screen

        compact_cpu = width < 100
        assert (lines[cpu[1] + 1][cpu[0] + 1] == "┌") == compact_cpu, screen
        if compact_cpu:
            assert lines[cpu[1] + 2][cpu[0] + 2 : cpu[0] + 6] == "CPU ", screen
            assert all(
                line[cpu[0] + 1] == "│" for line in lines[cpu[1] + 2 : cpu[3] - 2]
            ), screen

        if "disks" in boxes:
            disks = boxes["disks"]
            disk_left = width - sidebar_width if "proc_left = true" in option else 0
            assert disks[0] == disk_left, screen
            assert (
                any(
                    "Used:" in line[disks[0] : disks[2]]
                    for line in lines[disks[1] : disks[3]]
                )
                or "io_mode = true" in option
            ), screen
            if "net" in boxes:
                net = boxes["net"]
                assert disks[0::2] == net[0::2], screen
                assert (
                    net[3] == disks[1]
                    if "mem_below_net = true" in option
                    else disks[3] == net[1]
                ), screen
    elif "cpu" in boxes:
        assert boxes["cpu"][2] == width, screen


def check(binary):
    with tempfile.TemporaryDirectory(prefix="btop-layout-") as directory:
        root = Path(directory)
        config = root / "btop/btop.conf"
        config.parent.mkdir()
        command = ["tmux", "-S", str(root / "tmux.sock"), "-f", "/dev/null"]

        def tmux(*args, check=True):
            return subprocess.run(
                [*command, *args],
                check=check,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout

        def wait_for_screen(width, height, shown, option, beside):
            deadline = time.monotonic() + 10
            while True:
                screen = tmux("capture-pane", "-p")
                try:
                    check_screen(screen, width, height, shown, beside, option)
                    return
                except (AssertionError, ValueError, IndexError, StopIteration):
                    if time.monotonic() >= deadline:
                        print(screen)
                        raise
                    time.sleep(0.1)

        cases = [
            (200, 48, "cpu mem net proc", "", True),
            (160, 24, "cpu mem net proc", "", True),
            (120, 24, "cpu mem net proc", "", True),
            (98, 24, "cpu mem net proc", "", True),
            (97, 30, "cpu mem net proc", "", True),
            (99, 24, "cpu mem net proc", "", True),
            (100, 24, "cpu mem net proc", "", True),
            (200, 24, "cpu mem net proc", "", True),
            (80, 24, "cpu mem net proc", "", True),
            (200, 48, "cpu mem net proc", "", True),
            (80, 24, "cpu mem net proc", "cpu_single_graph = true", True),
            (80, 24, "cpu mem net proc", 'cpu_graph_lower = "system"', True),
            (60, 24, "cpu mem", 'clock_format = "%X"', True),
            (200, 48, "cpu mem", "", True),
            (200, 48, "cpu mem net", "", True),
            (200, 48, "cpu mem proc", "", True),
            (200, 48, "cpu net proc", "", False),
            (200, 48, "mem net proc", "", False),
            (200, 48, "cpu mem net proc", "cpu_bottom = true", True),
            (200, 48, "cpu mem net proc", "proc_left = true", True),
            (200, 48, "cpu mem net proc", "mem_below_net = true", True),
            (200, 48, "cpu mem net proc", "io_mode = true", True),
            (200, 48, "cpu mem net proc", "mem_graphs = false", True),
            (200, 48, "cpu mem", "show_disks = false", True),
            (200, 48, "cpu mem net proc", "show_disks = false", True),
        ]
        try:
            tmux("new-session", "-d", "-s", "layout", "-x", "200", "-y", "48")
            tmux("set-option", "-g", "status", "off")
            tmux("set-option", "-g", "remain-on-exit", "on")
            previous_config = None
            for width, height, shown, option, beside in cases:
                config.write_text(
                    f'shown_boxes = "{shown}"\n'
                    'clock_format = ""\nrounded_corners = false\n'
                    "update_ms = 100\nsave_config_on_exit = false\n"
                    'only_physical = false\nuse_fstab = false\ndisks_filter = "/"\n'
                    f"{option}\n"
                )
                tmux("resize-window", "-x", str(width), "-y", str(height))
                if previous_config != (shown, option):
                    tmux(
                        "respawn-pane",
                        "-k",
                        "exec "
                        + shlex.join(
                            [
                                "env",
                                f"XDG_CONFIG_HOME={root}",
                                binary,
                                "--force-utf",
                                "--no-tty",
                            ]
                        ),
                    )
                    previous_config = (shown, option)

                wait_for_screen(width, height, shown, option, beside)
                print(
                    f"PASS {width}x{height}: {shown}; {option or 'defaults'}",
                    flush=True,
                )

            for option in ("", "show_disks = false"):
                tmux("send-keys", "d")
                wait_for_screen(200, 48, "cpu mem net proc", option, True)
                print(f"PASS live disk toggle: {option or 'shown'}", flush=True)
        finally:
            tmux("kill-server", check=False)


if __name__ == "__main__":
    check(os.path.abspath(sys.argv[1]))
