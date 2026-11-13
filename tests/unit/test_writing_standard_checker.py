"""validate_writing_standard — prose extraction, splitting and the CLI."""
import validate_writing_standard as vws


def test_main_runs():
    assert vws.main([]) == 0
