#!/usr/bin/env python3
"""Subprocess helper that does not swallow the reason (blog-craft#59).

`subprocess.run(..., check=True, capture_output=True)` is the right call — the
caller wants the streams — but its `CalledProcessError` renders as

    Command '[...]' returned non-zero exit status 1.

and its traceback points at `subprocess.run` in the stdlib. That reads like a
blog-craft internals bug, while the actual cause is usually one line the child
already printed and nobody read:

    load answers: open .blog-craft.yaml: no such file or directory

`run_checked` keeps the capture and attaches it to the exception message, so
diagnosing a renderer failure is a one-line read instead of re-running
`bootstrap-render.sh` by hand.

Library:
  run_checked(cmd, **kw) -> CompletedProcess    # raises CommandFailed on rc != 0
  CommandFailed                                 # a CalledProcessError subclass
"""
from __future__ import annotations

import subprocess

__all__ = ["CommandFailed", "run_checked"]


class CommandFailed(subprocess.CalledProcessError):
    """A CalledProcessError whose message carries the captured streams.

    Subclasses `CalledProcessError` deliberately: callers (and callers'
    callers) already catch that, and every existing handler keeps working —
    they just get a message worth reading.
    """

    def __str__(self) -> str:
        parts = [super().__str__()]
        for label, stream in (("stderr", self.stderr), ("stdout", self.output)):
            text = stream.decode("utf-8", "replace") if isinstance(stream, bytes) else stream
            if text and text.strip():
                parts.append(f"--- {label} ---\n{text.strip()}")
        return "\n".join(parts)


def run_checked(cmd, **kw) -> subprocess.CompletedProcess:
    """Run `cmd`, capturing both streams; raise CommandFailed on a non-zero exit.

    Defaults to `capture_output=True, text=True`; any kwarg
    (`cwd=`, `env=`, …) passes through to `subprocess.run`.
    """
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise CommandFailed(r.returncode, cmd, output=r.stdout, stderr=r.stderr)
    return r
