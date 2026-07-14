"""Immutable, non-audio provenance for a Voxplot analysis record."""
from __future__ import annotations

import platform
import sys
from typing import Any

import parselmouth

from analysis.indices import ABIResult, AVQIResult, abi_model_metadata
from analysis.parselmouth_metrics import cpps_configuration
from analysis.recording_protocol import PROTOCOL_VERSION, QUALITY_RULESET_VERSION, StandardizedPair
from config import (
    ANALYSIS_LANGUAGE,
    READING_PASSAGE_IDS,
    USER_TIMEZONE,
    VOICE_QUALITY_SCORING_VERSION,
)


ANALYSIS_VERSION = "voxplot_analysis_v2"
NORM_SET_ID = "de_reference_cutoffs_v1"
SCHEMA_VERSION = 2


# DETERMINISTIC: build the metadata needed to reproduce an analysis; fallback contains no audio or secrets.
def build_analysis_metadata(
    *,
    standardized: StandardizedPair,
    sv_capture: dict[str, Any] | None,
    cs_capture: dict[str, Any] | None,
    avqi_result: AVQIResult,
    abi_result: ABIResult,
    norms: dict,
    voice_quality_score: float | None,
) -> dict:
    """Return the complete non-audio audit trail for a new recording."""
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "quality_ruleset_version": QUALITY_RULESET_VERSION,
        "scoring_version": VOICE_QUALITY_SCORING_VERSION,
        "analysis_language": ANALYSIS_LANGUAGE,
        "reading_passage_id": READING_PASSAGE_IDS[ANALYSIS_LANGUAGE],
        "recording_timezone": USER_TIMEZONE,
        "norm_set_id": NORM_SET_ID,
        "reference_cutoffs": {
            "avqi": norms["avqi"].as_dict(),
            "breathiness_estimate": norms["abi"].as_dict(),
        },
        "capture": {
            "sv": sv_capture or {"source_kind": "unknown"},
            "cs": cs_capture or {"source_kind": "unknown"},
            "raw_audio_stored": False,
        },
        "protocol": standardized.as_dict(),
        "indices": {
            "avqi_like": avqi_result.as_dict(),
            "voxplot_breathiness_estimate": abi_result.as_dict(),
        },
        "voice_quality": {
            "score_0_100": voice_quality_score,
            "requires_components": ["avqi", "abi"],
            "weighting": {"avqi": 0.5, "abi": 0.5},
        },
        "implementation": {
            "cpps": cpps_configuration(),
            "breathiness_model": abi_model_metadata(),
            "parselmouth_version": getattr(parselmouth, "__version__", "unknown"),
            "praat_version": str(getattr(parselmouth, "PRAAT_VERSION", "unknown")),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "runtime": f"python-{sys.version_info.major}.{sys.version_info.minor}",
        },
    }
