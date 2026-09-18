"""Running a command whose output someone may be following: stdout and stderr merged, every line emitted to the log sink as it arrives, the tail kept for the error."""

from __future__ import annotations

import subprocess
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from action_platform.logging import emit

TAIL = 60


@dataclass
class Completed:
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def stream(
    args: list[str],
    cwd: Optional[Path] = None,
    env: Optional[dict[str, str]] = None,
    tail: int = TAIL,
) -> Completed:
    emit("$ " + " ".join(_shown(a) for a in args))
    process = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )
    last: deque[str] = deque(maxlen=tail)

    assert process.stdout is not None

    for line in process.stdout:
        line = line.rstrip("\n")
        last.append(line)
        emit(line)

    process.stdout.close()
    code = process.wait()

    return Completed(code, "\n".join(last))


def _shown(arg: str) -> str:
    return arg if len(arg) <= 120 else arg[:117] + "…"
