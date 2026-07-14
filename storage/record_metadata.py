"""Read versioned Voxplot metadata without rewriting historical records."""
from __future__ import annotations

from collections.abc import Mapping


LEGACY_ANALYSIS_METADATA = {
    "schema_version": 0,
    "analysis_version": "legacy_unversioned",
    "protocol_version": "legacy_manual_unversioned",
    "scoring_version": "voice_quality_v1_legacy_unknown",
    "recording_timezone": "Europe/Berlin",
    "protocol": {
        "status": "legacy_unknown",
        "analysis_allowed": True,
    },
}


# DETERMINISTIC: read metadata with an explicit legacy fallback; fallback never changes stored history.
def analysis_metadata(record: Mapping) -> dict:
    sample_meta = record.get("sample_meta")
    raw = sample_meta.get("analysis_meta") if isinstance(sample_meta, Mapping) else None
    if not isinstance(raw, Mapping):
        return {
            **LEGACY_ANALYSIS_METADATA,
            "protocol": dict(LEGACY_ANALYSIS_METADATA["protocol"]),
        }
    metadata = {**LEGACY_ANALYSIS_METADATA, **dict(raw)}
    protocol = raw.get("protocol")
    metadata["protocol"] = {
        **LEGACY_ANALYSIS_METADATA["protocol"],
        **(dict(protocol) if isinstance(protocol, Mapping) else {}),
    }
    return metadata


# DETERMINISTIC: expose a record's capture quality class; fallback is legacy_unknown.
def recording_quality_status(record: Mapping) -> str:
    return str(analysis_metadata(record)["protocol"].get("status", "legacy_unknown"))


# DETERMINISTIC: expose a record's protocol label; fallback is legacy_manual_unversioned.
def protocol_version(record: Mapping) -> str:
    return str(analysis_metadata(record).get("protocol_version", "legacy_manual_unversioned"))


# DETERMINISTIC: expose a record's scoring label; fallback is voice_quality_v1_legacy_unknown.
def scoring_version(record: Mapping) -> str:
    return str(analysis_metadata(record).get("scoring_version", "voice_quality_v1_legacy_unknown"))
