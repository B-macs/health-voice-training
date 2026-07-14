"""One-time, idempotent import of local Voxplot JSONL history into Supabase."""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from storage.logger import JsonlRecordStore
from storage.supabase import SupabaseConfig, SupabaseRecordStore


def _load_config(path: Path) -> SupabaseConfig:
    """DETERMINISTIC: load the private TOML section; fallback exits before writing any records."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Secrets file not found: {path}") from exc
    config = SupabaseConfig.from_mapping(data.get("voxplot_supabase"))
    if config is None:
        raise SystemExit("[voxplot_supabase] is missing from the supplied secrets file.")
    return config


def migrate(log_paths: list[Path], config: SupabaseConfig) -> int:
    """DETERMINISTIC: submit every local record; fallback stops on a remote write error."""
    destination = SupabaseRecordStore(config)
    submitted = 0
    for log_path in log_paths:
        records = JsonlRecordStore(str(log_path)).read_all()
        for record in records:
            destination.append(record)
            submitted += 1
        print(f"Submitted {len(records)} record(s) from {log_path}")
    return submitted


def main() -> None:
    """DETERMINISTIC: parse explicit paths and report the idempotent import result."""
    parser = argparse.ArgumentParser(
        description="Import one or more Voxplot voice_log.jsonl files into Supabase."
    )
    parser.add_argument(
        "--secrets",
        required=True,
        type=Path,
        help="Path to a TOML file containing the [voxplot_supabase] section.",
    )
    parser.add_argument(
        "logs",
        nargs="+",
        type=Path,
        help="One or more local voice_log.jsonl files to import.",
    )
    args = parser.parse_args()

    missing = [path for path in args.logs if not path.is_file()]
    if missing:
        parser.error("Log file(s) not found: " + ", ".join(str(path) for path in missing))

    submitted = migrate(args.logs, _load_config(args.secrets))
    print(f"Submitted {submitted} record(s). Existing duplicate records were ignored safely.")


if __name__ == "__main__":
    main()
