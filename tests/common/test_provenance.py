from pathlib import Path

from xc_dynamics.common.provenance import run_record

REPO = Path(__file__).resolve().parents[2]


def test_record_in_the_repository():
    record = run_record(REPO)
    assert len(record["commit"]) == 40  # a full git hash
    assert isinstance(record["uncommitted_changes"], bool)
    assert record["machine"] and record["started"]


def test_record_outside_a_repository(tmp_path):
    record = run_record(tmp_path)
    assert record["commit"] == "unknown"
    assert record["uncommitted_changes"] is False
