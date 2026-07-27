"""P1 — subprocess failures carry the child's own words (blog-craft#59).

`reproduce.py` ran the renderer with `check=True, capture_output=True` and never
surfaced the streams. The operator got a bare `CalledProcessError` whose
traceback points at `subprocess.run` in the stdlib — it reads like a blog-craft
internals bug, while the actual cause is one line the renderer already printed:

    load answers: open .blog-craft.yaml: no such file or directory

`tools/proc.run_checked` keeps the capture (callers want the streams) but
re-raises with them attached, so the diagnosis is a one-line read.
"""
import os
import subprocess
import sys

import pytest

from proc import CommandFailed, run_checked  # tools/ on sys.path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_success_returns_completed_process_with_captured_stdout():
    r = run_checked([sys.executable, "-c", "print('hello')"])
    assert r.returncode == 0
    assert "hello" in r.stdout


def test_failure_message_carries_the_childs_stderr():
    with pytest.raises(CommandFailed) as e:
        run_checked([sys.executable, "-c",
                     "import sys; print('DISTINCTIVE-STDERR-LINE', file=sys.stderr); sys.exit(3)"])
    msg = str(e.value)
    assert "DISTINCTIVE-STDERR-LINE" in msg, "the reason must be IN the message"
    assert "3" in msg                       # the exit code
    assert "-c" in msg                       # the command


def test_failure_message_carries_stdout_too():
    with pytest.raises(CommandFailed) as e:
        run_checked([sys.executable, "-c", "print('ON-STDOUT'); raise SystemExit(1)"])
    assert "ON-STDOUT" in str(e.value)


def test_is_a_calledprocesserror_so_existing_handlers_still_catch_it():
    with pytest.raises(subprocess.CalledProcessError) as e:
        run_checked([sys.executable, "-c", "raise SystemExit(2)"])
    assert isinstance(e.value, CommandFailed)
    assert e.value.returncode == 2
    assert e.value.cmd[0] == sys.executable
    assert e.value.stderr is not None


def test_kwargs_pass_through(tmp_path):
    r = run_checked([sys.executable, "-c", "import os; print(os.getcwd())"], cwd=str(tmp_path))
    assert os.path.realpath(r.stdout.strip()) == os.path.realpath(str(tmp_path))


# --- the reported failure, end to end -----------------------------------------

def test_reproduce_apply_surfaces_the_renderers_own_reason(tmp_path):
    """The #59 repro: the renderer's stderr must reach the operator.

    Asserts the *property* — the failing file is named in the message — rather
    than any one wording, so the test survives the renderer changing how it
    phrases the error.
    """
    import reproduce
    with pytest.raises(subprocess.CalledProcessError) as e:
        reproduce.apply(str(tmp_path / "definitely-not-here.yaml"), str(tmp_path / "out"))
    msg = str(e.value)
    assert "--- stderr ---" in msg, "the captured stream must be attached, not discarded"
    assert "definitely-not-here.yaml" in msg.split("--- stderr ---", 1)[1], (
        "the reason must name the file that could not be read.\n"
        f"got: {msg}")
