"""G6: every recording appends a schema-valid JSONL row with norms/flags."""
import json

import pytest

from analysis.norms import flag_all
from storage.logger import JsonlRecordStore, REQUIRED_PARAMETER_KEYS, build_record, log_session


def _dummy_parameters():
    return {k: 1.0 for k in REQUIRED_PARAMETER_KEYS}


def test_build_record_rejects_missing_parameters():
    with pytest.raises(ValueError):
        build_record({}, {"f0_mean_hz": 1.0}, {}, {})


def test_build_record_schema():
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})
    record = build_record({"sv_seconds": 3.0, "cs_seconds": 6.0, "sample_rate_hz": 44100}, params, indices, norms)

    assert "timestamp" in record
    assert record["sample_meta"]["sample_rate_hz"] == 44100
    assert record["parameters"] == params
    assert record["indices"] == indices
    assert record["norms"]["jitter_local_pct"]["in_range"] is not None


def test_log_session_appends_valid_jsonl_line(tmp_path):
    path = tmp_path / "voice_log.jsonl"
    store = JsonlRecordStore(str(path))
    params = _dummy_parameters()
    indices = {"avqi": 3.0, "abi": 2.0}
    norms = flag_all({**params, **indices})

    log_session(store, {"sv_seconds": 3.0, "cs_seconds": 6.0, "sample_rate_hz": 44100}, params, indices, norms)
    log_session(store, {"sv_seconds": 3.1, "cs_seconds": 6.2, "sample_rate_hz": 44100}, params, indices, norms)

    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert set(parsed.keys()) == {"timestamp", "sample_meta", "parameters", "indices", "norms"}
