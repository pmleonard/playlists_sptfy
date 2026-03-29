from __future__ import annotations

import json
import shutil
from pathlib import Path

_REQUIRED_SETTINGS_KEYS = {
    "settings_version": int,
    "metadata_enabled": bool,
    "strict_mode": bool,
    "dry_run": bool,
    "log_level": str,
    "max_ctr": int,
}

_REQUIRED_CONFIG_KEYS = {
    "song_list_path": str,
    "duplicates_path": str,
    "duplicates_report_path": str,
    "songs_csv_path": str,
    "playlist_export_path": str,
    "grouped_songs_path": str,
    "run_summary_path": str,
    "tags_filter": dict,
}

_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
CURRENT_SETTINGS_VERSION = 1
_OPTIONAL_INT_SETTINGS = {
    "http_timeout_seconds": 1,
    "http_max_attempts": 1,
    "http_retry_backoff_seconds": 1,
    "http_retry_jitter_seconds": 0,
}


def _read_json_file(path: Path) -> dict:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def _write_json_file(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)
        file.write("\n")


def migrate_settings_to_v1(settings: dict, defaults: dict | None = None) -> tuple[dict, bool]:
    migrated = dict(settings)
    version = migrated.get("settings_version")
    changed = False
    defaults = defaults or {}

    def _backfill_missing_keys() -> None:
        nonlocal changed
        for key in (*_REQUIRED_SETTINGS_KEYS, *_OPTIONAL_INT_SETTINGS):
            if key not in migrated and key in defaults:
                migrated[key] = defaults[key]
                changed = True

    if version == CURRENT_SETTINGS_VERSION:
        _backfill_missing_keys()
        return migrated, changed

    if version in (None, 0):
        migrated["settings_version"] = CURRENT_SETTINGS_VERSION
        changed = True

        # Fill newly introduced keys from defaults when available.
        _backfill_missing_keys()

        return migrated, changed

    raise ValueError(
        f"Unsupported settings_version: {version} (expected {CURRENT_SETTINGS_VERSION})"
    )


def migrate_settings_file(settings_path: Path, default_settings_path: Path) -> bool:
    if not settings_path.exists() and default_settings_path.exists():
        shutil.copy(default_settings_path, settings_path)
        return True

    settings = _read_json_file(settings_path)
    defaults = _read_json_file(default_settings_path) if default_settings_path.exists() else {}
    migrated, changed = migrate_settings_to_v1(settings, defaults)
    if changed:
        _write_json_file(settings_path, migrated)
    return changed


def migrate_config(config: dict, defaults: dict | None = None) -> tuple[dict, bool]:
    migrated = dict(config)
    changed = False
    defaults = defaults or {}

    for key in _REQUIRED_CONFIG_KEYS:
        if key not in migrated and key in defaults:
            migrated[key] = defaults[key]
            changed = True

    return migrated, changed


def migrate_config_file(config_path: Path, default_config_path: Path) -> bool:
    if not config_path.exists() and default_config_path.exists():
        shutil.copy(default_config_path, config_path)
        return True

    config = _read_json_file(config_path)
    defaults = _read_json_file(default_config_path) if default_config_path.exists() else {}
    migrated, changed = migrate_config(config, defaults)
    if changed:
        _write_json_file(config_path, migrated)
    return changed


def validate_settings(settings: dict) -> dict:
    for key, expected_type in _REQUIRED_SETTINGS_KEYS.items():
        if key not in settings:
            raise ValueError(f"Missing required setting: {key}")
        if expected_type is int:
            try:
                settings[key] = int(settings[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid setting type for {key}: expected int") from exc
        elif expected_type is bool:
            if not isinstance(settings[key], bool):
                raise ValueError(f"Invalid setting type for {key}: expected bool")
        elif not isinstance(settings[key], expected_type):
            raise ValueError(f"Invalid setting type for {key}: expected {expected_type.__name__}")

    if settings["max_ctr"] < 0:
        raise ValueError("Invalid setting value for max_ctr: expected >= 0")

    if settings["settings_version"] != CURRENT_SETTINGS_VERSION:
        raise ValueError(
            "Unsupported settings_version: "
            f"{settings['settings_version']} (expected {CURRENT_SETTINGS_VERSION})"
        )

    settings["log_level"] = settings["log_level"].strip().upper()
    if settings["log_level"] not in _LOG_LEVELS:
        raise ValueError(
            "Invalid setting value for log_level: expected one of "
            "CRITICAL, ERROR, WARNING, INFO, DEBUG"
        )

    for key, min_value in _OPTIONAL_INT_SETTINGS.items():
        if key not in settings:
            continue
        try:
            settings[key] = int(settings[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid setting type for {key}: expected int") from exc
        if settings[key] < min_value:
            raise ValueError(f"Invalid setting value for {key}: expected >= {min_value}")

    return settings


def validate_config(config: dict) -> dict:
    for key, expected_type in _REQUIRED_CONFIG_KEYS.items():
        if key not in config:
            raise ValueError(f"Missing required setting: {key}")
        if not isinstance(config[key], expected_type):
            raise ValueError(f"Invalid setting type for {key}: expected {expected_type.__name__}")

    tags_filter = config["tags_filter"]
    for key in ("include", "exclude"):
        if key not in tags_filter:
            raise ValueError(f"Missing required tags_filter key: {key}")
        values = tags_filter[key]
        if not isinstance(values, (list, str)):
            raise ValueError(f"Invalid tags_filter.{key}: expected list or string")

    return config


def load_settings(
    settings_path: Path,
    default_settings_path: Path,
    config_path: Path,
    default_config_path: Path,
) -> dict:
    migrate_settings_file(settings_path, default_settings_path)
    migrate_config_file(config_path, default_config_path)

    settings_defaults = (
        _read_json_file(default_settings_path) if default_settings_path.exists() else {}
    )
    settings = _read_json_file(settings_path)
    settings, settings_changed = migrate_settings_to_v1(settings, settings_defaults)
    if settings_changed:
        _write_json_file(settings_path, settings)

    config_defaults = _read_json_file(default_config_path) if default_config_path.exists() else {}
    config = _read_json_file(config_path)
    config, config_changed = migrate_config(config, config_defaults)
    if config_changed:
        _write_json_file(config_path, config)

    validated_settings = validate_settings(settings)
    validated_config = validate_config(config)
    return {**validated_config, **validated_settings}
